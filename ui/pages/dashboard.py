# ui/pages/dashboard.py

import streamlit as st
from core.db_manager import (
    get_persons_by_user,
    get_graph_for_user,
    # 🔹 NUEVO: helpers para investigaciones
    list_investigations_for_user,
    update_investigation_notes,
    delete_investigation,
)
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def show_dashboard():
    """
    Dashboard completamente sin barra lateral
    """
    # Header moderno con logo y título
    st.markdown("""
        <div style="background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%); 
                    padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color: #ffffff; text-align: center; margin: 0;">
                🚀 Quasar III OSINT Suite
            </h1>
            <p style="color: rgba(255,255,255,0.95); text-align: center; margin: 10px 0;">
                Panel de Control Profesional de Análisis OSINT
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Mostrar información del usuario
    current_user = st.session_state.get('current_user', {}) or {}
    username = current_user.get('username', 'Usuario Desconocido')
    is_admin = current_user.get('is_admin', False)

    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; 
                   background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <div>
                <h3>👋 Bienvenido, {username}</h3>
                <p style="color: #6c757d; margin: 0;">Panel de Control Principal</p>
            </div>
            <div style="text-align: right;">
                <small style="color: #6c757d;">{datetime.now().strftime('%d/%m/%Y %H:%M')}</small>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Navegación interna con botones
    st.markdown("### ⚡ Acciones Rápidas")

    # 🔹 Pasamos de 4 a 5 columnas para añadir Investigaciones
    cols = st.columns(5)

    with cols[0]:
        if st.button("🔍 Búsqueda Avanzada", use_container_width=True,
                     key="btn_search", help="Buscar personas, emails, información"):
            st.session_state['page'] = 'person_search'
            st.session_state['force_reload'] = True
            st.rerun()

    with cols[1]:
        if st.button("🧠 Visualizar Grafo", use_container_width=True,
                     key="btn_graph", help="Ver relaciones y conexiones"):
            st.session_state['page'] = 'graph_visualization'
            st.session_state['force_reload'] = True
            st.rerun()

    with cols[2]:
        if st.button("⚙️ Configuración", use_container_width=True,
                     key="btn_config", help="Administrar claves API y configuración"):
            st.session_state['page'] = 'settings'
            st.session_state['force_reload'] = True
            st.rerun()

    with cols[3]:
        if st.button("📄 Reportes", use_container_width=True,
                     key="btn_reports", help="Generar informes profesionales"):
            st.session_state['page'] = 'report_generation'
            st.session_state['force_reload'] = True
            st.rerun()

    # 🔹 Nueva acción rápida: ir a la página de Investigaciones
    with cols[4]:
        if st.button("📂 Investigaciones", use_container_width=True,
                     key="btn_investigations", help="Gestionar investigaciones guardadas"):
            st.session_state['page'] = 'investigations'
            st.session_state['force_reload'] = True
            st.rerun()

    # Botón extra solo para administradores
    if is_admin:
        st.markdown("")
        if st.button("👑 Administración de Usuarios", use_container_width=True,
                     key="btn_admin_users", help="Gestionar cuentas y roles de usuario"):
            st.session_state['page'] = 'admin_users'
            st.session_state['force_reload'] = True
            st.rerun()

    # Tarjetas de información crítica
    st.markdown("### 📊 Estadísticas del Sistema")

    cols_stats = st.columns(3)

    user_id = st.session_state.get('current_user_id', None)

    with cols_stats[0]:
        # Estadísticas de personas
        if user_id:
            persons = get_persons_by_user(user_id)
            persons_count = len(persons)
        else:
            persons_count = 0

        st.metric("Personas Investigadas", persons_count, delta="+0", delta_color="normal")
        st.progress(persons_count / 100 if persons_count < 100 else 1.0)

    with cols_stats[1]:
        # Estadísticas de relaciones
        if user_id:
            graph_data = get_graph_for_user(user_id)
            relationships_count = len(graph_data.get("relationships", []))
        else:
            relationships_count = 0

        st.metric("Relaciones Establecidas", relationships_count, delta="+0", delta_color="normal")
        st.progress(relationships_count / 50 if relationships_count < 50 else 1.0)

    with cols_stats[2]:
        # Estadísticas de búsquedas
        searches_count = st.session_state.get('search_count', 0)
        st.metric("Búsquedas Realizadas", searches_count, delta="+0", delta_color="normal")
        st.progress(min(searches_count / 20, 1.0))

    # Panel de búsqueda reciente
    st.markdown("### 🕵️ Búsquedas Recientes")

    if user_id:
        recent_persons = get_persons_by_user(user_id)
        if recent_persons:
            # Mostrar los últimos 5 registros de forma más visual
            for i, person in enumerate(recent_persons[:5]):
                person_card = f"""
                <div style="border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; margin-bottom: 10px; 
                           background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #495057;">{person['name']}</h4>
                            <small style="color: #6c757d;">{person.get('email', 'Sin email')}</small>
                            <br/>
                            <span style="font-size: 12px; color: #adb5bd;">{person.get('location', 'Ubicación desconocida')}</span>
                        </div>
                        <div style="text-align: right;">
                            <small style="color: #6c757d;">{person['created_at'][:10]}</small>
                        </div>
                    </div>
                </div>
                """
                st.markdown(person_card, unsafe_allow_html=True)
        else:
            st.info("Aún no has realizado búsquedas. Comienza con una búsqueda avanzada.")
    else:
        st.warning("Accede al sistema para ver tus búsquedas.")

    # 🔹 NUEVO: Panel de Investigaciones (ver / editar notas / borrar)
    st.markdown("### 📂 Investigaciones")

    if user_id:
        try:
            investigations = list_investigations_for_user(user_id)
        except Exception as e:
            logger.error("Error listando investigaciones para usuario %s: %s", user_id, e)
            investigations = []

        if not investigations:
            st.info("Todavía no tienes investigaciones guardadas.")
        else:
            # Mostramos solo las últimas 5 para no saturar el dashboard
            for inv in investigations[:5]:
                inv_id = inv.get("id")
                label = inv.get("label") or inv.get("root_query") or f"Investigación {inv_id}"
                entity_type = inv.get("entity_type") or "desconocido"
                created_at = inv.get("created_at") or ""
                notes = inv.get("notes") or ""

                with st.expander(f"#{inv_id} • {label} ({entity_type}) • {created_at}", expanded=False):
                    st.write(f"**Root query:** `{inv.get('root_query')}`")
                    st.write(f"**Tipo de entidad:** `{entity_type}`")

                    # ✅ Editar notas de la investigación
                    new_notes = st.text_area(
                        "Notas de la investigación",
                        value=notes,
                        key=f"inv_notes_{inv_id}",
                        height=80,
                    )

                    cols_inv = st.columns(3)

                    # Guardar cambios en notas
                    with cols_inv[0]:
                        if st.button("💾 Guardar notas", key=f"btn_save_inv_{inv_id}"):
                            ok = update_investigation_notes(inv_id, new_notes)
                            if ok:
                                st.success("Notas actualizadas.")
                            else:
                                st.error("No se pudieron actualizar las notas.")
                            st.rerun()

                    # Abrir detalle en la página de Investigaciones
                    with cols_inv[1]:
                        if st.button("📂 Abrir detalle", key=f"btn_open_inv_{inv_id}"):
                            # Guardamos el seleccionado en sesión para que la página de investigaciones lo use
                            st.session_state["inv_selected_id"] = inv_id
                            st.session_state["page"] = "investigations"
                            st.session_state["force_reload"] = True
                            st.rerun()

                    # Eliminar investigación
                    with cols_inv[2]:
                        if st.button("🗑️ Eliminar", key=f"btn_del_inv_{inv_id}"):
                            ok = delete_investigation(inv_id)
                            if ok:
                                st.success(f"Investigación #{inv_id} eliminada.")
                            else:
                                st.error("No se pudo eliminar la investigación.")
                            st.rerun()
    else:
        st.warning("Accede al sistema para gestionar tus investigaciones.")

    # Cierre de sesión
    st.markdown("<hr>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("")
    with col2:
        if st.button("🔒 Cerrar Sesión", use_container_width=True,
                     key="btn_logout", help="Salir del sistema de forma segura"):
            st.session_state.clear()
            st.rerun()
