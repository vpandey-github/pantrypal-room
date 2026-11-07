"""Draft the weekly shopping list, and approve it (list owner only).

The draft has every staple that is below its minimum, and skips staples
already in stock, so nobody buys the same thing twice. Only the list
owner named in data/settings.json can approve the list. The check is in
the code, but it trusts the --by name the agent passes (see "Known
limitations" in the README).

Examples:
  python3 tools/shopping_list.py draft
  python3 tools/shopping_list.py approve --by owner --remove onions --add "paneer:200:g"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    fail, fmt_qty, load, norm, out, resolve, save, settings, stock, today,
)


def build_draft():
    have = stock()
    staples = load("staples.json", {"staples": []})["staples"]
    to_buy, skipped = [], []
    for s in staples:
        qty, _ = have.get(s["item"], (0, s["unit"]))
        if qty + 1e-9 < s["min"]:
            to_buy.append({"item": s["item"], "buy": s["buy"], "unit": s["unit"],
                           "have": qty, "min": s["min"]})
        else:
            skipped.append({"item": s["item"], "have": qty, "unit": s["unit"]})
    return to_buy, skipped


def cmd_draft(args):
    to_buy, skipped = build_draft()
    save("draft_list.json", {"date": today().isoformat(), "items": to_buy})
    owner = settings()["list_owner"]
    lines = [f"{fmt_qty(i['buy'], i['unit'])} {i['item']}" for i in to_buy]
    message = (f"Draft list ({len(to_buy)} items): " + ", ".join(lines) + "."
               if to_buy else "Nothing is running low this week.")
    if skipped:
        message += f" Skipped {len(skipped)} staples already in stock."
    message += f" Waiting for @{owner} to approve."
    out({"ok": True, "date": today().isoformat(), "list_owner": owner, "message": message,
         "to_buy": to_buy, "already_in_stock": skipped})


def parse_adds(text):
    adds = []
    for part in filter(None, (p.strip() for p in (text or "").split(","))):
        bits = part.split(":")
        if len(bits) != 3:
            fail(f"Could not read '{part}'. Use item:qty:unit, e.g. paneer:200:g")
        try:
            qty = float(bits[1])
        except ValueError:
            fail(f"Could not read the quantity in '{part}'.")
        if qty <= 0:
            fail(f"The quantity in '{part}' must be more than 0.")
        adds.append({"item": norm(bits[0]), "buy": qty, "unit": bits[2].strip()})
    return adds


def cmd_approve(args):
    owner = settings()["list_owner"]
    who = norm(args.by).lstrip("@")
    if who != norm(owner).lstrip("@"):
        fail(f"Only the list owner (@{owner}) can approve the shopping list. "
             f"'{args.by}' cannot.", list_owner=owner)

    draft = load("draft_list.json")
    if not draft or draft.get("date") != today().isoformat():
        to_buy, _ = build_draft()  # no draft from today: make a fresh one
    else:
        to_buy = draft["items"]

    removed, not_found = [], []
    for name in filter(None, (p.strip() for p in (args.remove or "").split(","))):
        match, _ = resolve(name, [i["item"] for i in to_buy])
        if match:
            to_buy = [i for i in to_buy if i["item"] != match]
            removed.append(match)
        else:
            not_found.append(name)
    added = parse_adds(args.add)
    for a in added:
        same = next((i for i in to_buy if i["item"] == a["item"]), None)
        if same and same["unit"] != a["unit"]:
            fail(f"{a['item']} is already on the list in {same['unit']}, not {a['unit']}.")
        if same:  # "add 2 tomatoes" when tomatoes are listed: buy more, don't list twice
            same["buy"] = round(same["buy"] + a["buy"], 3)
        else:
            to_buy.append(a)

    history = load("approved_lists.json", {"lists": []})
    history["lists"].append({"date": today().isoformat(), "approved_by": owner,
                             "items": to_buy, "removed": removed, "added": [a["item"] for a in added]})
    save("approved_lists.json", history)

    lines = [f"{fmt_qty(i['buy'], i['unit'])} {i['item']}" for i in to_buy]
    message = f"Final list approved by @{owner} ({len(to_buy)} items): " + ", ".join(lines) + "."
    if not_found:
        message += " Not on the list, so not removed: " + ", ".join(not_found) + "."
    out({"ok": True, "approved_by": owner, "removed": removed, "not_found": not_found,
         "added": [a["item"] for a in added], "message": message, "items": to_buy})


def main():
    p = argparse.ArgumentParser(description="Weekly shopping list")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("draft", help="draft the list from low staples")
    d.set_defaults(fn=cmd_draft)

    a = sub.add_parser("approve", help="approve the list (list owner only)")
    a.add_argument("--by", required=True, help="the person approving")
    a.add_argument("--remove", help="comma-separated items to drop")
    a.add_argument("--add", help="comma-separated item:qty:unit to add")
    a.set_defaults(fn=cmd_approve)

    args = p.parse_args()
    (getattr(args, "fn", None) or cmd_draft)(args)


if __name__ == "__main__":
    main()
