"""Reset the demo data to a known starting state.

All dates are relative to today, so the demo looks the same whenever you
run it: spinach and paneer expire tomorrow, milk is running low, and
last week's waste is higher than this week's.

Usage:
  python3 scripts/seed.py --owner <your Mattermost username>
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from common import data_dir, save, today  # noqa: E402

# name, qty left, qty bought, unit, expiry (days from today), price ($ for the batch), added_by, added (days ago)
PANTRY = [
    # In stock now
    ("spinach", 250, 250, "g", 1, 3.49, "Mom", 3),
    ("paneer", 200, 200, "g", 1, 4.99, "Dad", 4),
    ("milk", 0.5, 1, "L", 2, 1.29, "Mom", 2),
    ("curd", 400, 400, "g", 3, 2.49, "Mom", 1),
    ("eggs", 6, 6, "pcs", 10, 2.49, "Dad", 3),
    ("bread", 6, 20, "slices", 2, 3.29, "Dad", 4),
    ("tomatoes", 3, 8, "pcs", 4, 3.99, "Mom", 5),
    ("onions", 6, 12, "pcs", 20, 4.49, "Mom", 6),
    ("potatoes", 2, 6, "pcs", 15, 2.99, "Mom", 6),
    ("bananas", 3, 6, "pcs", 2, 1.59, "Dad", 3),
    ("rice", 3, 5, "kg", 180, 12.99, "Mom", 12),
    ("toor dal", 0.4, 1, "kg", 120, 4.99, "Mom", 12),
    ("atta", 3, 5, "kg", 90, 9.99, "Mom", 12),
    ("poha", 0.5, 0.5, "kg", 60, 2.99, "Dad", 8),
    ("lemons", 2, 4, "pcs", 6, 2.00, "Mom", 5),
    ("carrots", 2, 4, "pcs", 5, 1.49, "Mom", 5),
    ("peas", 200, 250, "g", 3, 1.99, "Mom", 4),
    ("cooking oil", 0.3, 1, "L", 200, 4.99, "Mom", 20),
    # Wasted this week (expired unused)
    ("coriander", 1, 1, "bunch", -2, 0.99, "Mom", 6),
    ("curd", 200, 400, "g", -3, 2.49, "Mom", 9),
    ("bread", 5, 20, "slices", -5, 3.29, "Dad", 10),
    # Wasted last week (expired unused)
    ("spinach", 250, 250, "g", -10, 3.49, "Mom", 14),
    ("paneer", 100, 200, "g", -9, 4.99, "Dad", 13),
    ("tomatoes", 3, 8, "pcs", -12, 3.99, "Mom", 16),
    ("milk", 0.5, 1, "L", -11, 1.29, "Mom", 13),
    ("bananas", 4, 6, "pcs", -13, 1.59, "Dad", 17),
]

# item, minimum to keep, how much to buy, unit
STAPLES = [
    ("rice", 2, 5, "kg"),
    ("toor dal", 0.5, 1, "kg"),
    ("atta", 2, 5, "kg"),
    ("milk", 1, 2, "L"),
    ("eggs", 6, 12, "pcs"),
    ("onions", 4, 10, "pcs"),
    ("tomatoes", 4, 8, "pcs"),
    ("potatoes", 4, 6, "pcs"),
    ("bread", 4, 20, "slices"),
    ("curd", 200, 400, "g"),
    ("cooking oil", 0.5, 1, "L"),
]

# name, minutes, serves, [(item, qty, unit), ...]
RECIPES = [
    ("Palak paneer", 35, 3, [("spinach", 250, "g"), ("paneer", 200, "g"), ("onions", 1, "pcs"), ("tomatoes", 2, "pcs")]),
    ("Paneer bhurji", 20, 3, [("paneer", 200, "g"), ("onions", 1, "pcs"), ("tomatoes", 1, "pcs")]),
    ("Paneer paratha", 30, 3, [("atta", 0.3, "kg"), ("paneer", 150, "g")]),
    ("Dal palak", 30, 4, [("toor dal", 0.15, "kg"), ("spinach", 200, "g"), ("tomatoes", 1, "pcs")]),
    ("Dal tadka", 30, 4, [("toor dal", 0.15, "kg"), ("onions", 1, "pcs"), ("tomatoes", 1, "pcs")]),
    ("Egg bhurji", 15, 2, [("eggs", 4, "pcs"), ("onions", 1, "pcs"), ("tomatoes", 1, "pcs")]),
    ("Masala omelette", 10, 2, [("eggs", 3, "pcs"), ("onions", 1, "pcs")]),
    ("Bread omelette", 10, 2, [("eggs", 2, "pcs"), ("bread", 4, "slices")]),
    ("Banana milkshake", 5, 2, [("bananas", 2, "pcs"), ("milk", 0.5, "L")]),
    ("Jeera rice", 20, 3, [("rice", 0.2, "kg")]),
    ("Veg pulao", 30, 3, [("rice", 0.25, "kg"), ("carrots", 1, "pcs"), ("peas", 100, "g"), ("onions", 1, "pcs")]),
    ("Curd rice", 15, 2, [("rice", 0.15, "kg"), ("curd", 200, "g")]),
    ("Lemon rice", 20, 3, [("rice", 0.2, "kg"), ("lemons", 1, "pcs")]),
    ("Poha", 15, 3, [("poha", 0.15, "kg"), ("onions", 1, "pcs"), ("potatoes", 1, "pcs"), ("lemons", 1, "pcs")]),
    ("Aloo paratha", 40, 3, [("atta", 0.3, "kg"), ("potatoes", 3, "pcs")]),
    ("Tomato soup", 25, 3, [("tomatoes", 4, "pcs"), ("onions", 1, "pcs")]),
]

# days ago, type, item, qty, unit, by
HISTORY = [
    (6, "bought", "onions", 12, "pcs", "Mom"),
    (6, "bought", "potatoes", 6, "pcs", "Mom"),
    (5, "bought", "tomatoes", 8, "pcs", "Mom"),
    (4, "bought", "paneer", 200, "g", "Dad"),
    (4, "bought", "bread", 20, "slices", "Dad"),
    (3, "bought", "spinach", 250, "g", "Mom"),
    (3, "used", "potatoes", 4, "pcs", "Mom"),
    (2, "used", "bread", 14, "slices", "Dad"),
    (2, "used", "tomatoes", 5, "pcs", "Mom"),
    (1, "used", "onions", 6, "pcs", "Mom"),
]


def main():
    p = argparse.ArgumentParser(description="Reset PantryPal demo data")
    p.add_argument("--owner", default="owner",
                   help="Mattermost username of the person who approves the shopping list")
    args = p.parse_args()
    t = today()

    items = []
    for i, (name, qty, bought, unit, exp, price, by, ago) in enumerate(PANTRY, start=1):
        items.append({"id": i, "name": name, "qty": qty, "qty_bought": bought, "unit": unit,
                      "expiry": (t + timedelta(days=exp)).isoformat(), "price": price,
                      "added_by": by, "added_on": (t - timedelta(days=ago)).isoformat()})
    save("pantry.json", {"items": items})

    save("staples.json", {"staples": [
        {"item": n, "min": m, "buy": b, "unit": u} for n, m, b, u in STAPLES]})

    save("recipes.json", {"recipes": [
        {"name": n, "minutes": mins, "serves": s,
         "ingredients": [{"item": i, "qty": q, "unit": u} for i, q, u in ing]}
        for n, mins, s, ing in RECIPES]})

    save("history.json", {"events": [
        {"date": (t - timedelta(days=ago)).isoformat(), "type": k, "item": i, "qty": q, "unit": u, "by": by}
        for ago, k, i, q, u, by in HISTORY]})

    save("settings.json", {"list_owner": args.owner.lstrip("@"), "currency": "$"})
    save("approved_lists.json", {"lists": []})
    draft = data_dir() / "draft_list.json"
    if draft.exists():
        draft.unlink()

    print(f'{{"ok": true, "message": "Demo data reset for {t.isoformat()}. List owner: @{args.owner.lstrip("@")}."}}')


if __name__ == "__main__":
    main()
