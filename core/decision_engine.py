### =========================================

# ORQUESTADOR

# SE ENCARGA DE DEVOLVER EL RESULTADO ESPERADO
#     - primary recommendation
#   - second-best recommendation
#   - rejected options con razones explícitas
#   - explicación concisa de los drivers principales
#   - confidence: high / medium / low
#   - missing critical data

# Solo coordina:
#   normalizer -> 
#   eligibility -> 
#   ranking -> 
#   confidence -> 
#   explanation

### IMPORTACIONES
from dataclasses import dataclass, field
from typing import List, Optional

from core.models import CompanyCase
from core.eligibility import check_all, EligibilityResult
from core.ranking import rank_eligible, FitResult
from core.confidence import assess_confidence, ConfidenceResult
from config.lenders import LENDERS, get_lender

## DATACLASS
@dataclass
class RejectedOption:
    lender_id: str
    lender_name: str
    reasons: List[str]


@dataclass
class RecommendedOption:
    lender_id: str
    lender_name: str
    score: float
    drivers: List[str]
    explanation: str


@dataclass
class DecisionResult:
    primary: Optional[RecommendedOption]
    second_best: Optional[RecommendedOption]
    rejected: List[RejectedOption]
    confidence: str
    confidence_reasons: List[str]
    missing_critical_data: List[str]
    all_missing_fields: List[str]
    data_contradictions: List[str]

#### FUNCIONES


def _lender_name(lender_id: str) -> str:
    return get_lender(lender_id)["name"]

def _build_explanation(fit: FitResult, eligibility_reasons_passed: bool) -> str:
    positive_drivers = [
        d for d in fit.drivers
        if not d.startswith(("uso '", "plazo preferido (", "monto solicitado (",
                              "urgencia alta (")) or
           any(kw in d for kw in ["coincide", "cae dentro", "cabe en", "puede operar rápido"])
    ]
    top_reasons = positive_drivers[:2] if positive_drivers else fit.drivers[:2]
    cleaned = [r[0].upper() + r[1:] for r in top_reasons if r]
    return ". ".join(cleaned) + "." if cleaned else "Mejor opción disponible entre los lenders elegibles."


def decide(case: CompanyCase, lenders: list = None) -> DecisionResult:
    lenders = lenders if lenders is not None else LENDERS

    eligibility_results: List[EligibilityResult] = check_all(case, lenders)
    ranked: List[FitResult] = rank_eligible(case, lenders, eligibility_results)
    confidence: ConfidenceResult = assess_confidence(case, lenders, eligibility_results, ranked)

    # --- Rechazados: todos los que NO fueron elegibles ---
    rejected = [
        RejectedOption(
            lender_id=r.lender_id,
            lender_name=_lender_name(r.lender_id),
            reasons=r.reasons,
        )
        for r in eligibility_results if not r.eligible
    ]

    def to_recommended(fit: FitResult) -> RecommendedOption:
        return RecommendedOption(
            lender_id=fit.lender_id,
            lender_name=_lender_name(fit.lender_id),
            score=fit.score,
            drivers=fit.drivers,
            explanation=_build_explanation(fit, eligibility_results),
        )

    primary = to_recommended(ranked[0]) if len(ranked) >= 1 else None
    second_best = to_recommended(ranked[1]) if len(ranked) >= 2 else None

    return DecisionResult(
        primary=primary,
        second_best=second_best,
        rejected=rejected,
        confidence=confidence.level,
        confidence_reasons=confidence.reasons,
        missing_critical_data=confidence.missing_critical,
        all_missing_fields=case.missing_fields,
        data_contradictions=case.contradictions,
    )