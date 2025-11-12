import streamlit as st
import requests


def search_telegram_user(username):
    """Telegram API o scraping"""
    # Implement


def check_whatsapp_number(phone, api_key):
    """WhatsApp API Business"""
    # Implement


def render_ui(user_id, api_keys, config, db):
    st.header("💬 Digital Communications Intel")

    tab1, tab2 = st.tabs(["Telegram", "WhatsApp"])

    with tab1:
        username = st.text_input("Username Telegram", placeholder="@usuario")
        if st.button("Buscar"):
            # Implement
            st.info("Función en desarrollo")

    with tab2:
        phone = st.text_input("Número WhatsApp", placeholder="+34123456789")
        if st.button("Verificar"):
            st.info("Requiere API WhatsApp Business")