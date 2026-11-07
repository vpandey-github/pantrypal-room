"""List food that expires soon, and food that has already expired.

Example:
  python3 tools/expiring.py --days 2
"""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import batches, fmt_qty, nice_date, out, parse_date, today  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Items expiring soon")
    p.add_argument("--days", type=int, default=2, help="look this many days ahead (default 2)")
    p.add_argument("--recent", type=int, default=3,
                   help="also list food that expired in the last N days (default 3)")
    args = p.parse_args()

    now = today()
    until = now + timedelta(days=args.days)
    soon, expired = [], []
    for b in batches():
        exp = parse_date(b.get("expiry"))
        if b["qty"] <= 0 or exp is None:
            continue
        row = {"item": b["name"], "qty": b["qty"], "unit": b["unit"], "expiry": exp.isoformat(),
               "days_left": (exp - now).days}
        if exp < now:
            if (now - exp).days <= args.recent:  # older waste is in the weekly report
                expired.append(row)
        elif exp <= until:
            soon.append(row)
    soon.sort(key=lambda r: r["expiry"])
    expired.sort(key=lambda r: r["expiry"])

    if soon:
        parts = []
        for r in soon:
            when = "today" if r["days_left"] == 0 else "tomorrow" if r["days_left"] == 1 else nice_date(parse_date(r["expiry"]))
            parts.append(f"{r['item']} ({fmt_qty(r['qty'], r['unit'])}, {when})")
        message = "Use soon: " + ", ".join(parts) + "."
    else:
        message = f"Nothing expires in the next {args.days} days."
    if expired:
        names = ", ".join(dict.fromkeys(r["item"] for r in expired))
        message += f" Already expired: {names}. If it was thrown away, tell me so I can log it."

    out({"ok": True, "date": now.isoformat(), "days": args.days, "message": message,
         "expiring_soon": soon, "already_expired": expired})


if __name__ == "__main__":
    main()
