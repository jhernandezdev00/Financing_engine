### =========================================

# MOTOR DE CONFIANZA

# SEÑALES CONSIDERADAS (EN ORDEN DE SEVERIDAD):
#   1) SIN NINGÚN LENDER ELEGIBLE            -> LOW (NO HAY NADA QUE RECOMENDAR)
#   2) CONTRADICCIONES EN LOS DATOS          -> NUNCA PERMITE HIGH
#   3) CAMPOS CRÍTICOS FALTANTES EN EL TOP   -> BAJA LA CONFIANZA SEGÚN CUÁNTOS
#   4) MARGEN ANGOSTO ENTRE TOP-1 Y TOP-2    -> BAJA LA CONFIANZA (DECISIÓN REÑIDA)
### =========================================

### IMPORTACIONES
from dataclasses import dataclass
from typing import List, Optional

from core.models import CompanyCase
from core.eligibility import EligibilityResult
from core.ranking import FitResult


# MARGEN
_NARROW_MARGIN_THRESHOLD = 10.0 


## DATACLASS
@dataclass
class ConfidenceResult:
    level: str                 
    reasons: List[str]
    missing_critical: List[str]  


def _missing_fields_for_lender(lender: dict, missing_fields: List[str]) -> List[str]:
    relevant_paths = set()
    for cond in lender.get("eligibility", {}).get("requires", []):
        relevant_paths.add(cond["field"])
    for cond in lender.get("eligibility", {}).get("reject_if", []):
        relevant_paths.add(cond["field"])

    relevant_paths.update({
        "need.use", "need.preferred_term_days",
        "need.amount", "need.urgency_days",
    })

    return [f for f in missing_fields if f in relevant_paths]


def assess_confidence(
    case: CompanyCase,
    lenders: list,
    eligibility_results: List[EligibilityResult],
    ranked: List[FitResult],
) -> ConfidenceResult:
    reasons: List[str] = []

    if not ranked:
        return ConfidenceResult(
            level="low",
            reasons=["Ningún lender resultó elegible con los datos disponibles"],
            missing_critical=case.missing_fields,
        )

    top = ranked[0]
    top_lender = next(l for l in lenders if l["id"] == top.lender_id)
    missing_critical = _missing_fields_for_lender(top_lender, case.missing_fields)

    has_contradictions = len(case.contradictions) > 0
    if has_contradictions:
        reasons.append(
            f"Se detectaron {len(case.contradictions)} contradicción(es) en "
            f"los datos de entrada"
        )

    n_missing = len(missing_critical)
    if n_missing > 0:
        reasons.append(
            f"{n_missing} dato(s) crítico(s) para evaluar '{top.lender_id}' "
            f"no fueron informados: {', '.join(missing_critical)}"
        )

    margin = None
    if len(ranked) >= 2:
        margin = round(ranked[0].score - ranked[1].score, 1)
        if margin < _NARROW_MARGIN_THRESHOLD:
            reasons.append(
                f"El margen entre la opción top ('{ranked[0].lender_id}', "
                f"score {ranked[0].score}) y la segunda mejor "
                f"('{ranked[1].lender_id}', score {ranked[1].score}) es "
                f"estrecho ({margin} pts) -- la decisión es ajustada"
            )

    if has_contradictions or n_missing >= 2 or not ranked:
        level = "low"
    elif n_missing == 1 or (margin is not None and margin < _NARROW_MARGIN_THRESHOLD):
        level = "medium"
    else:
        level = "high"

    if not reasons:
        reasons.append(
            "Datos completos para la opción recomendada, sin contradicciones "
            "y margen claro frente a la segunda mejor opción"
        )

    return ConfidenceResult(
        level=level,
        reasons=reasons,
        missing_critical=missing_critical,
    )