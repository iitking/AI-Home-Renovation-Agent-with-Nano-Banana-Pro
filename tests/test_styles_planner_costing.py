import json
import tempfile
import unittest
from pathlib import Path

from renovation_agent.costing import RatesError, estimate_cost, list_rate_presets, load_rates
from renovation_agent.planner import PlanError, RenovationPlan, RoomPlanner, build_planner_prompt, parse_plan
from renovation_agent.report import build_report
from renovation_agent.styles import PRESERVE_RULES, build_render_prompt, list_styles
from helpers import GOOD_PLAN, FakeClient


class TestStyles(unittest.TestCase):
    def test_prompt(self):
        p = build_render_prompt("japandi", "bedroom", ["Repaint walls"], "need storage", "Be bold.")
        for s in ("japandi", "bedroom", "Repaint walls", "need storage", "Be bold.", PRESERVE_RULES):
            self.assertIn(s, p)

    def test_unknown(self):
        with self.assertRaises(ValueError):
            build_render_prompt("steampunk-castle")

    def test_listed(self):
        self.assertIn("scandinavian", list_styles())


class TestParsePlan(unittest.TestCase):
    def test_plain_and_fenced(self):
        raw = json.dumps(GOOD_PLAN)
        for text in (raw, f"```json\n{raw}\n```", f"Sure! Here it is:\n{raw}\nHope it helps"):
            plan = parse_plan(text)
            self.assertEqual(plan.room_type, "living room")
            self.assertEqual(len(plan.items), 4)

    def test_unknown_category_becomes_other(self):
        self.assertEqual(parse_plan(json.dumps(GOOD_PLAN)).items[3].category, "other")

    def test_malformed_items_skipped_and_qty_coerced(self):
        d = {"room_type": "kitchen", "items": [{"name": ""}, "junk", {"name": "Tiles", "category": "flooring", "quantity": "abc", "unit": "sqft"}]}
        plan = RenovationPlan.from_dict(d)
        self.assertEqual(len(plan.items), 1)
        self.assertEqual(plan.items[0].quantity, 1.0)

    def test_errors(self):
        for bad in ("", "no json here", "{broken", json.dumps({"items": []}), json.dumps({"room_type": "x", "items": "no"})):
            with self.assertRaises(PlanError):
                parse_plan(bad)

    def test_planner_calls_client(self):
        c = FakeClient()
        plan = RoomPlanner(c, "planner-model").analyze("IMG", "modern", "budget low")
        model, contents, config = c.planner_calls[0]
        self.assertEqual(model, "planner-model")
        self.assertEqual(contents[0], "IMG")
        self.assertIn("budget low", contents[1])
        self.assertEqual(config["response_mime_type"], "application/json")
        self.assertEqual(plan.room_type, "living room")

    def test_prompt_lists_categories(self):
        self.assertIn("flooring", build_planner_prompt("modern"))


class TestCosting(unittest.TestCase):
    def setUp(self):
        self.rates = load_rates()
        self.plan = parse_plan(json.dumps(GOOD_PLAN))

    def test_math(self):
        est = estimate_cost(self.plan, self.rates, contingency_pct=10)
        p = self.rates["rates"]["paint"]["rate"]
        l = self.rates["rates"]["lighting"]["rate"]
        c = self.rates["rates"]["carpentry"]["rate"]
        expected = round(400 * p + 3 * l + 8 * c, 2)
        self.assertEqual(est.subtotal, expected)
        self.assertEqual(est.contingency, round(expected * 0.10, 2))
        self.assertEqual(est.total, round(expected * 1.10, 2))
        self.assertEqual(len(est.lines), 3)

    def test_rate_presets(self):
        presets = list_rate_presets()
        self.assertIn("default", presets)
        self.assertIn("india-metro", presets)
        self.assertIn("us-standard", presets)
        us_rates = load_rates("us-standard")
        self.assertEqual(us_rates["currency"], "USD")
        metro_rates = load_rates("india-metro")
        self.assertEqual(metro_rates["currency"], "INR")

    def test_unpriced(self):
        est = estimate_cost(self.plan, self.rates)
        self.assertEqual(len(est.unpriced), 1)
        self.assertIn("Mystery work", est.unpriced[0])

    def test_unit_mismatch_is_unpriced_not_guessed(self):
        d = dict(GOOD_PLAN, items=[{"name": "Paint", "category": "paint", "quantity": 5, "unit": "unit"}])
        est = estimate_cost(parse_plan(json.dumps(d)), self.rates)
        self.assertEqual(est.subtotal, 0)
        self.assertIn("rate is per 'sqft'", est.unpriced[0])

    def test_negative_contingency(self):
        with self.assertRaises(RatesError):
            estimate_cost(self.plan, self.rates, -1)

    def test_custom_rates_file(self):
        p = Path(tempfile.mkdtemp()) / "r.json"
        p.write_text(json.dumps({"currency": "USD", "rates": {"paint": {"unit": "sqft", "rate": 2}}}))
        est = estimate_cost(self.plan, load_rates(p), 0)
        self.assertEqual((est.currency, est.subtotal), ("USD", 800))

    def test_bad_rates_file(self):
        p = Path(tempfile.mkdtemp()) / "r.json"
        p.write_text("{}")
        with self.assertRaises(RatesError):
            load_rates(p)
        with self.assertRaises(RatesError):
            load_rates(p.parent / "missing.json")

    def test_report(self):
        est = estimate_cost(self.plan, self.rates)
        md = build_report(self.plan, est, "modern", "original.png", ["design_1.png"])
        for s in ("# Renovation report", "design_1.png", "Repaint walls", "Not priced", "Total"):
            self.assertIn(s, md)


if __name__ == "__main__":
    unittest.main()
