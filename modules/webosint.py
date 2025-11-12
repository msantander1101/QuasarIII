import streamlit as st
import requests
from bs4 import BeautifulSoup
import whois
import dns.resolver


def get_whois(domain):
    """WHOIS lookup"""
    return whois.whois(domain)


def get_dns_records(domain):
    """DNS records"""
    records = {}
    try:
        records['A'] = [str(r) for r in dns.resolver.resolve(domain, 'A')]
        records['MX'] = [str(r) for r in dns.resolver.resolve(domain, 'MX')]
        records['TXT'] = [str(r) for r in dns.resolver.resolve(domain, 'TXT')]
    except:
        pass
    return records


def crawl_website(url, profundidad=1):
    """Web crawling básico"""
    # Implementa scrapy o requests recursivo


def render_ui(user_id, api_keys, config, db):
    st.header("🌐 Web OSINT")

    tab1, tab2, tab3 = st.tabs(["WHOIS/DNS", "Crawling", "Tecnologías"])

    with tab1:
        domain = st.text_input("Dominio", placeholder="example.com")
        if st.button("Analizar"):
            st.json(get_whois(domain))
            st.json(get_dns_records(domain))

    with tab2:
        url = st.text_input("URL a crawler", placeholder="https://ejemplo.com")
        profundidad = st.slider("Profundidad", 1, 3, 1)
        if st.button("Crawlear"):
            crawl_website(url, profundidad)

    with tab3:
        st.info("Usa Wappalyzer API o BuiltWith")