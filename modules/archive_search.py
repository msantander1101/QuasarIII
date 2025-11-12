import streamlit as st


class DarkWebOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    def render_ui(self):
        st.header("🧅 Dark Web Search")
        st.warning("⚠️ Requiere conexión Tor activa")

        query = st.text_input("Query Onion", placeholder="email@example.com")

        if st.button("Buscar en Ahmia"):
            st.info("Función requiere proxy Tor configurado")