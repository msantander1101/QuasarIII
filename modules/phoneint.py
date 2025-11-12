from typing import Dict

import streamlit as st


class PhoneIntOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    def validate_phone(self, phone: str) -> Dict:
        """Valida formato de teléfono"""
        import re
        pattern = r'^\+\d{10,15}$'
        return {"valid": bool(re.match(pattern, phone)), "format": "E.164"}

    def render_ui(self):
        st.header("📞 Phone Intelligence")

        phone = st.text_input("Teléfono", placeholder="+34123456789")

        if st.button("Validar", type="primary"):
            result = self.validate_phone(phone)
            st.json(result)