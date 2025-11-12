import streamlit as st
import requests
from utils.rate_limiter import RateLimiter

limiter = RateLimiter(delay=2)


def search_pipl(email, api_key):
    """Pipl API"""
    url = "https://api.pipl.com/search/"
    params = {"email": email, "key": api_key}
    return requests.get(url, params=params).json()


def search_spokeo(name, location):
    """Spokeo scraper"""
    # Implementa scraper


def render_ui(user_id, api_keys, config, db):
    st.header("👥 Person Search Aggregators")

    col1, col2 = st.columns(2)

    with col1:
        email = st.text_input("Email", placeholder="user@example.com")
        if st.button("Buscar en Pipl"):
            if "Pipl" in api_keys:
                key = config.get_decrypted_key(db, user_id, "Pipl")
                results = search_pipl(email, key)
                st.json(results)

    with col2:
        st.subheader("Buscar por Nombre")
        name = st.text_input("Nombre completo")
        location = st.text_input("Ciudad/Estado")
        if st.button("Buscar en Spokeo"):
            st.info("Función en desarrollo")