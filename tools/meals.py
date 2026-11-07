"""Suggest meals that use up food expiring soon.

Ranks recipes by how many expiring items they use, then by whether
everything else is already in stock.

Example:
  python3 tools/meals.py --days 2 --top 3
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import batches, fmt_qty, is_expired, load, out, parse_date, stock, today  # noqa: E402


def expiring_days(days):
    """{item: days until its soonest batch expires}, for items expiring soon."""
    now = today()
    until = now + timedelta(days=days)
    soon = {}
    for b in batches():
        exp = parse_date(b.get("expiry"))
        if b["qty"] > 0 and exp and not is_expired(b) and exp <= until:
            left = (exp - now).days
            soon[b["name"]] = min(left, soon.get(b["name"], left))
    return soon


def main():
    p = argparse.ArgumentParser(description="Meal ideas that use expiring food first")
    p.add_argument("--days", type=int, default=2)
    p.add_argument("--top", type=int, default=3)
    args = p.parse_args()

    have = stock()
    soon = expiring_days(args.days)
    recipes = load("recipes.json", {"recipes": []})["recipes"]

    ready, almost = [], []
    for r in recipes:
        uses, missing = [], []
        for ing in r["ingredients"]:
            qty, _ = have.get(ing["item"], (0, ing["unit"]))
            if qty + 1e-9 < ing["qty"]:
                missing.append(f"{fmt_qty(ing['qty'] - qty, ing['unit'])} {ing['item']}")
            if ing["item"] in soon:
                uses.append(ing["item"])
        # Food that goes off sooner counts for more: tomorrow = 1/2, in 2 days = 1/3.
        urgency = round(sum(1 / (soon[i] + 1) for i in uses), 3)
        row = {"meal": r["name"], "uses_expiring": uses, "missing": missing,
               "minutes": r.get("minutes"), "serves": r.get("serves"), "urgency": urgency}
        if not missing:
            ready.append(row)
        elif len(missing) == 1 and uses:
            almost.append(row)

    key = lambda row: (-row["urgency"], row["minutes"] or 99)  # noqa: E731
    ready.sort(key=key)
    almost.sort(key=key)
    ready = ready[: args.top]
    almost = almost[:2]

    if ready and ready[0]["uses_expiring"]:
        best = ready[0]
        message = f"Try {best['meal']}: it uses {', '.join(best['uses_expiring'])} before it goes off."
    elif ready:
        message = f"Nothing urgent to use up. You can make {ready[0]['meal']} with what you have."
    else:
        message = "No full recipe can be made from current stock."

    out({"ok": True, "date": today().isoformat(), "expiring_items": sorted(soon), "message": message,
         "can_make_now": ready, "need_one_item": almost})


if __name__ == "__main__":
    main()
