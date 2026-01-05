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
from core.auth_manager import auth_manager  # ⬅️ AÑADIDO
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
from ui.pages.admin_users import show_admin_users_page
from ui.pages.investigations import show_investigations_page

# -------------------------------------------------
# Utils
# -------------------------------------------------
from ui.utils.helpers import clear_session
from utils.logger import setup_logger

logger = setup_logger()


# =================================================
# Bootstrap superusuario (Streamlit Secrets)
# =================================================
def bootstrap_superuser():
    """
    Crea un superusuario admin si no existe.
    Idempotente y seguro para Streamlit Cloud.
    """
    admin_user = st.secrets.get("BOOTSTRAP_ADMIN_USER", "")
    admin_pass = st.secrets.get("BOOTSTRAP_ADMIN_PASS", "")
    admin_email = st.secrets.get("BOOTSTRAP_ADMIN_EMAIL", "")

    if not (admin_user and admin_pass and admin_email):
        logger.info("Bootstrap admin no configurado (secrets vacíos)")
        return

    try:
        auth_manager.bootstrap_admin(
            username=admin_user,
            password=admin_pass,
            email=admin_email,
        )
        logger.info("Bootstrap admin ejecutado correctamente")
    except Exception:
        logger.exception("Error durante bootstrap admin")


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
        initial_sidebar_state="collapsed",
    )

    # -------------------------------------------------
    # DB init
    # -------------------------------------------------
    create_db()

    # ✅ Fuerza migración del esquema users (role/is_active) después de create_db()
    # Esto evita que create_db cree una tabla antigua sin columnas y rompa el bootstrap.
    auth_manager._ensure_schema()

    # -------------------------------------------------
    # Bootstrap admin (clave en Cloud)
    # -------------------------------------------------
    bootstrap_superuser()

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
        "force_reload": False,
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
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #0a192f 0%, #274472 100%);
        }
        MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )

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
            show_admin_users_page()

        elif page == "investigations":
            show_investigations_page()

        else:
            show_dashboard()

    else:
        show_login_with_tabs()


# -------------------------------------------------
# Entry point
# -------------------------------------------------
if __name__ == "__main__":
    main()
