import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from core.normalizer import from_json, from_csv
from core.decision_engine import decide
from config.lenders import LENDERS


st.set_page_config(page_title="Financing Recommendation System", layout="wide")

st.title("Financing Recommendation System")
st.caption(
    "Carga o pega los datos de una empresa para obtener una recomendación "
    "de financiamiento, con explicación y nivel de confianza."
)

# ---------------------------------------------------------------------------
# 1) Entrada de datos
# ---------------------------------------------------------------------------
st.header("1. Datos de la empresa")

input_format = st.radio("Formato de entrada", ["JSON", "CSV"], horizontal=True)

uploaded_file = st.file_uploader(
    f"Subir archivo .{input_format.lower()}",
    type=[input_format.lower()],
)

default_json = json.dumps({
    "company": {"entity_type": "PM", "age_months": 24, "industry": "manufacturing", "exports": False},
    "financials": {
        "monthly_revenue": 600000, "annual_revenue": 7200000, "govt_revenue_pct": 10,
        "revenue_drop_pct": 0, "cash": 200000, "cash_in_90d": 1200000, "cash_out_90d": 1500000,
        "receivables": 800000, "payables": 900000, "client_concentration_pct": 45, "invoice_days": 60,
    },
    "need": {"amount": 1000000, "urgency_days": 10, "use": "working_capital", "preferred_term_days": 90},
    "risk": {"credit_status": "good", "collateral": False, "eligible_invoices": True},
    "docs": {"bank_statements": True, "financial_statements": True},
}, indent=2, ensure_ascii=False)

raw_text = st.text_area(
    "...o pega el caso aquí directamente",
    value=default_json if input_format == "JSON" else "",
    height=280,
)

run_clicked = st.button("Evaluar caso", type="primary")

# ---------------------------------------------------------------------------
# 2) Procesamiento
# ---------------------------------------------------------------------------
if run_clicked:
    try:
        if uploaded_file is not None:
            content = uploaded_file.read().decode("utf-8")
        else:
            content = raw_text

        if not content.strip():
            st.error("No hay datos para procesar. Sube un archivo o pega el caso.")
            st.stop()

        case = from_json(content) if input_format == "JSON" else from_csv(content)
        result = decide(case)

    except Exception as e:
        st.error(f"No se pudo procesar el caso: {e}")
        st.stop()

    # -----------------------------------------------------------------------
    # 3) Resultado: recomendación primaria
    # -----------------------------------------------------------------------
    st.header("2. Recomendación")

    confidence_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}
    badge = confidence_color.get(result.confidence, "")

    if result.primary is None:
        st.error(
            "Ningún lender resultó elegible con los datos disponibles. "
            "Revisa los datos faltantes más abajo."
        )
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"Opción principal: {result.primary.lender_name}")
            st.write(result.primary.explanation)
        with col2:
            st.metric("Confianza", f"{badge} {result.confidence.upper()}")
            st.metric("Score de fit", f"{result.primary.score:.1f} / 100")

        if result.second_best:
            with st.expander(f"Segunda mejor opción: {result.second_best.lender_name} "
                              f"(score {result.second_best.score:.1f})"):
                st.write(result.second_best.explanation)
                st.caption("Drivers detallados:")
                for d in result.second_best.drivers:
                    st.markdown(f"- {d}")

    # -----------------------------------------------------------------------
    # 4) Por qué esta confianza
    # -----------------------------------------------------------------------
    st.subheader("¿Por qué este nivel de confianza?")
    for reason in result.confidence_reasons:
        st.markdown(f"- {reason}")

    if result.missing_critical_data:
        st.warning(
            "Datos críticos faltantes para la opción recomendada: "
            + ", ".join(result.missing_critical_data)
        )

    if result.data_contradictions:
        st.error("Contradicciones detectadas en los datos de entrada:")
        for c in result.data_contradictions:
            st.markdown(f"- {c}")

    # -----------------------------------------------------------------------
    # 5) Opciones rechazadas
    # -----------------------------------------------------------------------
    st.header("3. Opciones rechazadas")
    if not result.rejected:
        st.write("Ninguna — todos los lenders resultaron elegibles.")
    for r in result.rejected:
        with st.expander(f"{r.lender_name}"):
            for reason in r.reasons:
                st.markdown(f"- {reason}")

    # -----------------------------------------------------------------------
    # 6) Trazabilidad cruda (para usuarios avanzados / walkthrough)
    # -----------------------------------------------------------------------
    with st.expander("Ver trazabilidad completa (campos faltantes, datos crudos)"):
        st.write("**Todos los campos no informados en este caso:**")
        st.code(", ".join(result.all_missing_fields) or "Ninguno")
        st.write("**Lenders evaluados:**", ", ".join(l["name"] for l in LENDERS))