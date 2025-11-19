# ui/main.py

import streamlit as st
import os, sys

# Agregar el directorio raiz a path para poder importar core, modules, y utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar desde core
from core.auth_manager import register_user, authenticate_user
from core.db_manager import create_db
from core.config_manager import config_manager
from modules.ai.intelligence_core import ai_analyzer, initialize_ai_analyzer

# Importar páginas de UI
from ui.pages.login import show_login_with_tabs
from ui.pages.register import show_register_page
from ui.pages.dashboard import show_dashboard
from ui.pages.person_search import show_person_search_ui
from ui.pages.graph_visualization import show_graph_visualization
from ui.pages.settings import show_settings_page
from ui.pages.report_generation import show_report_generation_page

# Importa helpers y utilidades
from ui.utils.helpers import get_current_user_id, set_current_user_id, clear_session

# Importa el logger
from utils.logger import setup_logger

logger = setup_logger()

def main():
    logger.info("Iniciando aplicación Streamlit - Quasar III OSINT Suite")

    # Asegura que la BD está creada
    create_db()

    # --- Estado de sesión ---
    # Usamos valores por defecto si no existen
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
        st.session_state['current_user'] = {}
        st.session_state['current_user_id'] = None
        st.session_state['page'] = 'dashboard' # Pagina inicial
        st.session_state['force_reload'] = False # Flag para forzar recarga
        st.session_state['search_results'] = None # Resultados temporales de búsqueda
        st.session_state['search_count'] = 0 # Contador de búsquedas
        st.session_state['current_timestamp'] = None # Timestamp para reportes
        st.session_state['active_tab'] = 'login' # Para manejar pestañas

    # Inicializa contadores
    if 'current_timestamp' not in st.session_state:
        st.session_state['current_timestamp'] = st.session_state.get('current_timestamp', '')

    # --- Inicializar IA si el usuario ha iniciado sesión ---
    if st.session_state.get('authenticated', False):
        user_id = st.session_state.get('current_user_id')
        if user_id:
            # Verificar si se tiene la clave API para cargar IA
            api_key = config_manager.get_config(user_id, "openai_api_key")
            if api_key:
                initialize_ai_analyzer(api_key)
                logger.info("IA iniciada con clave proporcionada para usuario")
            else:
                initialize_ai_analyzer(None)

    # Mostrar contenido principal (sin sidebar)
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4edf5 100%) !important;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    # Logueo condicional: Decide qué mostrar
    if st.session_state.get('authenticated', False):
        logger.info(f"Sesión activa. Usuario identificado: { st.session_state.get('current_user', {}).get('username', 'Desconocido') }")
        page = st.session_state.get('page', 'dashboard')

        # Navegación basada en estado (ahora todo está en la página)
        if page == 'person_search':
            show_person_search_ui() # Mostrar el panel de búsqueda avanzada
        elif page == 'graph_visualization':
            show_graph_visualization() # Mostrar el panel de visualización del grafo
        elif page == 'settings': # Nueva página de config
            show_settings_page()
        elif page == 'report_generation': # Nueva página de reportes
            show_report_generation_page()
        else:
            # Por defecto, muestra el dashboard
            show_dashboard()
    else:
        # Mostrar el login con pestañas directamente
        show_login_with_tabs()

# Código de ejecución principal de Streamlit
if __name__ == "__main__":
    main()