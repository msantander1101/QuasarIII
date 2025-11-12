import requests
import streamlit as st
from bs4 import BeautifulSoup

from utils.rate_limiter import RateLimiter


class GeneralSearchOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager
        self.limiter = RateLimiter(delay=2)

    def search_google(self, query, api_key=None):
        """Google Custom Search"""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": api_key, "cx": "your_cx", "q": query}
        return requests.get(url, params=params).json()

    def search_duckduckgo(self, query):
        """DuckDuckGo HTML"""
        url = "https://duckduckgo.com/html/"
        params = {"q": query}
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers)
        return BeautifulSoup(response.text, 'html.parser').find_all('a')

    def render_ui(self):
        st.header("🔍 Búsqueda General")

        query = st.text_input("Query", placeholder="site:linkedin.com \"CEO\"")

        col1, col2 = st.columns(2)
        with col1:
            engine = st.selectbox("Motor", ["Google", "DuckDuckGo"])

        if st.button("Buscar"):
            with st.spinner("Buscando..."):
                if engine == "Google":
                    key = self.config.get_decrypted_key(self.db, self.user_id, "GoogleCustomSearch")
                    if key:
                        results = self.search_google(query, key)
                        st.json(results)
                    else:
                        st.error("Configura API key")
                else:
                    links = self.search_duckduckgo(query)
                    st.write(f"Encontrados {len(links)} resultados")