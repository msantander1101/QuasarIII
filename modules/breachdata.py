import aiohttp
import streamlit as st
import asyncio
import requests
from typing import List, Dict
import pandas as pd

class BreachDataOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

        self.sources = {
            "haveibeenpwned": {"enabled": True, "api_key_required": True},
            "dehashed": {"enabled": True, "api_key_required": True},
            "leakcheck": {"enabled": True, "api_key_required": True},
        }

    async def check_hibp(self, email: str) -> List[Dict]:
        """Check HaveIBeenPwned"""
        try:
            api_key = self.config.get_decrypted_key(self.db, self.user_id, "HaveIBeenPwned")
            if not api_key:
                return []

            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
            headers = {"hibp-api-key": api_key, "User-Agent": "OSINT-Pro"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{"name": b["Name"], "date": b["BreachDate"], "source": "HIBP"} for b in data]
                    return []
        except:
            return []

    def render_ui(self):
        st.header("🔓 Breach Data")

        email = st.text_input("Email", placeholder="user@example.com")

        if st.button("Verificar Breaches", type="primary"):
            if not email:
                st.error("❌ Ingresa email")
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            breaches = loop.run_until_complete(self.check_hibp(email))

            if breaches:
                st.error(f"🚨 {len(breaches)} breaches encontrados!")
                df = pd.DataFrame(breaches)
                st.dataframe(df)
                st.session_state.results_breachdata = {"breaches": breaches}
            else:
                st.success("✅ Email no comprometido")