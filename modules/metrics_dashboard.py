import sqlite3
import time
from typing import Dict, Any

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import pandas as pd
import json


class MetricsDashboard:
    """
    Dashboard de métricas en tiempo real para OSINT Framework
    """

    def __init__(self, user_id: int, db_manager):
        self.user_id = user_id
        self.db = db_manager

        # Métricas en caché
        self.cache = {}
        self.cache_ttl = 60  # segundos

    def get_overview_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas generales del usuario"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Total búsquedas
        cursor.execute('''
                       SELECT COUNT(*)
                       FROM searches
                       WHERE user_id = ?
                       ''', (self.user_id,))
        total_searches = cursor.fetchone()[0]

        # Targets únicos
        cursor.execute('''
                       SELECT COUNT(DISTINCT COALESCE(target_username, target_email, target_phone))
                       FROM searches
                       WHERE user_id = ?
                       ''', (self.user_id,))
        unique_targets = cursor.fetchone()[0]

        # Hallazgos totales
        cursor.execute('''
                       SELECT results
                       FROM searches
                       WHERE user_id = ?
                       ''', (self.user_id,))
        all_results = cursor.fetchall()

        total_findings = 0
        for result_row in all_results:
            if result_row[0]:
                result_data = json.loads(result_row[0])
                total_findings += sum(len(v) for v in result_data.values() if isinstance(v, list))

        # Tasa de éxito
        cursor.execute('''
                       SELECT COUNT(*)
                       FROM alerts
                       WHERE user_id = ?
                       ''', (self.user_id,))
        total_alerts = cursor.fetchone()[0]

        conn.close()

        return {
            "total_searches": total_searches,
            "unique_targets": unique_targets,
            "total_findings": total_findings,
            "total_alerts": total_alerts,
            "success_rate": (total_alerts / total_searches * 100) if total_searches > 0 else 0
        }

    def get_activity_timeline(self, days: int = 30) -> pd.DataFrame:
        """Obtiene actividad diaria para gráfico de líneas"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        start_date = datetime.now() - timedelta(days=days)

        cursor.execute('''
                       SELECT DATE (search_date) as date, COUNT (*) as count
                       FROM searches
                       WHERE user_id = ? AND search_date >= ?
                       GROUP BY DATE (search_date)
                       ORDER BY date
                       ''', (self.user_id, start_date.isoformat()))

        data = cursor.fetchall()
        conn.close()

        df = pd.DataFrame(data, columns=["date", "searches"])
        df["alerts"] = 0  # Placeholder para alertas

        return df

    def get_module_usage(self) -> Dict[str, int]:
        """Obtiene uso por módulo"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT results
                       FROM searches
                       WHERE user_id = ?
                       ''', (self.user_id,))

        results = cursor.fetchall()
        conn.close()

        module_counts = defaultdict(int)

        for result_row in results:
            if result_row[0]:
                result_data = json.loads(result_row[0])
                for module in result_data.keys():
                    module_counts[module] += 1

        return dict(module_counts)

    def get_alert_priority_distribution(self) -> Dict[str, int]:
        """Distribución de alertas por prioridad"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT alert_data
                       FROM alerts
                       WHERE user_id = ?
                       ''', (self.user_id,))

        alerts = cursor.fetchall()
        conn.close()

        priorities = []
        for alert_row in alerts:
            if alert_row[0]:
                alert_data = json.loads(alert_row[0])
                priorities.append(alert_data.get("priority", "MEDIA"))

        return dict(Counter(priorities))

    def get_top_targets(self, limit: int = 10) -> pd.DataFrame:
        """Targets más investigados"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT COALESCE(target_username, target_email, target_phone) as target,
                              COUNT(*) as count,
                MAX(search_date) as last_seen
                       FROM searches
                       WHERE user_id = ?
                       GROUP BY target
                       ORDER BY count DESC
                           LIMIT ?
                       ''', (self.user_id, limit))

        data = cursor.fetchall()
        conn.close()

        return pd.DataFrame(data, columns=["target", "investigations", "last_seen"])

    def get_performance_metrics(self) -> Dict[str, float]:
        """Métricas de performance: avg time, success rate"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Tiempo promedio por búsqueda (simulado)
        cursor.execute('''
                       SELECT COUNT(*)
                       FROM batch_searches
                       WHERE user_id = ?
                       ''', (self.user_id,))
        batch_count = cursor.fetchone()[0]

        conn.close()

        return {
            "avg_search_time": 45.2,  # Placeholder - implementar tracking real
            "success_rate": 87.5,
            "batch_completion_rate": 92.3,
            "modules_per_search": 2.1
        }

    def render_ui(self):
        """Renderiza dashboard completo"""
        st.header("📊 OSINT Framework Dashboard")

        # Auto-refresh cada 30 segundos
        if st.checkbox("Auto-refresh cada 30s", value=True):
            time.sleep(30)
            st.rerun()

        # Métricas principales
        st.subheader("🎯 Métricas Principales")

        metrics = self.get_overview_metrics()

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("🔍 Búsquedas Totales", metrics["total_searches"])

        with col2:
            st.metric("👤 Targets Únicos", metrics["unique_targets"])

        with col3:
            st.metric("📈 Hallazgos Totales", metrics["total_findings"])

        with col4:
            st.metric("🚨 Alertas Generadas", metrics["total_alerts"])

        with col5:
            st.metric("✅ Tasa Éxito", f"{metrics['success_rate']:.1f}%")

        # Gráficos
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Actividad Diaria")

            timeline_df = self.get_activity_timeline(days=30)

            fig = px.line(
                timeline_df,
                x="date",
                y="searches",
                title="Búsquedas por día",
                labels={"searches": "Búsquedas", "date": "Fecha"}
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("🎯 Distribución por Módulo")

            module_usage = self.get_module_usage()

            fig = px.pie(
                values=list(module_usage.values()),
                names=list(module_usage.keys()),
                title="Uso de Módulos"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Segunda fila de gráficos
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚨 Alertas por Prioridad")

            priority_dist = self.get_alert_priority_distribution()

            fig = px.bar(
                x=list(priority_dist.keys()),
                y=list(priority_dist.values()),
                title="Alertas por Nivel",
                labels={"x": "Prioridad", "y": "Cantidad"}
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("⚡ Performance")

            perf = self.get_performance_metrics()

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=perf["success_rate"],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Tasa Éxito (%)"},
                gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "darkblue"}}
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Tablas de datos
        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔝 Top Targets Investigados")

            top_targets = self.get_top_targets(limit=10)
            st.dataframe(top_targets, use_container_width=True)

        with col2:
            st.subheader("📊 Batch Recientes")

            batches = db.get_user_batch_searches(self.user_id, limit=5)
            batch_data = [{
                "Batch ID": batch[2][:8],
                "Targets": batch[3],
                "Fecha": batch[6][:10]
            } for batch in batches]

            st.dataframe(pd.DataFrame(batch_data), use_container_width=True)

        # Alertas recientes
        st.markdown("---")
        st.subheader("🔔 Alertas Recientes")

        recent_alerts = db.get_recent_alerts(self.user_id, limit=5)

        for alert in recent_alerts:
            data = json.loads(alert[5])

            with st.expander(f"{data['priority']} - {data['rule_name']}", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"Target: **{data['target']['value']}**")
                    st.json(data['changes'])

                with col2:
                    st.caption(f"⏰ {data['timestamp'][:19]}")

                    if st.button("Marcar leída", key=f"read_alert_{alert[0]}"):
                        db.mark_alert_read(alert[0])
                        st.rerun()

        # Exportar dashboard
        if st.button("📥 Exportar Dashboard como PDF"):
            pdf_data = self.generate_dashboard_pdf()
            st.download_button(
                label="Descargar PDF",
                data=pdf_data,
                file_name=f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

    def generate_dashboard_pdf(self) -> bytes:
        """Genera PDF del dashboard usando reportlab"""
        from utils.pdf_generator import PDFReport

        report = PDFReport(title="OSINT Framework Dashboard")

        report.add_title_page(
            investigator="System",
            target="Dashboard Overview",
            case_id=f"DASHBOARD-{datetime.now().strftime('%Y%m%d')}"
        )

        # Agregar métricas
        metrics = self.get_overview_metrics()
        report.add_executive_summary(
            findings_count=metrics["total_findings"],
            critical_findings=metrics["total_alerts"],
            modules_used=5
        )

        # Agregar gráficos
        module_usage = self.get_module_usage()
        report.add_chart(
            "bar",
            module_usage,
            "Uso de Módulos"
        )

        return report.generate()


# Integración en app.py
def render_dashboard():
    dashboard = MetricsDashboard(st.session_state.user["id"], db)
    dashboard.render_ui()


# Añadir a navbar
if st.button("📈 Dashboard"):
    st.session_state.page = "dashboard"
    st.rerun()