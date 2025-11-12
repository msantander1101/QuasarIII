from typing import Dict

import streamlit as st
import asyncio
from email_validator import validate_email


class EmailIntOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    async def validate_format(self, email: str) -> Dict:
        """Valida formato y DNS"""
        try:
            valid = validate_email(email)
            return {"valid": True, "normalized": valid.email}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def render_ui(self):
        st.header("📧 Email Intelligence")

        email = st.text_input("Email", placeholder="user@example.com")

        if st.button("Validar", type="primary"):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.validate_format(email))
            st.json(result)