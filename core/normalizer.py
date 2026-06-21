### =========================================

# NORMALIZACION DE ENTRADAS
# SE TOMAN LOS DATOS CRUDOS Y SE ENCARGA DE PRODUCIR 
# UNA CLASE "COMPANYCASE" CONSISTENTE COMO ENTRADA DE LA INFORMACION

### =========================================

### LIBRERIAS
import json
import csv
import io
from dataclasses import fields
from typing import Optional

from core.models import (
    CompanyCase, CompanyProfile, FinancialSnapshot,
    FinancingNeed, RiskEligibility, Documentation,
)


#### ====== MAPEA CADA SUB-MODULO A SU "NAMESPACE" ESPERADO EN EL JSON
_SUBMODELS = {
    "company": CompanyProfile,
    "financials": FinancialSnapshot,
    "need": FinancingNeed,
    "risk": RiskEligibility,
    "docs": Documentation,
}

_BOOL_TRUE = {"true", "1", "yes", "si", "sí", "y"}
_BOOL_FALSE = {"false", "0", "no", "n"}

def _coerce(value):
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()

        if v == "":
            return None
        
        low = v.lower()

        if low in _BOOL_TRUE:
            return True
        if low in _BOOL_FALSE:
            return False
        
        try:
            if "." in v:
                return float(v)
            return int(v)
        except ValueError:
            return v   
    return value

def from_dict(raw: dict) -> CompanyCase:
    case = CompanyCase()
    missing = []


    for namespace, model_cls in _SUBMODELS.items():
        section = raw.get(namespace, {}) or {}
        instance = getattr(case, namespace)

        for f in fields(model_cls):
            if f.name in section:
                setattr(instance, f.name, _coerce(section[f.name]))
            else:
                missing.append(f"{namespace}.{f.name}")
        
        case.missing_fields = missing
        case.contradictions = _detect_contradictions(case)
        return case 

def from_json(raw_json: str) -> CompanyCase:
    return from_dict(json.loads(raw_json))

def from_csv(raw_csv: str) -> CompanyCase:
    reader = csv.DictReader(io.StringIO(raw_csv))
    row = next(reader, None)
    if row is None:
        raise ValueError("CSV vacío: no se encontró ninguna fila de datos")

    nested = {}
    for key, value in row.items():
        if "." not in key:
            continue  # columna no reconocida, se ignora silenciosamente
        namespace, field_name = key.split(".", 1)
        nested.setdefault(namespace, {})[field_name] = value

    return from_dict(nested)

def apply_partial_Update(case: CompanyCase, updates: dict) -> CompanyCase:
    for namespace, model_cls in _SUBMODELS.items():
        section = updates.get(namespace)
        if not section:
            continue
        instance = getattr(case, namespace)
        for f in fields(model_cls):
            if f.name in section:
                setattr(instance, f.name, _coerce(section[f.name]))
                missing_key = f"{namespace}.{f.name}"
                if missing_key in case.missing_fields:
                    case.missing_fields.remove(missing_key)

    case.contradictions = _detect_contradictions(case)
    return case

def _detect_contradictions(case: CompanyCase) -> list:
    issues = []
    fin = case.financials
    risk = case.risk
    need = case.need

    ##### ===========================
    # Ingreso Mensual * 12 (Aprox. Ingreso Anual)
    #### ===========================

    if fin.monthly_revenue is not None and fin.annual_revenue is not None:
        implied = fin.monthly_revenue * 12

        if fin.annual_revenue > 0:
            delta_pct = abs(implied - fin.annual_revenue) / fin.annual_revenue

            if delta_pct > 0.25:

                issues.append(
                    f"Ingreso Mensual x 12 ({implied:,.0f} difiere) "
                    f"> 25% del ingreso_anual ({fin.annual_revenue:.0f})"
                )

    ##### ===========================
    # Facturas elegibles pero sin ciclo de pago informado
    #### ===========================

    if risk.eligible_invoices is True and fin.invoice_days is None:
        issues.append(
            "facturas_elegibles=True pero días_factura no fue informado"
        )

    ##### ===========================
    # Urgencia no positiva
    #### ===========================    
    if need.urgency_days is not None and need.urgency_days <= 0:
        issues.append(f"días_urgencia inválido: {need.urgency_days}")

    ##### ===========================
    # Concentración de cliente fuera de rango lógico
    #### =========================== 

    if fin.client_concentration_pct is not None:
        if not (0 <= fin.client_concentration_pct <= 100):
            issues.append(
                f"porcentaje_concentración_cliente fuera de rango: "
                f"{fin.client_concentration_pct}"
            )

    ##### ===========================
    # Caida de ingresos negativa (debería ser >=0, una caída no es negativa)
    #### =========================== 
    if fin.revenue_drop_pct is not None and fin.revenue_drop_pct < 0:
        issues.append(f"porcentaje_caída_ingresos negativo: {fin.revenue_drop_pct}")

    return issues