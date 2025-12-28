"""
Investigations UI — Gestión y consulta de investigaciones guardadas.

- Lista investigaciones previas del usuario
- Permite abrir una investigación y ver el snapshot de resultados OSINT
- Reutiliza los mismos bloques visuales de person_search
"""

import logging
from typing import Dict, Any, Optional, List

import streamlit as st

from core.db_manager import (
    list_investigations_for_user,
    get_investigation_with_results,
)

# Reutilizamos componentes de person_search
from ui.pages.person_search.components.person_card import render_person_card
from ui.pages.person_search.components.socmint_block import render_socmint_block
from ui.pages.person_search.components.web_email_blocks import (
    render_web_block,
    render_email_block,
)
from ui.pages.person_search.components.darkweb_block import render_darkweb_block
from ui.pages.person_search.components.dorks_block import render_dorks_block
from ui.pages.person_search.components.general_block import render_general_block
from ui.pages.person_search.components.breach_block import render_breach_block

logger = logging.getLogger(__name__)


# --------------- Helpers internos ---------------

def _get_effective_user_id() -> Optional[int]:
    """
    Determina el user_id efectivo desde la sesión.
    """
    user_id = st.session_state.get("current_user_id") or st.session_state.get("user_id")
    return user_id


def _pick_best_snapshot(results_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    De una lista de snapshots de investigación (investigation_results),
    elige el más adecuado.

    Estrategia actual:
      - Preferimos source == "combined"
      - Si no hay, devolvemos el primero.
    """
    if not results_list:
        return None

    # Buscar uno marcado como "combined"
    for r in results_list:
        if (r.get("source") or "").lower() == "combined":
            return r.get("data")

    # Fallback: usaremos el data del primero
    return results_list[0].get("data")


def _render_results_blocks(results: Dict[str, Any]):
    """
    Renderiza los bloques de resultados reutilizando exactamente
    la misma lógica visual que la búsqueda de personas.
    """
    if not isinstance(results, dict):
        st.warning("Snapshot de resultados no válido.")
        return

    st.markdown("---")
    st.subheader("📊 Resultados de la investigación")

    # ========== SOCMINT ==========
    social = results.get("social", {})
    socmint_data = social.get("results") if isinstance(social, dict) else None

    if isinstance(socmint_data, dict) and socmint_data:
        st.markdown("### 🌐 SOCMINT")
        render_socmint_block(socmint_data)
    else:
        st.info("No se detectaron perfiles sociales en este snapshot.")

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

    # ========== RADAR GENERAL WEB ==========
    if "general_web" in results:
        render_general_block(results["general_web"])

    # ========== DARKWEB ==========
    if "darkweb" in results and results["darkweb"].get("results"):
        render_darkweb_block(results["darkweb"])

    # ========== BRECHAS / LEAKS ==========
    if "breach" in results:
        render_breach_block(results["breach"])

    # ========== DORKS ==========
    if "dorks" in results:
        render_dorks_block(results["dorks"])

    # ------------------ METADATA ------------------
    meta = results.get("_metadata", {})
    st.markdown("---")
    st.caption(
        f"⏱ Tiempo original de búsqueda: {meta.get('search_time','N/A')}s | "
        f"Fuentes consultadas: {', '.join(meta.get('sources_searched', []))}"
    )


# --------------- MAIN UI ---------------

def show_investigations_page():
    user_id = _get_effective_user_id()
    if not user_id:
        st.error("No hay usuario autenticado. No se pueden mostrar investigaciones.")
        return

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1f2937,#111827);
                padding:18px;border-radius:12px;margin-bottom:20px">
        <h1 style="color:white;margin:0">📂 Investigaciones guardadas</h1>
        <p style="color:#d1d5db;margin-top:8px">
            Revisa búsquedas previas, casos y snapshots OSINT asociados a un objetivo.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ------------ Lista de investigaciones ------------

    investigations = list_investigations_for_user(user_id)
    if not investigations:
        st.info("Aún no tienes investigaciones guardadas. Ejecuta una búsqueda en 'Person Search' para generar la primera.")
        return

    # Preparar opciones de selección
    options_labels = []
    id_map = {}
    for inv in investigations:
        inv_id = inv["id"]
        label = inv.get("label") or inv.get("root_query") or f"Investigación {inv_id}"
        etype = inv.get("entity_type") or "unknown"
        created = inv.get("created_at") or ""
        opt_label = f"#{inv_id} • {label} • ({etype}) • {created}"
        options_labels.append(opt_label)
        id_map[opt_label] = inv_id

    st.markdown("### 📁 Selecciona una investigación")

    default_index = 0
    # Si venimos de una búsqueda reciente, intentamos preseleccionar
    last_inv_id = st.session_state.get("ps_last_investigation_id")
    if last_inv_id:
        for idx, inv in enumerate(investigations):
            if inv["id"] == last_inv_id:
                default_index = idx
                break

    selected_label = st.selectbox(
        "Investigaciones disponibles",
        options_labels,
        index=default_index,
        key="inv_selector",
    )

    selected_id = id_map.get(selected_label)
    if not selected_id:
        st.warning("No se pudo determinar la investigación seleccionada.")
        return

    st.markdown(f"#### 🧾 Detalle de la investigación #{selected_id}")

    inv_data = get_investigation_with_results(selected_id)
    if not inv_data:
        st.error("No se pudo cargar la investigación seleccionada.")
        return

    # Cabecera con metadatos
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Root query:** `{inv_data.get('root_query')}`")
        st.markdown(f"**Tipo de entidad:** `{inv_data.get('entity_type') or 'desconocido'}`")
    with col_b:
        st.markdown(f"**Creada:** `{inv_data.get('created_at')}`")
        notes = inv_data.get("notes") or "—"
        st.markdown(f"**Notas:** {notes}")

    snapshots = inv_data.get("results") or []
    if not snapshots:
        st.info("Esta investigación aún no tiene snapshots de resultados almacenados.")
        return

    # Información rápida sobre snapshots
    st.markdown("##### 🧬 Snapshots almacenados")
    for s in snapshots:
        st.markdown(
            f"- ID: `{s['id']}` • source=`{s['source']}` • fecha=`{s['created_at']}`"
        )

    # Elegir el mejor snapshot para mostrar
    best = _pick_best_snapshot(snapshots)
    if not best:
        st.warning("No se pudo interpretar el snapshot de resultados.")
        return

    _render_results_blocks(best)


__all__ = ["show_investigations_page"]
