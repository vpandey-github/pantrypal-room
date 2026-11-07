"""Weekly food-waste report: what went off, what it cost, and the trend.

Food counts as wasted when it expired unused, or when someone recorded
throwing it away with `pantry.py discard`. "This week" is the last 7 days
including today; "last week" is the 7 days before that.

Example:
  python3 tools/weekly_report.py
"""

import argparse
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import batches, fmt_qty, load, money, out, parse_date, today  # noqa: E402


def wasted_between(start, end):
    """Wasted items whose waste date falls in [start, end]."""
    rows = []
    for b in batches():
        bought = b.get("qty_bought") or b["qty"] or 1
        price = b.get("price") or 0
        exp = parse_date(b.get("expiry"))
        # Expired unused: wasted the day after its expiry date.
        if exp and b["qty"] > 0 and start <= exp + timedelta(days=1) <= end:
            rows.append({"item": b["name"], "qty": b["qty"], "unit": b["unit"],
                         "how": "expired", "date": (exp + timedelta(days=1)).isoformat(),
                         "value": round(price * b["qty"] / bought, 2)})
        # Thrown away on purpose.
        thrown_on = parse_date(b.get("wasted_on"))
        if b.get("wasted_qty") and thrown_on and start <= thrown_on <= end:
            rows.append({"item": b["name"], "qty": b["wasted_qty"], "unit": b["unit"],
                         "how": "thrown away", "date": thrown_on.isoformat(),
                         "value": round(price * b["wasted_qty"] / bought, 2)})
    rows.sort(key=lambda r: -r["value"])
    return rows


def main():
    p = argparse.ArgumentParser(description="Weekly food-waste report")
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args()

    end = today()
    start = end - timedelta(days=args.days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=args.days - 1)

    this_week = wasted_between(start, end)
    last_week = wasted_between(prev_start, prev_end)
    this_value = round(sum(r["value"] for r in this_week), 2)
    last_value = round(sum(r["value"] for r in last_week), 2)

    events = [e for e in load("history.json", {"events": []})["events"]
              if start <= parse_date(e["date"]) <= end]
    # "Mom" and "mom" are the same person (seed data vs. Mattermost usernames).
    updates_by = Counter(e["by"].strip().capitalize() for e in events if e["type"] in ("bought", "used"))
    approved = [lst for lst in load("approved_lists.json", {"lists": []})["lists"]
                if start <= parse_date(lst["date"]) <= end]

    if last_value > 0:
        change_pct = round((this_value - last_value) / last_value * 100)
        trend = "down" if this_value < last_value else "up" if this_value > last_value else "flat"
    else:
        change_pct, trend = None, "no data for last week"

    items_text = ", ".join(f"{fmt_qty(r['qty'], r['unit'])} {r['item']}" for r in this_week) or "nothing"
    message = f"This week: {len(this_week)} items wasted ({items_text}), about {money(this_value)}."
    if change_pct is not None:
        message += f" Last week: {money(last_value)}, so waste is {trend} {abs(change_pct)}%."
    if updates_by:
        message += " Updates logged: " + ", ".join(f"{who} {n}" for who, n in updates_by.most_common()) + "."

    out({
        "ok": True,
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        "message": message,
        "wasted_this_week": this_week,
        "wasted_value_this_week": this_value,
        "wasted_value_last_week": last_value,
        "change_percent": change_pct,
        "trend": trend,
        "updates_by_person": dict(updates_by),
        "shopping_lists_approved": len(approved),
    })


if __name__ == "__main__":
    main()
