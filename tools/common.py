"""Shared helpers for the PantryPal tools.

Every tool reads and writes JSON files in the data folder and prints JSON,
so the agents in the Switch room can read the output easily.

Two environment variables help with testing and demos:
  PANTRY_DATA_DIR  use a different data folder (default: <repo>/data)
  PANTRY_TODAY     pretend today is this date, e.g. 2026-11-07
"""

import difflib
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------- paths and dates ----------

def data_dir() -> Path:
    return Path(os.environ.get("PANTRY_DATA_DIR", ROOT / "data"))


def today() -> date:
    value = os.environ.get("PANTRY_TODAY")
    return parse_date(value) if value else date.today()


def parse_date(value):
    if value in (None, ""):
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def nice_date(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}"


# ---------- JSON files ----------

def load(name, default=None):
    path = data_dir() / name
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(name, data):
    path = data_dir() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def out(payload, code=0):
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(message, **extra):
    out({"ok": False, "error": message, **extra}, code=1)


def settings():
    return load("settings.json", {"list_owner": "owner", "currency": "₹"})


def money(value) -> str:
    return f"{settings().get('currency', '₹')}{round(value):,}"


# ---------- pantry batches ----------
# A batch is one purchase: {"id", "name", "qty", "qty_bought", "unit",
# "expiry", "price", "added_by", "added_on"}. "price" is what the whole
# batch cost, so wasted value = price * qty_left / qty_bought.

def batches():
    return load("pantry.json", {"items": []})["items"]


def save_batches(items):
    save("pantry.json", {"items": items})


def is_expired(batch, on=None) -> bool:
    exp = parse_date(batch.get("expiry"))
    return exp is not None and exp < (on or today())


def stock(on=None):
    """Usable (not expired) quantity per item name: {name: (qty, unit)}."""
    totals = {}
    for b in batches():
        if b["qty"] > 0 and not is_expired(b, on):
            qty, _ = totals.get(b["name"], (0, b["unit"]))
            totals[b["name"]] = (round(qty + b["qty"], 3), b["unit"])
    return totals


def known_units():
    """The unit each item has been stored in before."""
    units = {}
    for b in batches():
        units.setdefault(b["name"], b["unit"])
    for s in load("staples.json", {"staples": []})["staples"]:
        units.setdefault(s["item"], s["unit"])
    return units


# ---------- item names ----------

def norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _variants(name):
    yield name
    yield name + "s"
    yield name + "es"
    if name.endswith("es"):
        yield name[:-2]
    if name.endswith("s"):
        yield name[:-1]


def resolve(name, known):
    """Match what a person typed ('egg', 'dal') to a known item name.

    Returns (match, suggestions). match is None when nothing fits clearly.
    """
    name = norm(name)
    known = sorted(set(known))
    for v in _variants(name):
        if v in known:
            return v, []
    contains = [k for k in known if any(v in k.split() or v == k for v in _variants(name))]
    if len(contains) == 1:
        return contains[0], []
    suggestions = contains or difflib.get_close_matches(name, known, n=3, cutoff=0.6)
    return None, suggestions


def fmt_qty(qty, unit):
    """2 L, 250 g, 12 (for pieces: "12 eggs" reads better than "12 pcs eggs")."""
    qty = round(qty, 3)
    if qty == int(qty):
        qty = int(qty)
    return f"{qty}" if unit == "pcs" else f"{qty} {unit}"


# ---------- history ----------

def log_event(kind, name, qty, unit, by, **extra):
    history = load("history.json", {"events": []})
    history["events"].append({
        "date": today().isoformat(),
        "type": kind,
        "item": name,
        "qty": qty,
        "unit": unit,
        "by": by,
        **extra,
    })
    save("history.json", history)
