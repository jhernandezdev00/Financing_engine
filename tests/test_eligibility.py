### IMPORTACIONES
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.normalizer import from_dict
from core.eligibility import check_eligibility, check_all
from config.lenders import LENDERS, get_lender

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


class TestEligibility(unittest.TestCase):
    def setUp(self):
        self.case = from_dict(COMPLETE_CASE_RAW)

    def test_impulso_capital_is_eligible(self):
        result = check_eligibility(self.case, get_lender("impulso_capital"))
        self.assertTrue(result.eligible)
        self.assertEqual(result.reasons, [])

    def test_tradebridge_rejected_when_no_exports(self):
        result = check_eligibility(self.case, get_lender("tradebridge"))
        self.assertFalse(result.eligible)
        self.assertTrue(any("exportación" in r for r in result.reasons))

    def test_colateral_plus_rejected_without_collateral(self):
        result = check_eligibility(self.case, get_lender("colateral_plus"))
        self.assertFalse(result.eligible)
        self.assertTrue(any("colateral" in r for r in result.reasons))

    def test_colateral_plus_still_rejected_after_adding_collateral_due_to_revenue(self):
        self.case.risk.collateral = True
        result = check_eligibility(self.case, get_lender("colateral_plus"))
        self.assertFalse(result.eligible)
        self.assertTrue(any("ingreso anual" in r for r in result.reasons))
        self.assertFalse(any("colateral" in r for r in result.reasons))

    def test_missing_critical_field_blocks_eligibility(self):
        self.case.financials.monthly_revenue = None
        result = check_eligibility(self.case, get_lender("impulso_capital"))
        self.assertFalse(result.eligible)
        self.assertIn("financials.monthly_revenue", result.missing_for_check)

    def test_reject_if_skips_when_field_missing(self):
        self.case.financials.govt_revenue_pct = None
        result = check_eligibility(self.case, get_lender("impulso_capital"))
        # debe seguir elegible: la condicion reject_if con on_missing=skip
        # no debe activarse solo porque el dato no vino
        self.assertTrue(result.eligible)

    def test_check_all_returns_one_result_per_lender(self):
        results = check_all(self.case, LENDERS)
        self.assertEqual(len(results), len(LENDERS))

    def test_rule_mutation_changes_outcome(self):
        """Simula 'FacturaYa ahora acepta facturas a 20 dias' (live challenge A)."""
        self.case.financials.invoice_days = 25
        facturaya = get_lender("facturaya")
        result_before = check_eligibility(self.case, facturaya)
        self.assertFalse(result_before.eligible)  # regla actual pide >=30

        mutated = dict(facturaya)
        mutated["eligibility"] = dict(facturaya["eligibility"])
        mutated["eligibility"]["requires"] = [
            {"field": "risk.eligible_invoices", "op": "is_true", "on_missing": "fail"},
            {"field": "financials.invoice_days", "op": ">=", "value": 20, "on_missing": "fail"},
        ]
        result_after = check_eligibility(self.case, mutated)
        self.assertTrue(result_after.eligible)


if __name__ == "__main__":
    unittest.main()
