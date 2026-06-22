### IMPORTACIONES
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models import CompanyCase
from core.normalizer import from_dict, from_json, from_csv, apply_partial_update

### CLASES
class TestModels(unittest.TestCase):
    def test_empty_case_has_all_none(self):
        case = CompanyCase()
        self.assertIsNone(case.company.entity_type)
        self.assertIsNone(case.financials.monthly_revenue)
        self.assertEqual(case.missing_fields, [])
        self.assertEqual(case.contradictions, [])


class TestNormalizer(unittest.TestCase):
    def setUp(self):
        self.complete_raw = {
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

    def test_complete_case_has_no_missing_fields(self):
        case = from_dict(self.complete_raw)
        self.assertEqual(case.missing_fields, [])
        self.assertEqual(case.contradictions, [])

    def test_missing_fields_are_tracked(self):
        raw = {"company": {"entity_type": "PM"}}
        case = from_dict(raw)
        self.assertIn("company.age_months", case.missing_fields)
        self.assertIn("financials.monthly_revenue", case.missing_fields)

    def test_from_json_matches_from_dict(self):
        import json
        case = from_json(json.dumps(self.complete_raw))
        self.assertEqual(case.financials.monthly_revenue, 600000)

    def test_from_csv_basic(self):
        csv_text = (
            "company.entity_type,company.age_months,financials.monthly_revenue\n"
            "PM,24,600000"
        )
        case = from_csv(csv_text)
        self.assertEqual(case.company.entity_type, "PM")
        self.assertEqual(case.company.age_months, 24)
        self.assertEqual(case.financials.monthly_revenue, 600000.0)

    def test_csv_empty_raises(self):
        with self.assertRaises(ValueError):
            from_csv("company.entity_type,company.age_months\n")

    def test_contradiction_revenue_mismatch(self):
        raw = dict(self.complete_raw)
        raw["financials"] = dict(raw["financials"])
        raw["financials"]["annual_revenue"] = 200000  # muy distinto de monthly*12
        case = from_dict(raw)
        self.assertTrue(any("ingreso_anual" in c for c in case.contradictions))

    def test_contradiction_eligible_invoices_without_invoice_days(self):
        raw = dict(self.complete_raw)
        raw["financials"] = dict(raw["financials"])
        del raw["financials"]["invoice_days"]
        case = from_dict(raw)
        self.assertTrue(any("días_factura" in c for c in case.contradictions))

    def test_apply_partial_update_changes_value_and_clears_missing(self):
        case = from_dict({"company": {"entity_type": "PM"}})
        self.assertIn("risk.collateral", case.missing_fields)
        apply_partial_update(case, {"risk": {"collateral": True}})
        self.assertTrue(case.risk.collateral)
        self.assertNotIn("risk.collateral", case.missing_fields)


if __name__ == "__main__":
    unittest.main()
