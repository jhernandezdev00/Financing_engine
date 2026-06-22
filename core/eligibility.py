### =========================================

# MOTOR DE ELEGIBILIDAD

### =========================================

### IMPORTACIONES
from dataclasses import dataclass
from typing import Optional, Any, List

from core.models import CompanyCase

#### MAPEO

_OPS = {
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "is_true":  lambda a, b: a is True,
    "is_false": lambda a, b: a is False,
}

_FIELD_LABELS = {
    "company.exports": "operaciones de exportación",
    "company.age_months": "antigüedad de la empresa",
    "risk.collateral": "colateral disponible",
    "risk.eligible_invoices": "facturas elegibles",
    "financials.monthly_revenue": "ingreso mensual",
    "financials.annual_revenue": "ingreso anual",
    "financials.govt_revenue_pct": "% de ingresos por gobierno",
    "financials.revenue_drop_pct": "caída de ingresos",
    "financials.invoice_days": "ciclo de pago de facturas",
}

#### DATACLASE
@dataclass
class EligibilityResult:
    lender_id: str
    eligible: bool
    reasons: List[str]              # Motivo de Rechazo (vacío si elegible)
    missing_for_check: List[str]    # Campos que faltaron y no se pudieron evaluar


## FUNCIONES
def _describe_failed_condition(cond: dict, value, prefix: str) -> str:
    field = cond["field"]
    label = _FIELD_LABELS.get(field, field)
    op = cond["op"]

    if op == "is_true":
        return f"{prefix}: se requiere {label}, pero el valor actual es 'no'"
    if op == "is_false":
        return f"{prefix}: se requiere que NO aplique {label}, pero el valor actual es 'sí'"

    op_words = {">": "mayor a", ">=": "al menos", "<": "menor a",
                "<=": "como máximo", "==": "igual a", "!=": "distinto de"}
    target = cond.get("value")
    return (f"{prefix}: {label} debe ser {op_words.get(op, op)} {target} "
            f"(valor actual: {value})")

def _get_field(case: CompanyCase, path: str) -> Optional[Any]:
    "Resuelve 'financials.monthly_revenue' -> case.financials.monthly_revenue"
    namespace, field_name = path.split(".", 1)
    return getattr(getattr(case, namespace), field_name)

def _evaluate_condition(case: CompanyCase, condition: dict) -> Optional[bool]:
    value = _get_field(case, condition["field"])
    op = _OPS[condition["op"]]
    target = condition.get("value")

    return op(value, target) if value is not None else None

def check_eligibility(case: CompanyCase, lender: dict) -> EligibilityResult:
    reasons: List[str] = []
    missing: List[str] = []

    lender_id = lender["id"]
    elig = lender.get("eligibility", {})

    for cond in elig.get("requires", []):
        value = _get_field(case, cond["field"])

        if value is None:
            if cond.get("on_missing", "fail") == "fail":
                missing.append(cond["field"])

                reasons.append(cond["field"])

                reasons.append(
                    f"No se pudo confirmar requisitos: {cond['field']}"
                    f"(dato faltante)"
                )

            continue
            
        result = _OPS[cond["op"]](value, cond.get("value"))

        if not result:
            reasons.append(_describe_failed_condition(cond, value, "No cumple requisito"))
    
    for cond in elig.get("reject_if", []):
        value = _get_field(case, cond["field"])

        if value is None:
            if cond.get("on_missing", "skip") == "fail":
                missing.append(cond["field"])
                reasons.append(
                    f"No se pudo confirmar exclusión: {cond['field']} "
                    f"(dato faltante)"
                )
            continue
        result = _OPS[cond["op"]](value, cond.get("value"))
        if result:
            reasons.append(_describe_failed_condition(cond, value, "Rechazado por regla"))

    eligible = len(reasons) == 0
    return EligibilityResult(
        lender_id=lender_id,
        eligible=eligible,
        reasons=reasons,
        missing_for_check=missing,
    )

def check_all(case: CompanyCase, lenders: list) -> List[EligibilityResult]:
    return[check_eligibility(case, i) for i in lenders]

