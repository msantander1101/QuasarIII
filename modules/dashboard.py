import streamlit as st
import plotly.graph_objects as go
from collections import defaultdict
from app import db


def render_metrics_dashboard():
    st.header("📈 Dashboard de Métricas OSINT")

    # Métricas generales
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Búsquedas Totales",
        db.get_total_searches(st.session_state.user["id"])
    )

    col2.metric(
        "Targets Únicos",
        db.get_unique_targets_count(st.session_state.user["id"])
    )

    col3.metric(
        "Hallazgos Críticos",
        db.get_critical_findings_count(st.session_state.user["id"])
    )

    col4.metric(
        "Tasa de Éxito",
        f"{db.get_success_rate(st.session_state.user['id']):.1f}%"
    )

    # Gráfico de actividad temporal
    st.subheader("📅 Actividad Diaria")

    daily_activity = db.get_daily_activity(st.session_state.user["id"], days=30)

    fig = go.Figure(data=[
        go.Bar(x=[d["date"] for d in daily_activity],
               y=[d["count"] for d in daily_activity])
    ])
    fig.update_layout(title="Búsquedas por día", xaxis_title="Fecha", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

    # Top módulos utilizados
    st.subheader("🏆 Módulos Más Usados")

    module_usage = db.get_module_usage_stats(st.session_state.user["id"])

    fig2 = go.Figure(data=[
        go.Pie(labels=[m["module"] for m in module_usage],
               values=[m["count"] for m in module_usage])
    ])
    st.plotly_chart(fig2, use_container_width=True)

    # Alerts recientes
    st.subheader("🚨 Alertas Recientes")

    alerts = db.get_unread_alerts(st.session_state.user["id"], limit=5)
    for alert in alerts:
        with st.expander(f"🔔 {alert['title']}"):
            st.write(alert['message'])
            st.caption(f"Fecha: {alert['created_at']}")


# Añadir a navbar
if st.button("📈 Dashboard"):
    st.session_state.page = "dashboard"
    st.rerun()