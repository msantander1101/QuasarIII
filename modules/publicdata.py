import streamlit as st
import requests


def search_fastpeople(name, city, state):
    """FastPeopleSearch scraper"""
    url = f"https://www.fastpeoplesearch.com/name/{name}_{city}-{state}"
    # Implement scraper


def search_whitepages(name, location):
    """Whitepages API"""
    # Implement


def render_ui(user_id, api_keys, config, db):
    st.header("📚 Public Data Aggregators")

    name = st.text_input("Nombre", placeholder="Juan Perez")
    city = st.text_input("Ciudad", placeholder="Madrid")

    if st.button("Buscar en FastPeople"):
        results = search_fastpeople(name, city, "CA")
        st.json(results)