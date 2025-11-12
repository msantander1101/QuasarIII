import streamlit as st
import requests


def search_apkpure(app_name):
    """Buscar APK en APKPure"""
    url = f"https://apkpure.com/search?q={app_name}"
    # Implement scraper


def check_virustotal_apk(hash, api_key):
    """VirusTotal APK analysis"""
    url = f"https://www.virustotal.com/vtapi/v2/file/report"
    params = {"resource": hash, "apikey": api_key}
    return requests.get(url, params=params).json()


def render_ui(user_id, api_keys, config, db):
    st.header("📱 Mobile OSINT")

    tab1, tab2 = st.tabs(["Buscar APK", "Analizar APK"])

    with tab1:
        app = st.text_input("Nombre app", placeholder="WhatsApp")
        if st.button("Buscar en APKPure"):
            results = search_apkpure(app)
            st.json(results)

    with tab2:
        apk_hash = st.text_input("Hash SHA256", placeholder="a" * 64)
        if st.button("Analizar con VT"):
            if "VirusTotal" in api_keys:
                key = config.get_decrypted_key(db, user_id, "VirusTotal")
                data = check_virustotal_apk(apk_hash, key)
                st.json(data)