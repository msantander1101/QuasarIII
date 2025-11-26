"""
Módulo de Google Dorks para QuasarIII

Este módulo genera consultas de búsqueda avanzadas (google dorks) y,
dependiendo de las claves disponibles, consulta SerpAPI, Google Custom Search
o DuckDuckGo para obtener resultados reales.
"""

import time
import os
import requests
from typing import List, Dict, Optional
from urllib.parse import quote_plus

def search_google_dorks(query: str,
                        patterns: Optional[List[str]] = None,
                        max_results: int = 10,
                        serpapi_key: Optional[str] = None,
                        google_api_key: Optional[str] = None,
                        google_cx: Optional[str] = None) -> List[Dict[str, any]]:

    if not query:
        return []

    # -------------------------------------------------------------------------
    # 🔥 DORKS PROFESIONALES POR DEFECTO (OSINT + HUELLA DIGITAL)
    # -------------------------------------------------------------------------
    if patterns is None:
        patterns = [

            # ------------------------------
            # 🔎 Perfiles & Huella Digital
            # ------------------------------
            'site:linkedin.com/in',
            'site:instagram.com',
            'site:twitter.com',
            'site:t.me',
            'site:keybase.io',
            '"powered by discourse" "view user"',
            '"index of /users"',

            # ------------------------------
            # 🔐 Leaks y credenciales
            # ------------------------------
            'site:pastebin.com',
            'site:ghostbin.com',
            'site:dpaste.org',
            '"password" "lastpass" filetype:txt',
            '"password" "admin" filetype:xls',
            '"credentials exposed"',

            # -----------------------------------
            # 🧬 Repositorios (Github/GitLab leaks)
            # -----------------------------------
            'site:github.com "API_KEY"',
            'site:github.com "SECRET_KEY"',
            'site:gitlab.com "token"',
            '"filename:.env" "DB_PASSWORD"',

            # -----------------------------------
            # 📄 Documentos sensibles
            # -----------------------------------
            'filetype:pdf',
            'filetype:xls',
            'filetype:txt "confidential"',
            'intitle:"index of" "backup"',
            'intitle:"index of" "logs"',

            # -----------------------------------
            # 🔍 WordPress OSINT
            # -----------------------------------
            'inurl:wp-config.php',
            'inurl:wp-admin "index of"',
            'site:*/wp-content/uploads',
            'intitle:"WordPress Users"',

            # -----------------------------------
            # ☁️ Cloud Buckets Públicos
            # -----------------------------------
            'site:amazonaws.com "index of"',
            'site:storage.googleapis.com "index of"',
            '"index of" "azure"',

            # -----------------------------------
            # 🛰️ Infraestructura expuesta
            # -----------------------------------
            '"Server at" "port" "Apache"',
            '"Dashboard" "login" "admin"',
            '"camera" "inurl:view.shtml"',
            '"index of" "mysql dump"',
        ]

    # -------------------------------------------------------------------------
    # Recuperación de claves vía entorno
    # -------------------------------------------------------------------------
    serpapi_key = serpapi_key or os.getenv('SERPAPI_API_KEY')
    google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
    google_cx = google_cx or os.getenv('GOOGLE_CUSTOM_SEARCH_CX')

    results: List[Dict[str, any]] = []

    # -------------------------------------------------------------------------
    # Funciones auxiliares para las APIs
    # -------------------------------------------------------------------------
    def _search_serpapi(dork_q: str, limit: int) -> List[Dict[str, any]]:
        subresults = []
        if not serpapi_key:
            return subresults
        try:
            url = "https://serpapi.com/search"
            params = {
                "engine": "google",
                "q": dork_q,
                "api_key": serpapi_key,
                "num": limit,
            }
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("organic_results", [])[:limit]:
                    subresults.append({
                        "title": item.get("title"),
                        "url": item.get("link"),
                        "snippet": item.get("snippet"),
                        "source": "SerpAPI",
                        "confidence": 0.90,
                        "timestamp": time.time(),
                    })
        except Exception:
            pass
        return subresults

    def _search_google_cse(dork_q: str, limit: int) -> List[Dict[str, any]]:
        subresults = []
        if not (google_api_key and google_cx):
            return subresults
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": google_api_key,
                "cx": google_cx,
                "q": dork_q,
                "num": limit,
            }
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("items", [])[:limit]:
                    subresults.append({
                        "title": item.get("title"),
                        "url": item.get("link"),
                        "snippet": item.get("snippet"),
                        "source": "Google CSE",
                        "confidence": 0.85,
                        "timestamp": time.time(),
                    })
        except Exception:
            pass
        return subresults

    def _search_duckduckgo(dork_q: str, limit: int) -> List[Dict[str, any]]:
        subresults = []
        try:
            api_url = (
                f"https://api.duckduckgo.com/?q={quote_plus(dork_q)}"
                "&format=json&no_redirect=1&skip_disambig=1"
            )
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()

                def extract_topics(topics):
                    for item in topics:
                        if isinstance(item, dict) and 'Topics' in item:
                            extract_topics(item['Topics'])
                        else:
                            if isinstance(item, dict) and 'FirstURL' in item and 'Text' in item:
                                subresults.append({
                                    'title': item.get('Text', 'Sin título'),
                                    'url': item.get('FirstURL', '#'),
                                    'snippet': item.get('Text', ''),
                                    'source': 'DuckDuckGo',
                                    'confidence': 0.75,
                                    'timestamp': time.time(),
                                })

                if 'RelatedTopics' in data:
                    extract_topics(data['RelatedTopics'])
        except Exception:
            pass
        return subresults[:limit]

    # -------------------------------------------------------------------------
    # Ejecución de dorks
    # -------------------------------------------------------------------------
    for pattern in patterns:
        dork_query = f"{pattern} {query}".strip()
        google_url = f"https://www.google.com/search?q={quote_plus(dork_query)}"

        if serpapi_key:
            subresults = _search_serpapi(dork_query, 3)
        elif google_api_key and google_cx:
            subresults = _search_google_cse(dork_query, 3)
        else:
            subresults = _search_duckduckgo(dork_query, 3)

        results.append({
            "source": "google_dorks",
            "query": dork_query,
            "title": f"Google Dork: {pattern}",
            "url": google_url,
            "description": f"Resultados de dork '{pattern}' para '{query}'",
            "timestamp": time.time(),
            "confidence": 0.80,
            "results": subresults,
        })

    return results


def search_dorks(query: str, patterns: Optional[List[str]] = None) -> List[Dict[str, any]]:
    return search_google_dorks(query, patterns)

def search(query: str, **kwargs) -> List[Dict[str, any]]:
    patterns = kwargs.get('patterns')
    return search_google_dorks(query, patterns)
import re

# ================================================================
#  PERFILADOR AUTOMÁTICO DE DORKS PARA QUASARIII
# ================================================================
def classify_query_type(query: str) -> str:
    """Detecta automáticamente qué tipo de dato se está investigando."""

    query = query.strip()

    if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", query):
        return "email"

    if re.match(r"^\d{7,15}$", query.replace("+", "").replace(" ", "")):
        return "phone"

    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", query):
        return "ip"

    if re.match(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$", query):
        return "subnet"

    if re.match(r"^[a-zA-Z0-9\-_]{3,32}$", query):
        return "username"

    if "." in query and not query.startswith("http"):
        return "domain"

    if query.startswith("http://") or query.startswith("https://"):
        return "url"

    # Si no encaja en nada → persona genérica
    return "person"


# ================================================================
#  DORKS PROFESIONALES SEGÚN TIPO DE OBJETIVO
# ================================================================
def get_dorks_for_type(query_type: str) -> list:

    dorks = {

        # ---------------------------------------------------
        # PERSONA (nombre real)
        # ---------------------------------------------------
        "person": [
            '"{}" site:linkedin.com/in',
            '"{}" site:facebook.com',
            '"{}" site:instagram.com',
            '"{}" "curriculum vitae"',
            '"{}" "phone number"',
            '"{}" "email"'
        ],

        # ---------------------------------------------------
        # USERNAME (alias)
        # ---------------------------------------------------
        "username": [
            '"{}" site:github.com',
            '"{}" site:gitlab.com',
            '"{}" site:keybase.io',
            '"{}" site:twitter.com',
            '"{}" site:steamcommunity.com',
            '"{}" "username" "profile"'
        ],

        # ---------------------------------------------------
        # EMAIL
        # ---------------------------------------------------
        "email": [
            '"{}" site:pastebin.com',
            '"{}" site:ghostbin.com',
            '"{}" filetype:txt "password"',
            '"{}" "data breach"',
            '"{}" "leaked"',
            '"{}" "credential"'
        ],

        # ---------------------------------------------------
        # TELÉFONO
        # ---------------------------------------------------
        "phone": [
            '"{}" "WhatsApp"',
            '"{}" "Telegram"',
            '"{}" "contact"',
            '"{}" "lookup"',
            '"{}" "reverse phone"'
        ],

        # ---------------------------------------------------
        # DOMINIO / EMPRESA
        # ---------------------------------------------------
        "domain": [
            'site:{}/wp-admin',
            'site:{}/wp-content',
            'site:{}/.git',
            'site:{}/"index of"',
            'site:pastebin.com "{}"',
            'site:github.com "{}"',
        ],

        # ---------------------------------------------------
        # IP
        # ---------------------------------------------------
        "ip": [
            '"{}" "port"',
            '"{}" "open"',
            '"{}" "ssh"',
            '"{}" "vulnerable"',
            '"{}" "camera"',
        ],

        # ---------------------------------------------------
        # SUBRED
        # ---------------------------------------------------
        "subnet": [
            '"{}" "IP range"',
            '"{}" "open services"',
            '"{}" "network"'
        ],

        # ---------------------------------------------------
        # URL
        # ---------------------------------------------------
        "url": [
            '"{}" "index of"',
            '"{}" "backup"',
            '"{}" "config"',
            '"{}" "credentials"',
        ],
    }

    return dorks.get(query_type, [])



# ================================================================
#  FUSIÓN AUTOMÁTICA CON EL MÓDULO EXISTENTE
# ================================================================
def generate_profiled_dorks(query: str, user_patterns=None):
    """
    Si el usuario pasa patrones: se usan.
    Si NO pasa patrones: se generan automáticamente en base al tipo de dato.
    """

    if user_patterns:
        return [pattern.format(query) if "{}" in pattern else pattern for pattern in user_patterns]

    qtype = classify_query_type(query)
    base_dorks = get_dorks_for_type(qtype)

    # Expande {}
    expanded = [d.format(query) for d in base_dorks]

    return expanded
