"""
UI Orchestrator for Person Search (Streamlit)
Versión final limpia, profesional y controlada.
"""

import time
import logging
import os
from typing import List

import streamlit as st

from modules.search.advanced_search import search_multiple_sources
from utils.dorks_upload import save_uploaded_dorks

# Componentes UI
from .components.person_card import render_person_card
from .components.socmint_block import render_socmint_block
from .components.web_email_blocks import render_web_block, render_email_block
from .components.darkweb_block import render_darkweb_block
from .components.dorks_block import render_dorks_block

logger = logging.getLogger(__name__)

# ------------------ Helpers ------------------


def _normalize_sources(selected: List[str]) -> List[str]:
    if not selected:
        return ["people", "email", "social"]
    if "all" in selected:
        return ["people", "email", "social", "web", "darkweb", "dorks"]
    return selected


# ------------------ MAIN UI ------------------


def show_person_search_ui():
    st.markdown("""
    <div style="background:linear-gradient(135deg,#3a7bd5,#004e92);
                padding:18px;border-radius:12px;margin-bottom:20px">
        <h1 style="color:white;margin:0">🧠 Person Intelligence Search</h1>
        <p style="color:#dce6ff;margin-top:8px">
            OSINT • SOCMINT • Email • Web — ejecución bajo demanda
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ------------------ INPUTS ------------------
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("👤 Nombre completo", key="ps_name")
        username = st.text_input("🧩 Username (SOCMINT)", key="ps_username")

    with col2:
        email = st.text_input("📧 Email", key="ps_email")
        domain = st.text_input("🌐 Dominio", key="ps_domain")

    sources = st.multiselect(
        "🗂 Fuentes a consultar",
        options=["all", "people", "email", "social", "web", "darkweb", "dorks"],
        default=["people", "email", "social"]
    )

    # ------------------ ADVANCED OPTIONS ------------------
    with st.expander("⚙️ Opciones avanzadas", expanded=False):
        st.markdown("#### 🕵️‍♂️ Google Dorks personalizados")

        uploaded_dorks = st.file_uploader(
            "Sube un archivo de dorks (.txt o .json)",
            type=["txt", "json"],
            help="TXT: un dork por línea | JSON: { default: [...], email: [...], etc }"
        )

        dorks_file = None
        user_id = st.session_state.get("user_id", 1)

        if uploaded_dorks:
            dorks_file = save_uploaded_dorks(
                user_id=user_id,
                uploaded_file=uploaded_dorks
            )
            if dorks_file:
                st.success(f"Archivo cargado correctamente: {uploaded_dorks.name}")
            else:
                st.error("El archivo de dorks no es válido")

        # Fallback: variable de entorno
        if not dorks_file:
            dorks_file = os.getenv("QUASAR_DORKS_FILE")

        if dorks_file:
            st.caption(f"📄 Dorks activos: `{os.path.basename(dorks_file)}`")

    # ------------------ ACTIONS ------------------
    cta1, cta2 = st.columns(2)

    with cta1:
        if st.button("🔍 Ejecutar búsqueda", use_container_width=True):
            query = name or email or domain or username
            if not query:
                st.warning("Introduce al menos un criterio de búsqueda")
                return

            try:
                with st.spinner("Ejecutando búsqueda OSINT..."):
                    res = search_multiple_sources(
                        query=query,
                        selected_sources=_normalize_sources(sources),
                        email=email or "",
                        username=username or None,
                        dorks_file=dorks_file or None,
                        user_id=user_id,
                    )

                st.session_state["ps_results"] = res
                st.session_state["ps_time"] = time.time()
                st.success("Búsqueda finalizada")

            except Exception as e:
                logger.exception("Person search error")
                st.error(f"Error ejecutando búsqueda: {e}")

    with cta2:
        if st.button("🧹 Limpiar", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k.startswith("ps_"):
                    st.session_state.pop(k)
            st.rerun()

    # ------------------ RESULTS ------------------
    results = st.session_state.get("ps_results")
    if not results:
        st.info("Configura los parámetros y ejecuta la búsqueda.")
        return

    st.markdown("---")
    st.subheader("📊 Resultados")

    # ========== SOCMINT ==========
    social = results.get("social", {})
    socmint_data = social.get("results") if isinstance(social, dict) else None

    if isinstance(socmint_data, dict) and socmint_data:
        st.markdown("### 🌐 SOCMINT")
        render_socmint_block(socmint_data)
    else:
        st.info("No se detectaron perfiles sociales.")

    # ========== PERSONAS ==========
    people = results.get("people", {})
    people_list = people.get("results", [])

    if people_list:
        st.markdown("### 👥 Personas")
        for i, person in enumerate(people_list):
            render_person_card(person, i)

    # ========== EMAIL ==========
    if "email" in results:
        render_email_block(results["email"])

    # ========== WEB ==========
    if "web" in results:
        render_web_block(results["web"])

    # ========== DARKWEB ==========
    if "darkweb" in results and results["darkweb"].get("results"):
        render_darkweb_block(results["darkweb"])

    # ========== DORKS ==========
    if "dorks" in results:
        render_dorks_block(results["dorks"])

    # ------------------ METADATA ------------------
    meta = results.get("_metadata", {})
    st.markdown("---")
    st.caption(
        f"⏱ Tiempo: {meta.get('search_time','N/A')}s | "
        f"Fuentes: {', '.join(meta.get('sources_searched', []))}"
    )


__all__ = ["show_person_search_ui"]
