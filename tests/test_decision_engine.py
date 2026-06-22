### IMPORTACIONES
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.normalizer import from_dict, apply_partial_update
from core.decision_engine import decide

### CODIGO

COMPLETE_CASE_RAW = {
    "company": {"entity_type": "PM", "age_months": 24,
                "industry": "manufacturing", "exports": False},
    "financials": {"monthly_revenue": 600000, "annual_revenue": 7200000,
                   "govt_revenue_pct": 10, "revenue_drop_pct": 0,
                   "cash": 200000, "cash_in_90d": 1200000,
                   "cash_out_90d": 1500000, "receivables": 800000,
                   "payables": 900000, "client_concentration_pct": 45,
                   "invoice_days": 60},
    "need": {"amount": 1000000, "urgency_days": 10,
             "use": "working_capital", "preferred_term_days": 90},
    "risk": {"credit_status": "good", "collateral": False,
             "eligible_invoices": True},
    "docs": {"bank_statements": True, "financial_statements": True},
}


class TestDecisionEngine(unittest.TestCase):
    def test_decide_returns_primary_and_rejected(self):
        case = from_dict(COMPLETE_CASE_RAW)
        result = decide(case)
        self.assertIsNotNone(result.primary)
        self.assertTrue(len(result.rejected) > 0)
        self.assertIn(result.confidence, ("high", "medium", "low"))

    def test_rejected_reasons_are_human_readable(self):
        case = from_dict(COMPLETE_CASE_RAW)
        result = decide(case)
        rejected_names = {r.lender_name for r in result.rejected}
        self.assertIn("TradeBridge", rejected_names)
        tb = next(r for r in result.rejected if r.lender_name == "TradeBridge")
        self.assertTrue(any("exportación" in reason for reason in tb.reasons))
        self.assertFalse(any("is_true" in reason for reason in tb.reasons))

    def test_live_update_changes_recommendation(self):
        """Simula el live challenge tipo C: 'collateral becomes available'."""
        case = from_dict(COMPLETE_CASE_RAW)
        before = decide(case)
        rejected_before = {r.lender_id for r in before.rejected}
        self.assertIn("colateral_plus", rejected_before)

        apply_partial_update(case, {
            "risk": {"collateral": True},
            "financials": {"annual_revenue": 30_000_000},
        })
        after = decide(case)
        rejected_after = {r.lender_id for r in after.rejected}
        self.assertNotIn("colateral_plus", rejected_after)

    def test_no_eligible_lenders_returns_none_primary(self):
        raw = {"company": {"entity_type": "PM"}}
        case = from_dict(raw)
        result = decide(case)
        self.assertIsNone(result.primary)
        self.assertEqual(result.confidence, "low")


if __name__ == "__main__":
    unittest.main()
