"""Tests for the PantryPal tools. Run with:  python3 -m unittest -v

Each test runs the real scripts against a fresh copy of the demo data in a
temporary folder, with "today" fixed so the results never change.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-11-06"


class PantryToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {**os.environ, "PANTRY_DATA_DIR": self.tmp.name, "PANTRY_TODAY": TODAY}
        self.run_script("scripts/seed.py", "--owner", "asha")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, script, *args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / script), *args],
                                env=self.env, capture_output=True, text=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["ok"], ok, msg=result.stdout + result.stderr)
        return data

    # ---- pantry.py ----

    def test_add_then_use_updates_stock(self):
        self.run_script("tools/pantry.py", "add", "--item", "Eggs", "--qty", "12",
                        "--expiry", "2026-11-20", "--price", "4.99", "--by", "Mom")
        data = self.run_script("tools/pantry.py", "use", "--item", "egg", "--qty", "4", "--by", "Dad")
        self.assertEqual(data["item"], "eggs")
        self.assertEqual(data["in_stock"], 14)

    def test_using_more_than_in_stock_is_refused(self):
        data = self.run_script("tools/pantry.py", "use", "--item", "eggs", "--qty", "10",
                               "--by", "Dad", ok=False)
        self.assertEqual(data["in_stock"], 6)

    def test_use_takes_soonest_expiry_first(self):
        self.run_script("tools/pantry.py", "add", "--item", "milk", "--qty", "2",
                        "--expiry", "2026-11-12", "--by", "Mom")
        self.run_script("tools/pantry.py", "use", "--item", "milk", "--qty", "0.5", "--by", "Mom")
        soon = self.run_script("tools/expiring.py", "--days", "2")
        self.assertNotIn("milk", [r["item"] for r in soon["expiring_soon"]])

    def test_wrong_unit_is_refused(self):
        self.run_script("tools/pantry.py", "add", "--item", "rice", "--qty", "500",
                        "--unit", "g", "--by", "Mom", ok=False)

    def test_unknown_item_suggests_names(self):
        data = self.run_script("tools/pantry.py", "use", "--item", "panir", "--qty", "1",
                               "--by", "Dad", ok=False)
        self.assertIn("paneer", data["did_you_mean"])

    # ---- expiring.py and meals.py ----

    def test_expiring_lists_tomorrows_items(self):
        data = self.run_script("tools/expiring.py", "--days", "1")
        self.assertEqual({r["item"] for r in data["expiring_soon"]}, {"spinach", "paneer"})

    def test_meals_put_expiring_food_first(self):
        data = self.run_script("tools/meals.py")
        self.assertEqual(data["can_make_now"][0]["meal"], "Palak paneer")

    # ---- shopping_list.py ----

    def test_draft_skips_items_in_stock(self):
        data = self.run_script("tools/shopping_list.py", "draft")
        to_buy = {i["item"] for i in data["to_buy"]}
        self.assertIn("milk", to_buy)
        self.assertNotIn("rice", to_buy)
        self.run_script("tools/pantry.py", "add", "--item", "milk", "--qty", "2",
                        "--expiry", "2026-11-10", "--by", "Mom")
        data = self.run_script("tools/shopping_list.py", "draft")
        self.assertNotIn("milk", {i["item"] for i in data["to_buy"]})

    def test_only_list_owner_can_approve(self):
        self.run_script("tools/shopping_list.py", "draft")
        self.run_script("tools/shopping_list.py", "approve", "--by", "Dad", ok=False)
        data = self.run_script("tools/shopping_list.py", "approve", "--by", "@Asha",
                               "--remove", "potatoes", "--add", "paneer:200:g")
        items = {i["item"] for i in data["items"]}
        self.assertNotIn("potatoes", items)
        self.assertIn("paneer", items)

    # ---- weekly_report.py ----

    def test_weekly_report_counts_waste_and_trend(self):
        data = self.run_script("tools/weekly_report.py")
        self.assertEqual(len(data["wasted_this_week"]), 3)
        self.assertAlmostEqual(data["wasted_value_this_week"], 3.06)
        self.assertAlmostEqual(data["wasted_value_last_week"], 9.2)
        self.assertEqual(data["trend"], "down")

    def test_discard_counts_as_waste(self):
        self.run_script("tools/pantry.py", "discard", "--item", "spinach", "--by", "Mom")
        data = self.run_script("tools/weekly_report.py")
        self.assertIn("spinach", [r["item"] for r in data["wasted_this_week"]])



    # ---- cook ----

    def test_cook_uses_every_ingredient(self):
        data = self.run_script("tools/pantry.py", "cook", "--meal", "palak paneer", "--by", "Mom")
        self.assertEqual(data["message"],
                         "Logged Palak paneer: used 250 g spinach, 200 g paneer, 1 onion, 2 tomatoes.")
        stock = {r["item"]: r["qty"] for r in self.run_script("tools/pantry.py", "list")["items"]}
        self.assertNotIn("spinach", stock)
        self.assertEqual(stock["onions"], 5)
        self.assertEqual(stock["tomatoes"], 1)

    def test_cook_short_ingredient_changes_nothing(self):
        self.run_script("tools/pantry.py", "cook", "--meal", "palak paneer", "--by", "Mom")
        data = self.run_script("tools/pantry.py", "cook", "--meal", "Palak Paneer", "--by", "Dad", ok=False)
        self.assertIn("spinach (need 250 g, have 0 g)", data["error"])
        stock = {r["item"]: r["qty"] for r in self.run_script("tools/pantry.py", "list")["items"]}
        self.assertEqual(stock["onions"], 5)  # unchanged by the failed cook

    def test_cook_unknown_meal(self):
        data = self.run_script("tools/pantry.py", "cook", "--meal", "pizza", "--by", "Dad", ok=False)
        self.assertIn("isn't one of our recipes", data["error"])


    def test_report_merges_name_case(self):
        self.run_script("tools/pantry.py", "use", "--item", "eggs", "--qty", "1", "--by", "mom")
        data = self.run_script("tools/weekly_report.py")
        self.assertEqual(data["updates_by_person"], {"Mom": 8, "Dad": 3})


    # ---- refused input ----

    def test_zero_quantity_and_past_expiry_are_refused(self):
        data = self.run_script("tools/pantry.py", "use", "--item", "eggs", "--qty", "0", "--by", "Dad", ok=False)
        self.assertIn("more than 0", data["error"])
        data = self.run_script("tools/pantry.py", "add", "--item", "milk", "--qty", "1", "--unit", "L",
                               "--expiry", "2026-11-01", "--by", "Mom", ok=False)
        self.assertIn("already in the past", data["error"])

    def test_approve_refuses_bad_or_negative_add(self):
        for bad in ("paneer:200", "paneer:lots:g", "tomatoes:-3:pcs"):
            self.run_script("tools/shopping_list.py", "approve", "--by", "asha", "--add", bad, ok=False)

    def test_approve_merges_duplicates_and_reports_unknown_removals(self):
        data = self.run_script("tools/shopping_list.py", "approve", "--by", "asha",
                               "--add", "tomatoes:2:pcs", "--remove", "pizza")
        tomatoes = [i for i in data["items"] if i["item"] == "tomatoes"]
        self.assertEqual(len(tomatoes), 1)
        self.assertEqual(tomatoes[0]["buy"], 10)
        self.assertEqual(data["not_found"], ["pizza"])
        self.assertIn("Not on the list, so not removed: pizza", data["message"])


if __name__ == "__main__":
    unittest.main()
