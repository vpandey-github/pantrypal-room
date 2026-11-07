"""Add, use, discard and list pantry items.

Examples:
  python3 tools/pantry.py add --item milk --qty 2 --unit L --expiry 2026-11-10 --price 56 --by Mom
  python3 tools/pantry.py use --item eggs --qty 4 --by Dad
  python3 tools/pantry.py cook --meal "palak paneer" --by Mom
  python3 tools/pantry.py discard --item spinach --by Mom
  python3 tools/pantry.py list
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    batches, fail, fmt_qty, is_expired, known_units, load, log_event, nice_date,
    norm, out, parse_date, resolve, save_batches, stock, today,
)


def cmd_add(args):
    if args.qty <= 0:
        fail("Quantity must be more than 0.")
    units = known_units()
    name, _ = resolve(args.item, units.keys())
    name = name or norm(args.item)
    unit = args.unit or units.get(name)
    if not unit:
        fail(f"What unit is '{name}' measured in? Pass --unit (e.g. g, kg, L, pcs).", item=name)
    if name in units and units[name] != unit:
        fail(f"'{name}' is tracked in {units[name]}, not {unit}. Convert the quantity to {units[name]}.",
             item=name, expected_unit=units[name])
    expiry = parse_date(args.expiry) if args.expiry else None
    if expiry and expiry < today():
        fail(f"That expiry date ({args.expiry}) is already in the past.")

    items = batches()
    new_id = max((b["id"] for b in items), default=0) + 1
    items.append({
        "id": new_id,
        "name": name,
        "qty": args.qty,
        "qty_bought": args.qty,
        "unit": unit,
        "expiry": expiry.isoformat() if expiry else None,
        "price": args.price,
        "added_by": args.by,
        "added_on": today().isoformat(),
    })
    save_batches(items)
    log_event("bought", name, args.qty, unit, args.by, price=args.price)
    have, _ = stock().get(name, (0, unit))
    msg = f"Added {fmt_qty(args.qty, unit)} {name}"
    if expiry:
        msg += f", expires {nice_date(expiry)}"
    out({"ok": True, "message": msg + f". In stock now: {fmt_qty(have, unit)}.",
         "item": name, "in_stock": have, "unit": unit})


def take(items, name, qty):
    """Take qty of an item from the batch that expires first, so nothing goes off unnoticed."""
    usable = [b for b in items if b["name"] == name and b["qty"] > 0 and not is_expired(b)]
    usable.sort(key=lambda b: b["expiry"] or "9999-12-31")
    left = qty
    for b in usable:
        step = min(b["qty"], left)
        b["qty"] = round(b["qty"] - step, 3)
        left = round(left - step, 3)
        if left <= 0:
            break


def cmd_use(args):
    if args.qty <= 0:
        fail("Quantity must be more than 0.")
    current = stock()
    name, suggestions = resolve(args.item, current.keys())
    if not name:
        fail(f"'{args.item}' is not in the pantry.", did_you_mean=suggestions)
    have, unit = current[name]
    if args.qty > have + 1e-9:
        fail(f"Only {fmt_qty(have, unit)} {name} in stock, but {fmt_qty(args.qty, unit)} was used. "
             f"Please check the amount.", item=name, in_stock=have, unit=unit)

    items = batches()
    take(items, name, args.qty)
    save_batches(items)
    log_event("used", name, args.qty, unit, args.by)
    remaining = round(have - args.qty, 3)
    out({"ok": True, "message": f"Used {fmt_qty(args.qty, unit)} {name}. Left: {fmt_qty(remaining, unit)}.",
         "item": name, "in_stock": remaining, "unit": unit})


def one(name, qty, unit):
    """'1 onion', not '1 onions'."""
    if unit != "pcs" or qty != 1:
        return name
    return name[:-2] if name.endswith("oes") else name[:-1] if name.endswith("s") else name


def cmd_cook(args):
    """Record a meal cooked: use every ingredient of its recipe in one go."""
    recipes = {norm(r["name"]): r for r in load("recipes.json", {"recipes": []})["recipes"]}
    key, suggestions = resolve(args.meal, recipes.keys())
    if not key:
        fail(f"'{args.meal}' isn't one of our recipes. Tell me what was used instead.",
             did_you_mean=[recipes[k]["name"] for k in suggestions])
    recipe = recipes[key]

    # Check everything first, so a short ingredient changes nothing.
    current = stock()
    short = []
    for ing in recipe["ingredients"]:
        have, unit = current.get(ing["item"], (0, ing["unit"]))
        if ing["qty"] > have + 1e-9:
            short.append(f"{ing['item']} (need {fmt_qty(ing['qty'], unit)}, have {fmt_qty(have, unit)})")
    if short:
        fail(f"Can't log {recipe['name']}: not enough " + ", ".join(short) +
             ". Tell me what was actually used.", meal=recipe["name"], short=short)

    items = batches()
    for ing in recipe["ingredients"]:
        take(items, ing["item"], ing["qty"])
    save_batches(items)  # save the stock before writing history, as `use` does
    used = []
    for ing in recipe["ingredients"]:
        log_event("used", ing["item"], ing["qty"], ing["unit"], args.by, meal=recipe["name"])
        used.append(f"{fmt_qty(ing['qty'], ing['unit'])} {one(ing['item'], ing['qty'], ing['unit'])}")
    out({"ok": True, "message": f"Logged {recipe['name']}: used " + ", ".join(used) + ".",
         "meal": recipe["name"], "used": recipe["ingredients"]})


def cmd_discard(args):
    """Record food thrown away, so the weekly report counts it as waste."""
    items = batches()
    names = {b["name"] for b in items if b["qty"] > 0}
    name, suggestions = resolve(args.item, names)
    if not name:
        fail(f"'{args.item}' is not in the pantry.", did_you_mean=suggestions)
    thrown = 0
    unit = None
    for b in items:
        if b["name"] == name and b["qty"] > 0:
            unit = b["unit"]
            thrown += b["qty"]
            b["wasted_qty"] = round(b.get("wasted_qty", 0) + b["qty"], 3)
            b["wasted_on"] = today().isoformat()
            b["qty"] = 0
    save_batches(items)
    log_event("wasted", name, round(thrown, 3), unit, args.by)
    out({"ok": True, "message": f"Noted: {fmt_qty(thrown, unit)} {name} thrown away.",
         "item": name, "wasted": round(thrown, 3), "unit": unit})


def cmd_list(args):
    current = stock()
    rows = []
    for name in sorted(current):
        qty, unit = current[name]
        next_exp = min((b["expiry"] for b in batches()
                        if b["name"] == name and b["qty"] > 0 and b["expiry"] and not is_expired(b)),
                       default=None)
        rows.append({"item": name, "qty": qty, "unit": unit, "next_expiry": next_exp})
    out({"ok": True, "date": today().isoformat(), "count": len(rows), "items": rows})


def main():
    p = argparse.ArgumentParser(description="PantryPal pantry tool")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="record something bought")
    a.add_argument("--item", required=True)
    a.add_argument("--qty", type=float, required=True)
    a.add_argument("--unit")
    a.add_argument("--expiry", help="YYYY-MM-DD")
    a.add_argument("--price", type=float, default=0, help="total price paid for this batch")
    a.add_argument("--by", required=True, help="who bought it")
    a.set_defaults(fn=cmd_add)

    u = sub.add_parser("use", help="record something used")
    u.add_argument("--item", required=True)
    u.add_argument("--qty", type=float, required=True)
    u.add_argument("--by", required=True)
    u.set_defaults(fn=cmd_use)

    c = sub.add_parser("cook", help="record a meal cooked (uses all its ingredients)")
    c.add_argument("--meal", required=True)
    c.add_argument("--by", required=True)
    c.set_defaults(fn=cmd_cook)

    d = sub.add_parser("discard", help="record something thrown away")
    d.add_argument("--item", required=True)
    d.add_argument("--by", required=True)
    d.set_defaults(fn=cmd_discard)

    ls = sub.add_parser("list", help="show what is in stock")
    ls.set_defaults(fn=cmd_list)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
