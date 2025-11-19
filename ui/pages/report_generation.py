# ui/pages/report_generation.py
import os
from datetime import datetime

import streamlit as st
from modules.reporting.pdf_generator import generate_pdft_report, example_generate_report
from modules.search.central_search import execute_search
from modules.ai.intelligence_core import ai_analyzer, initialize_ai_analyzer
from core.config_manager import config_manager
from core.db_manager import get_user_by_id  # Para mostrar nombre real
import logging

logger = logging.getLogger(__name__)


# Función para crear estructura de datos para reporte
def prepare_report_structure(data: dict, user_id: int) -> list:
    """
    Convierte resultado de búsqueda en una estructura adecuada para reporte.
    Esta función puede adaptarse para diferentes tipos de datos (persona, relación, etc.).

    :param data: Resultados de búsqueda obtenidos desde central_search
    :param user_id: ID del usuario para buscar datos del perfil

    :returns: Lista de bloques de contenido para insertar en PDF.
    """
    blocks = []

    blocks.append({"type": "heading", "content": "Resumen del Informe OSINT"})

    # Encabezado básico
    try:
        user = get_user_by_id(user_id)
        if user:
            username = user[1]  # Suponiendo que user[1] es username
        else:
            username = "Usuario Desconocido"
    except Exception:
        username = "Usuario Desconocido"

    blocks.append({"type": "paragraph", "content": f"Este informe fue generado automágicamente por el sistema. \
                   Autor del análisis: {username}. Generado el {st.session_state.get('current_timestamp', 'Desconocido')}."})

    # Si hay resultados de búsqueda centrada
    if data and isinstance(data, dict):
        blocks.append({"type": "heading", "content": "Información Recopilada"})
        for source_type, result in data.items():
            blocks.append({"type": "heading", "content": f"Fuente {source_type}"})
            if isinstance(result, dict) and "error" in result:
                blocks.append({"type": "paragraph", "content": f"[Error]: {result.get('error', 'No especificado')}."})
            elif isinstance(result, list):
                # Ejemplo simple para listas:
                for idx, item in enumerate(result[:5]):  # Solo los primeros cinco para evitar overflow
                    if isinstance(item, dict):
                        txt = ", ".join([f"{k}: {v}" for k, v in item.items()])[:300] + (
                            "..." if len(txt) > 300 else "")
                        blocks.append({"type": "paragraph", "content": f"{idx + 1}. {txt}"})
                    else:
                        blocks.append({"type": "paragraph", "content": f"{idx + 1}. {str(item)[:300]}"})
            else:
                blocks.append({"type": "paragraph", "content": str(result)[0:500] + "..."})
    else:
        blocks.append({"type": "paragraph", "content": "No hay datos para reportar en esta sección."})

    return blocks


def show_report_generation_page():
    """
    Interfaz para generar reportes.
    """

    st.subheader("📄 Generador de Reportes PDF")

    user_id = st.session_state.get('current_user_id')
    if not user_id:
        st.error("No se puede generar reportes sin sesión activa.")
        return

    # Opción 1: Ejemplo de reporte pregenerado (prueba)
    if st.button("🔍 Generar Reporte de Ejemplo"):
        try:
            # Usar función interna para obtener datos del reporte
            # En una app real, esto podría ir en `central_search.py` y pasar aquí el resultado
            temp_data = {
                "demo": [{"name": "Persona1"}, {"name": "Persona2"}]
            }
            report_path = generate_pdft_report(
                filename="reporte_demo",
                title="Reporte Demo",
                author="Sistema",
                content_data=prepare_report_structure(temp_data, user_id),
                cover_text="Este es un reporte de muestra para verificar funcionalidad."
            )
            st.success("✅ Reporte generado con éxito.")
            # Mostrar botón para descargar
            with open(report_path, "rb") as file:
                btn = st.download_button(label="📥 Descargar Reporte PDF",
                                         data=file,
                                         file_name=os.path.basename(report_path),
                                         mime="application/pdf")
        except Exception as e:
            st.error(f"❌ Error generando reporte de ejemplo: {str(e)}")

    # Opción 2: Crear reporte basado en búsqueda
    st.markdown("### Generar Reporte Personalizado")

    query = st.text_input("Ingrese término de búsqueda para generar informe:", key="report_search_term")

    available_sources = [
        "general", "web", "social", "people", "pastes",
        "breaches", "emails", "domains", "archives", "darkweb",
        "images", "geo", "public_data", "crypto", "communications",
        "mobile", "phones", "documents"
    ]

    selected_sources = st.multiselect("Fuentes para análisis", available_sources)

    # Botón para ejecutar búsqueda centralizada Y generar reporte
    if st.button("🚀 Generar Reporte desde Búsqueda") and query and selected_sources:
        st.info("Iniciando búsqueda y análisis...")

        # Primero, verificar si tenemos acceso a IA
        api_key = config_manager.get_config(user_id, "openai_api_key")
        if api_key:
            initialize_ai_analyzer(api_key)
            st.info("✓ Sistema de IA iniciado con clave proporcionada.")
        else:
            st.warning("⚠️ Clave API de OpenAI no detectada. Reporte sin análisis IA.")
            initialize_ai_analyzer(None)  # Inicializa desactivado

        # Luego, ejecuta búsqueda
        try:
            search_results = execute_search(query, selected_sources)
            st.success("✓ Búsqueda completada.")

            # Generaría una vista de resultados en UI si lo deseas, pero ahora lo usamos para reporte

            # Preparar estructura de archivo de reporte
            report_blocks = prepare_report_structure(search_results, user_id)

            # Ahora genera el PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = generate_pdft_report(
                filename=f"reporte_{query}_{timestamp}",  # Asegura nombres únicos, incluso con espacios
                title="Informe de Análisis OSINT",
                author="Usuario",
                content_data=report_blocks,
                cover_text=f"Análisis sobre: '{query}' usando fuentes: {', '.join(selected_sources)}",
                output_dir="reports"
            )

            st.success("✅ Reporte generado con éxito.")
            # Mostrar botón para descarga
            with open(report_path, "rb") as file:
                btn = st.download_button(label="📥 Descargar Reporte PDF",
                                         data=file,
                                         file_name=os.path.basename(report_path),
                                         mime="application/pdf")
        except Exception as e:
            st.error(f"❌ Error durante generación de reporte: {str(e)}")
            logger.error(f"Error detallado en generación de reporte: {e}")

    # Opción 3: Si la IA está activa, puedes hacer análisis del resultado actual
    if ai_analyzer and ai_analyzer.is_active:
        st.markdown("---")
        st.subheader("🧠 Análisis de Información con IA")
        analysis_input_text = st.text_area("Introducir texto para análisis con IA:",
                                           placeholder="Por ejemplo, una descripción de persona o grupo de datos...",
                                           height=100)
        if st.button("💡 Analizar con IA") and analysis_input_text:
            if len(analysis_input_text) < 10:  # Evitar entradas muy cortas
                st.warning("⚠️ Texto muy corto para análisis IA.")
            else:
                # Ejemplo: Resumen
                summary = ai_analyzer.summarize_text(analysis_input_text)
                st.write("**Resumen IA:**")
                st.markdown(summary)

                # Ejemplo: Clasificación
                categories = ["personal", "profesional", "financiera", "medica", "ubicacion"]
                classification = ai_analyzer.classify_information(analysis_input_text, categories)
                st.write("**Clasificación IA:**")
                st.json(classification)

                # Ejemplo: Detección de datos sensibles
                sensitive_detected = ai_analyzer.detect_sensitive_data(analysis_input_text)
                st.write("**Datos Sensibles Detectados:**")
                for dt in sensitive_detected[:3]:
                    st.json(dt)  # Solo muestra hasta tres

                st.info("✅ Ejemplo de análisis IA integrado.")
    else:
        st.info("AI aún desactivada (falta clave OpenAI). Agrega una API key en config.")

    # Botón para volver al dashboard
    if st.button(" ← Volver al Dashboard"):
        st.session_state['page'] = 'dashboard'
        st.session_state['force_reload'] = True
        st.rerun()