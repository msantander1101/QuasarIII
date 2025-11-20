# ui/templates/sidebar.py

import streamlit as st
from core.config_manager import config_manager


def render_sidebar():
    """
    Sidebar moderno con navegación intuitiva
    """

    # Logo y título
    st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h2 style="color: #495057; margin-bottom: 5px;">Quasar III</h2>
            <p style="color: #6c757d; font-size: 14px; margin: 0;">OSINT Suite Professional</p>
        </div>
    """, unsafe_allow_html=True)

    # Estado de las claves de API
    st.markdown("### 🔑 Configuración API")
    user_id = st.session_state.get('current_user_id')

    if user_id:
        required_keys = config_manager.get_required_keys_list()
        required_status = config_manager.are_keys_provided(user_id)

        for key, provided in required_status.items():
            status_icon = "✅" if provided else "❌"
            status_color = "green" if provided else "red"
            st.markdown(
                f"<p style='margin: 5px 0;'>{status_icon} <span style='color: {status_color};'>{key}</span></p>",
                unsafe_allow_html=True)

    # Menú de navegación
    st.markdown("### 📋 Navegación Principal")

    menu_items = {
        "📊 Dashboard": "dashboard",
        "🔍 Búsqueda Avanzada": "person_search",
        "🧠 Visualizar Grafo": "graph_visualization",
        "👥 SOCMINT": "social_search",
        "📄 Reportes": "report_generation",
        "⚙️ Configuración": "settings"
    }

    for item, page in menu_items.items():
        if st.button(item, use_container_width=True):
            st.session_state['page'] = page
            st.session_state['force_reload'] = True
            st.rerun()

    # Barra lateral informativa
    st.markdown("---")

    st.markdown("### 💡 Consejos")
    st.info("""
    • Usa la barra de búsqueda para hallar información
    • Guarda personas importantes para análisis posteriores
    • Explora el grafo de relaciones para conectar información
    • Configura tus claves API para búsquedas avanzadas
    """)

    st.markdown("---")

    # Información de versión
    st.markdown("### 📦 Versión 1.0.0")
    st.caption("OSINT Suite Profesional")