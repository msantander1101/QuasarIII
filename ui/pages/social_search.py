# ui/pages/social_search.py

import streamlit as st
import logging
import time

from modules.search.socmint.socmint import search_social_profiles
from ui.pages.person_search.components.socmint_block import render_socmint_block

logger = logging.getLogger(__name__)


def show_social_search_ui():
    st.markdown("""
    <div style="background: linear-gradient(135deg,#3a7bd5,#004e92);
                padding:20px;border-radius:12px;margin-bottom:20px;">
      <h1 style="color:white;margin:0;">🌐 SOCMINT — Perfiles Sociales</h1>
      <p style="color:rgba(255,255,255,0.9);margin-top:8px;">
        Búsqueda OSINT real usando Maigret y Sherlock (local)
      </p>
    </div>
    """, unsafe_allow_html=True)

    username = st.text_input(
        "👤 Username",
        placeholder="ej: johndoe, maria_garcia",
        key="socmint_username"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Buscar perfiles", use_container_width=True):
            if not username or len(username.strip()) < 2:
                st.warning("Introduce un username válido")
                return

            with st.spinner("Ejecutando SOCMINT (Maigret / Sherlock)..."):
                try:
                    results = search_social_profiles(username.strip())
                    st.session_state["socmint_results"] = results
                    st.session_state["socmint_time"] = time.time()
                    st.success("Búsqueda SOCMINT completada")
                except Exception as e:
                    logger.exception("SOCMINT error")
                    st.error(f"Error SOCMINT: {e}")

    with col2:
        if st.button("🧹 Limpiar", use_container_width=True):
            st.session_state.pop("socmint_results", None)
            st.rerun()

    # =========================
    # RESULTADOS
    # =========================
    results = st.session_state.get("socmint_results")

    if not results:
        st.info("Introduce un username y ejecuta la búsqueda.")
        return

    st.markdown("---")
    st.subheader("📊 Resultados SOCMINT")

    social_profiles = results.get("social_profiles")

    if isinstance(social_profiles, dict) and social_profiles:
        render_socmint_block(social_profiles)
    else:
        st.info("No se encontraron perfiles sociales.")

    # Metadata
    errors = results.get("errors", [])
    if errors:
        st.warning("Errores detectados:")
        for e in errors:
            st.write(f"- {e}")

    st.markdown("---")
    st.info("SOCMINT ejecutado localmente. No se usan APIs externas.")
