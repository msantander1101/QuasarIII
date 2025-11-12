from typing import Dict
import streamlit as st
import asyncio
import whois
import dns.resolver


class DomainIntOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    async def get_whois(self, domain: str) -> Dict:
        """WHOIS lookup"""
        try:
            w = whois.whois(domain)
            return {
                "registrar": w.get("registrar"),
                "creation_date": str(w.get("creation_date")),
                "expiration_date": str(w.get("expiration_date")),
                "name_servers": w.get("name_servers")
            }
        except:
            return {"error": "No se pudo obtener WHOIS"}

    def render_ui(self):
        st.header("🌐 Domain Intelligence")

        domain = st.text_input("Dominio", placeholder="example.com")

        if st.button("Analizar", type="primary"):
            if not domain:
                st.error("❌ Ingresa dominio")
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            whois_data = loop.run_until_complete(self.get_whois(domain))

            # DNS Records
            records = {}
            try:
                records['A'] = [str(r) for r in dns.resolver.resolve(domain, 'A')]
                records['MX'] = [str(r) for r in dns.resolver.resolve(domain, 'MX')]
            except:
                pass

            col1, col2 = st.columns(2)
            with col1:
                st.json(whois_data)
            with col2:
                st.json(records)

            st.session_state.results_domainint = {"whois": whois_data, "dns": records}