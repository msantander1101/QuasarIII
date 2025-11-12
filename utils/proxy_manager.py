import streamlit as st
import requests
import socket
import socks
import json
from typing import Dict, List, Optional


class ProxyManager:
    def __init__(self, user_id: int, db_manager):
        self.user_id = user_id
        self.db = db_manager
        self.proxies = self._load_proxies()
        self.tor_enabled = self._check_tor()

    def _load_proxies(self) -> List[Dict]:
        try:
            encrypted = self.db.get_api_key(self.user_id, "Proxies_List")
            if encrypted:
                from config_manager import ConfigManager
                return json.loads(ConfigManager().decrypt_api_key(encrypted))
        except:
            pass
        return []

    def _check_tor(self) -> bool:
        try:
            session = self._get_tor_session()
            response = session.get("https://check.torproject.org/", timeout=10, verify=False)
            return "Congratulations" in response.text
        except:
            return False

    def _get_tor_session(self):
        session = requests.Session()
        session.proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
        return session

    def get_current_ip(self, use_tor: bool = False):
        session = self._get_tor_session() if use_tor else requests.Session()
        return session.get("https://api.ipify.org").text

    def render_ui(self):
        st.subheader("🛡️ Proxy Manager")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("IP Actual", requests.get("https://api.ipify.org").text)
        with col2:
            if self.tor_enabled:
                st.metric("IP Tor", self.get_current_ip(use_tor=True))

        # Gestor de proxies
        if st.file_uploader("Subir proxies.json"):
            st.info("Formato: [{\"type\": \"http\", \"host\": \"1.2.3.4\", \"port\": 8080}]")