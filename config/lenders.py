### =========================================

# CONFIGURACION DE LENDERS

#### ESTRUCUTURA DE CADA PRESTAMISTA

# id : identificador unico (snake_case)
# name : nombre
# product : tipo de producto financiero
# good_for : descripcion 

# eligibility:
#     requires        : lista de condiciones que deben cumplirse (hard filter)
#     reject_if       : lista de condiciones que, si se cumplen, RECHAZAN


#     Cada condición es un dict: {field, op, value}

#     field           : ruta dentro del CompanyCase, ej "financials.monthly_revenue"
#     op              : ">", ">=", "<", "<=", "==", "!=", "is_true", "is_false"
#     value           : valor de comparación (no aplica para is_true/is_false)
#     on_missing      : qué hacer si el campo no vino ("fail" | "skip")
#                        fail  -> ese requisito no se puede confirmar -> NO elegible
#                                 (pero se reporta como dato faltante, no como rechazo duro)
#                        skip  -> se ignora esa condición si falta el dato
#   amount_range    : [min, max] en MXN
#   term_days_range : [min, max] en días
#   fit_signals     : pistas usadas por el ranking engine para medir qué tan
#                     bien encaja

### =========================================


LENDERS = [
    {
        "id": "impulso_capital",
        "name": "Impulso Capital",
        "product": "term_loan",
        "good_for": "capital de trabajo general",
        "eligibility": {
            "requires": [
                {"field": "financials.monthly_revenue", "op": ">=",
                 "value": 150_000, "on_missing": "fail"},
                {"field": "company.age_months", "op": ">=",
                 "value": 12, "on_missing": "fail"},
            ],
            "reject_if": [
                {"field": "financials.govt_revenue_pct", "op": ">",
                 "value": 50, "on_missing": "skip"},
                {"field": "financials.revenue_drop_pct", "op": ">",
                 "value": 30, "on_missing": "skip"},
            ],
        },
        "amount_range": [500_000, 7_500_000],
        "term_days_range": [360, 720],  # 12-24 meses
        "fit_signals": {
            "preferred_use": ["working_capital"],
            "term_alignment_days": [360, 720],
        },
    },
    {
        "id": "linea_flex",
        "name": "Línea Flex",
        "product": "revolving_line",
        "good_for": "liquidez recurrente de corto plazo",
        "eligibility": {
            "requires": [
                {"field": "financials.monthly_revenue", "op": ">=",
                 "value": 400_000, "on_missing": "fail"},
                {"field": "company.age_months", "op": ">=",
                 "value": 12, "on_missing": "fail"},
            ],
            "reject_if": [
                {"field": "financials.govt_revenue_pct", "op": ">",
                 "value": 35, "on_missing": "skip"},
            ],
        },
        # Nota: monto depende de % del ingreso mensual, se resuelve en
        # ranking/engine con una función especial (ver amount_kind)
        "amount_kind": "pct_of_monthly_revenue",
        "amount_pct_range": [0.10, 0.35],
        "term_days_range": [15, 120],
        "fit_signals": {
            "preferred_use": ["working_capital"],
            "term_alignment_days": [15, 120],
        },
    },
    {
        "id": "facturaya",
        "name": "FacturaYa",
        "product": "factoring",
        "good_for": "problemas de timing en cuentas por cobrar",
        "eligibility": {
            "requires": [
                {"field": "risk.eligible_invoices", "op": "is_true",
                 "on_missing": "fail"},
                {"field": "financials.invoice_days", "op": ">=",
                 "value": 30, "on_missing": "fail"},
            ],
            "reject_if": [],
        },
        "amount_kind": "pct_of_invoice",
        "amount_pct_range": [0.85, 0.95],
        "term_days_range": [90, 180],
        "fit_signals": {
            "preferred_use": ["working_capital", "receivables"],
            "term_alignment_days": [90, 180],
        },
    },
    {
        "id": "tradebridge",
        "name": "TradeBridge",
        "product": "export_po_financing",
        "good_for": "exportación u operaciones cross-border",
        "eligibility": {
            "requires": [
                {"field": "company.exports", "op": "is_true",
                 "on_missing": "fail"},
            ],
            "reject_if": [],
        },
        "amount_kind": "pct_of_po",
        "amount_pct_range": [0.0, 0.50],
        "term_days_range": [90, 120],
        "fit_signals": {
            "preferred_use": ["export"],
            "term_alignment_days": [90, 120],
        },
    },
    {
        "id": "colateral_plus",
        "name": "Colateral Plus",
        "product": "secured_loan",
        "good_for": "financiamiento grande / largo plazo",
        "eligibility": {
            "requires": [
                {"field": "risk.collateral", "op": "is_true",
                 "on_missing": "fail"},
                {"field": "company.age_months", "op": ">=",
                 "value": 24, "on_missing": "fail"},
                {"field": "financials.annual_revenue", "op": ">=",
                 "value": 25_000_000, "on_missing": "fail"},
            ],
            "reject_if": [],
        },
        "amount_range": [2_000_000, 30_000_000],
        "term_days_range": [0, 1460],  # hasta 48 meses
        "fit_signals": {
            "preferred_use": ["working_capital", "expansion"],
            "term_alignment_days": [360, 1460],
        },
    },
]


###### =================================== 

# FUNCION PARA BUSQUEDA

###### ===================================

def get_lender(lender_id: str) -> dict:
    for lender in LENDERS:
        if lender["id"] == lender_id:
            return lender
    raise KeyError(f"Lender desconocido: {lender_id}")