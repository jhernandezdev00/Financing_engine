### =========================================

# MOTOR DE RANKING

# SEÑALES DE FIT (CADA UNA SUMA O RESTA PUNTOS, 0-100 TOTAL):
#   1) USO PREFERIDO        -> ¿EL 'USE' DE LA EMPRESA ESTÁ EN PREFERRED_USE?
#   2) ALINEACIÓN DE PLAZO  -> ¿PREFERRED_TERM_DAYS CAE DENTRO DE TERM_ALIGNMENT_DAYS?
#   3) AJUSTE DE MONTO      -> ¿EL AMOUNT SOLICITADO CABE EN EL RANGO DEL LENDER?
#   4) URGENCIA VS VELOCIDAD -> LENDERS DE CICLO CORTO (TERM CORTO) PUNTÚAN MÁS
#                                CUANDO URGENCY_DAYS ES BAJO

### =========================================

### IMPORTACIONES
from dataclasses import dataclass
from typing import List, Optional

from core.models import CompanyCase
from core.eligibility import EligibilityResult


### PESOS
_WEIGHTS = {
    "use_match": 35,
    "term_alignment": 25,
    "amount_fit": 25,
    "urgency_speed": 15,
}

### DATACLASES
class FitResult:
    lender_id: str
    score: float
    drivers: List[str]


def _lender_amount_range(lender: dict, case: CompanyCase) -> Optional[tuple]:
    if "amount_range" in lender:
        return tuple(lender["amount_range"])

    kind = lender.get("amount_kind")
    pct_lo, pct_hi = lender.get("amount_pct_range", [0, 0])

    if kind == "pct_of_monthly_revenue":
        base = case.financials.monthly_revenue
    elif kind == "pct_of_invoice":
        base = case.financials.receivables
    elif kind == "pct_of_po":
        base = case.need.amount
    else:
        return None

    if base is None:
        return None
    return (base * pct_lo, base * pct_hi)

def _score_use_match(lender: dict, case: CompanyCase) -> tuple:
    preferred = lender.get("fit_signals", {}).get("preferred_use", [])
    use = case.need.use
    if use is None:
        return 0.0, "uso de la empresa no informado (sin puntos por match de uso)"
    if use in preferred:
        return _WEIGHTS["use_match"], f"uso '{use}' coincide con lo que atiende este lender"
    return 0.0, f"uso '{use}' no es el foco principal de este lender"


def _score_term_alignment(lender: dict, case: CompanyCase) -> tuple:
    align = lender.get("fit_signals", {}).get("term_alignment_days")
    preferred_term = case.need.preferred_term_days
    if not align or preferred_term is None:
        return 0.0, "plazo preferido no informado (sin puntos por alineación de plazo)"
    lo, hi = align
    if lo <= preferred_term <= hi:
        return _WEIGHTS["term_alignment"], (
            f"plazo preferido ({preferred_term}d) cae dentro del rango "
            f"típico de este lender ({lo}-{hi}d)"
        )
    distance = min(abs(preferred_term - lo), abs(preferred_term - hi))
    partial = max(0.0, _WEIGHTS["term_alignment"] - distance / 10)
    return partial, (
        f"plazo preferido ({preferred_term}d) fuera del rango típico "
        f"({lo}-{hi}d), puntaje parcial"
    )


def _score_amount_fit(lender: dict, case: CompanyCase) -> tuple:
    amount_range = _lender_amount_range(lender, case)
    requested = case.need.amount
    if amount_range is None or requested is None:
        return 0.0, "monto solicitado o rango del lender no disponible"

    lo, hi = amount_range
    full = _WEIGHTS["amount_fit"]

    if lo <= requested <= hi:
        return full, (
            f"monto solicitado ({requested:,.0f}) cabe en el rango del "
            f"lender ({lo:,.0f}-{hi:,.0f})"
        )

    if requested > hi * 3 or (lo > 0 and requested < lo * 0.3):
        penalty = -full
        return penalty, (
            f"desajuste EXTREMO de monto: solicitado ({requested:,.0f}) vs "
            f"rango del lender ({lo:,.0f}-{hi:,.0f}) — este lender no es "
            f"realista para este monto"
        )

    distance = (lo - requested) if requested < lo else (requested - hi)
    span = hi - lo if hi > lo else hi
    relative_distance = distance / span if span else 1.0
    partial = max(0.0, full * (1 - relative_distance))
    return partial, (
        f"monto solicitado ({requested:,.0f}) cerca pero fuera del rango "
        f"del lender ({lo:,.0f}-{hi:,.0f}), puntaje parcial"
    )

def _score_urgency_speed(lender: dict, case: CompanyCase) -> tuple:
    urgency = case.need.urgency_days
    term_range = lender.get("term_days_range")
    if urgency is None or not term_range:
        return 0.0, "urgencia no informada (sin puntos por velocidad)"
    min_term = term_range[0]
    if urgency <= 15 and min_term <= 15:
        return _WEIGHTS["urgency_speed"], (
            f"urgencia alta ({urgency}d) y este lender puede operar rápido "
            f"(mínimo {min_term}d)"
        )
    if urgency <= 15 and min_term > 15:
        return 0.0, (
            f"urgencia alta ({urgency}d) pero este lender requiere al menos "
            f"{min_term}d, no es el más rápido"
        )
    return _WEIGHTS["urgency_speed"] / 2, "urgencia no crítica, velocidad no es decisiva"


def score_fit(case: CompanyCase, lender: dict) -> FitResult:
    drivers = []
    total = 0.0

    for scorer in (_score_use_match, _score_term_alignment,
                   _score_amount_fit, _score_urgency_speed):
        points, reason = scorer(lender, case)
        total += points
        drivers.append(reason)

    return FitResult(lender_id=lender["id"], score=round(total, 1), drivers=drivers)


def rank_eligible(case: CompanyCase, lenders: list,
                   eligibility_results: List[EligibilityResult]) -> List[FitResult]:
    """
    Calcula fit SOLO para los lenders que pasaron elegibilidad, y los
    devuelve ordenados de mayor a menor score.
    """
    eligible_ids = {r.lender_id for r in eligibility_results if r.eligible}
    eligible_lenders = [l for l in lenders if l["id"] in eligible_ids]

    results = [score_fit(case, lender) for lender in eligible_lenders]
    results.sort(key=lambda r: r.score, reverse=True)
    return results
