### =========================================

# MODELO INTERNO PARA EL SISTEMA
# SE ENCARGA DE RECIBIR Y TRANSFORMAR EL INPUT.

### =========================================

### LIBRERIAS

from dataclasses import dataclass, field, asdict
from typing import Optional, List

## DATACLASS
from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class CompanyProfile:
    entity_type: Optional[str] = None
    age_months: Optional[int] = None
    industry: Optional[str] = None
    exports: Optional[bool] = None


@dataclass
class FinancialSnapshot:
    monthly_revenue: Optional[float] = None
    annual_revenue: Optional[float] = None
    govt_revenue_pct: Optional[float] = None
    revenue_drop_pct: Optional[float] = None
    cash: Optional[float] = None
    cash_in_90d: Optional[float] = None
    cash_out_90d: Optional[float] = None
    receivables: Optional[float] = None
    payables: Optional[float] = None
    client_concentration_pct: Optional[float] = None
    invoice_days: Optional[int] = None


@dataclass
class FinancingNeed:
    amount: Optional[float] = None
    urgency_days: Optional[int] = None
    use: Optional[str] = None
    preferred_term_days: Optional[int] = None


@dataclass
class RiskEligibility:
    credit_status: Optional[str] = None
    collateral: Optional[bool] = None
    eligible_invoices: Optional[bool] = None


@dataclass
class Documentation:
    bank_statements: Optional[bool] = None
    financial_statements: Optional[bool] = None


@dataclass
class CompanyCase:
    company: CompanyProfile = field(default_factory=CompanyProfile)
    financials: FinancialSnapshot = field(default_factory=FinancialSnapshot)
    need: FinancingNeed = field(default_factory=FinancingNeed)
    risk: RiskEligibility = field(default_factory=RiskEligibility)
    docs: Documentation = field(default_factory=Documentation)

    missing_fields: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)