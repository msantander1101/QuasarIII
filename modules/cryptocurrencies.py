import streamlit as st


class CryptoOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    def render_ui(self):
        st.header("₿ Cryptocurrency Intel")

        wallet = st.text_input("Wallet Address", placeholder="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")

        if st.button("Verificar", type="primary"):
            st.info("Integración con Blockchain.info requiere API key")