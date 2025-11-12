import streamlit as st
import requests
from datetime import datetime

def search_pastebin(query, api_key=None):
    """Pastebin scraping"""
    # Implementa scraping de pastebin.com


def search_psbdmp(query):
    """PSBDMP API"""
    url = f"https://psbdmp.ws/api/v2/search/{query}"
    return requests.get(url).json()


def render_ui(user_id, api_keys, config, db):
    st.header("📝 Paste Search / Leaks")

    query = st.text_input("Buscar en paste sites", placeholder="email@example.com")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Buscar en PSBDMP"):
            results = search_psbdmp(query)
            st.json(results)

    with col2:
        if st.button("Scrape Pastebin"):
            st.warning("Usa proxies para evitar bloqueo")
