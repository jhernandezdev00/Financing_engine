### IMPORTACIONES

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.normalizer import from_dict
from core.eligibility import check_all
from core.ranking import rank_eligible
from core.confidence import assess_confidence
from config.lenders import LENDERS


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

### CLASES

class TestRanking(unittest.TestCase):
    def setUp(self):
        self.case = from_dict(COMPLETE_CASE_RAW)
        self.elig = check_all(self.case, LENDERS)

    def test_ranked_only_includes_eligible(self):
        ranked = rank_eligible(self.case, LENDERS, self.elig)
        ranked_ids = {r.lender_id for r in ranked}
        self.assertNotIn("tradebridge", ranked_ids)      # rechazado (no exporta)
        self.assertNotIn("colateral_plus", ranked_ids)    # rechazado (sin colateral)

    def test_ranked_is_sorted_descending(self):
        ranked = rank_eligible(self.case, LENDERS, self.elig)
        scores = [r.score for r in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_extreme_amount_mismatch_is_penalized_below_partial_fit(self):
        ranked = rank_eligible(self.case, LENDERS, self.elig)
        scores = {r.lender_id: r.score for r in ranked}
        # linea_flex maneja montos pequeños (10-35% del ingreso mensual,
        # aprox 60k-210k), muy lejos del 1,000,000 solicitado -> penalizado
        self.assertLess(scores["linea_flex"], scores["impulso_capital"])


class TestConfidence(unittest.TestCase):
    def setUp(self):
        self.case = from_dict(COMPLETE_CASE_RAW)

    def _pipeline(self, case):
        elig = check_all(case, LENDERS)
        ranked = rank_eligible(case, LENDERS, elig)
        conf = assess_confidence(case, LENDERS, elig, ranked)
        return elig, ranked, conf

    def test_no_eligible_lenders_gives_low(self):
        self.case.financials.monthly_revenue = None
        self.case.risk.eligible_invoices = None
        self.case.company.exports = None
        self.case.risk.collateral = None
        _, ranked, conf = self._pipeline(self.case)
        self.assertEqual(conf.level, "low")

    def test_contradiction_blocks_high_confidence(self):
        self.case.contradictions.append("contradiccion simulada")
        _, _, conf = self._pipeline(self.case)
        self.assertEqual(conf.level, "low")

    def test_missing_critical_field_lowers_confidence(self):
        self.case.need.use = None
        self.case.missing_fields.append("need.use")
        _, _, conf = self._pipeline(self.case)
        self.assertIn(conf.level, ("medium", "low"))

    def test_confidence_level_is_valid(self):
        _, _, conf = self._pipeline(self.case)
        self.assertIn(conf.level, ("high", "medium", "low"))


if __name__ == "__main__":
    unittest.main()
