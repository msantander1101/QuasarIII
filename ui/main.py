# ui/main.py

import streamlit as st
import os
import sys

# -------------------------------------------------
# Path raíz del proyecto
# -------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# -------------------------------------------------
# Core
# -------------------------------------------------
from core.db_manager import create_db
from core.config_manager import config_manager
from modules.ai.intelligence_core import initialize_ai_analyzer

# -------------------------------------------------
# UI Pages
# -------------------------------------------------
from ui.pages.login import show_login_with_tabs
from ui.pages.dashboard import show_dashboard
from ui.pages.person_search import show_person_search_ui
from ui.pages.graph_visualization import show_graph_visualization
from ui.pages.settings import show_settings_page
from ui.pages.report_generation import show_report_generation_page
from ui.pages.admin_users import show_admin_users_page  # ⬅️ añadido

# -------------------------------------------------
# Utils
# -------------------------------------------------
from ui.utils.helpers import clear_session  # si lo usas en otros sitios
from utils.logger import setup_logger

logger = setup_logger()


# =================================================
# MAIN
# =================================================
def main():
    logger.info("Arrancando Quasar III OSINT Suite")

    # -------------------------------------------------
    # Streamlit config
    # -------------------------------------------------
    st.set_page_config(
        page_title="Quasar III OSINT Suite",
        page_icon="🕵️‍♂️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # -------------------------------------------------
    # DB init
    # -------------------------------------------------
    create_db()

    # -------------------------------------------------
    # Session state defaults
    # -------------------------------------------------
    defaults = {
        "authenticated": False,
        "current_user": {},
        "current_user_id": None,
        "page": "dashboard",
        "search_results": None,
        "search_count": 0,
        "current_timestamp": None,
        "active_tab": "login",
        "force_reload": False,     # ⬅️ añadido para coherencia con dashboard
    }

    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # -------------------------------------------------
    # Initialize AI (if logged in)
    # -------------------------------------------------
    if st.session_state["authenticated"]:
        user_id = st.session_state.get("current_user_id")
        if user_id:
            api_key = config_manager.get_config(user_id, "openai_api_key")
            initialize_ai_analyzer(api_key)
            logger.info("IA inicializada")

    # -------------------------------------------------
    # Global styles
    # -------------------------------------------------
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #0a192f 0%, #274472 100%);
        }
        MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # Routing
    # -------------------------------------------------
    if st.session_state["authenticated"]:
        page = st.session_state.get("page", "dashboard")
        current_user = st.session_state.get("current_user", {})
        logger.info(
            "Sesión activa | Usuario=%s | Página=%s",
            current_user.get("username"),
            page,
        )

        if page == "person_search":
            show_person_search_ui()

        elif page == "graph_visualization":
            show_graph_visualization()

        elif page == "settings":
            show_settings_page()

        elif page == "report_generation":
            show_report_generation_page()

        elif page == "admin_users":
            # El propio módulo hace el check de is_admin
            show_admin_users_page()

        else:
            show_dashboard()

    else:
        show_login_with_tabs()


# -------------------------------------------------
# Entry point
# -------------------------------------------------
if __name__ == "__main__":
    main()
