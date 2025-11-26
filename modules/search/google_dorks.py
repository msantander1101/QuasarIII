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
import re
from functools import lru_cache


def _search_serpapi(dork_q: str, limit: int, serpapi_key: str) -> List[Dict[str, any]]:
    """Búsqueda usando SerpAPI."""
    if not serpapi_key:
        return []

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
            return [
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": "SerpAPI",
                    "confidence": 0.90,
                    "timestamp": time.time(),
                }
                for item in data.get("organic_results", [])[:limit]
            ]
    except Exception:
        pass
    return []


def _search_google_cse(dork_q: str, limit: int, google_api_key: str, google_cx: str) -> List[Dict[str, any]]:
    """Búsqueda usando Google Custom Search."""
    if not (google_api_key and google_cx):
        return []

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
            return [
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": "Google CSE",
                    "confidence": 0.85,
                    "timestamp": time.time(),
                }
                for item in data.get("items", [])[:limit]
            ]
    except Exception:
        pass
    return []


def _search_duckduckgo(dork_q: str, limit: int) -> List[Dict[str, any]]:
    """Búsqueda usando DuckDuckGo."""
    try:
        api_url = (
            f"https://api.duckduckgo.com/?q={quote_plus(dork_q)}"
            "&format=json&no_redirect=1&skip_disambig=1"
        )
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()

            def extract_topics(topics):
                subresults = []
                for item in topics:
                    if isinstance(item, dict) and 'Topics' in item:
                        subresults.extend(extract_topics(item['Topics']))
                    elif isinstance(item, dict) and 'FirstURL' in item and 'Text' in item:
                        subresults.append({
                            'title': item.get('Text', 'Sin título'),
                            'url': item.get('FirstURL', '#'),
                            'snippet': item.get('Text', ''),
                            'source': 'DuckDuckGo',
                            'confidence': 0.75,
                            'timestamp': time.time(),
                        })
                return subresults

            if 'RelatedTopics' in data:
                extracted = extract_topics(data['RelatedTopics'])
                return extracted[:limit]
    except Exception:
        pass
    return []


# -------------------------------------------------------------------------
# 🔥 DORKS PROFESIONALES POR DEFECTO (OSINT + HUELLA DIGITAL)
# -------------------------------------------------------------------------
DEFAULT_DORKS = [
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


def search_google_dorks(query: str,
                        patterns: Optional[List[str]] = None,
                        max_results: int = 10,
                        serpapi_key: Optional[str] = None,
                        google_api_key: Optional[str] = None,
                        google_cx: Optional[str] = None) -> List[Dict[str, any]]:
    """
    Busca utilizando dorks en buscadores.

    Args:
        query (str): Consulta principal
        patterns (List[str], optional): Patrones a usar (por defecto DEFAULT_DORKS)
        max_results (int): Máximo número de resultados
        serpapi_key (str, optional): Clave SerpAPI
        google_api_key (str, optional): Clave Google Custom Search
        google_cx (str, optional): CX Google Custom Search

    Returns:
        List[Dict]: Resultados de búsqueda
    """
    if not query:
        return []

    # Recuperación de claves vía entorno
    serpapi_key = serpapi_key or os.getenv('SERPAPI_API_KEY')
    google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
    google_cx = google_cx or os.getenv('GOOGLE_CUSTOM_SEARCH_CX')

    patterns = patterns or DEFAULT_DORKS

    # Determinar qué motor de búsqueda usar
    search_method = None
    if serpapi_key:
        search_method = lambda q, lim: _search_serpapi(q, lim, serpapi_key)
    elif google_api_key and google_cx:
        search_method = lambda q, lim: _search_google_cse(q, lim, google_api_key, google_cx)
    else:
        search_method = _search_duckduckgo

    results: List[Dict[str, any]] = []
    for pattern in patterns:
        dork_query = f"{pattern} {query}".strip()
        google_url = f"https://www.google.com/search?q={quote_plus(dork_query)}"
        subresults = search_method(dork_query, min(3, max_results))

        # Asegurar que subresults es una lista
        if not isinstance(subresults, list):
            subresults = []

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


# ==========================================================================
# PERFILADOR AUTOMÁTICO DE DORKS PARA QUASARIII
# ==========================================================================

@lru_cache(maxsize=1024)
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


# ========================================================================
# DORKS PROFESIONALES SEGÚN TIPO DE OBJETIVO
# ========================================================================
_DORKS_BY_TYPE = {
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


def get_dorks_for_type(query_type: str) -> List[str]:
    """Obtiene dorks basados en el tipo de consulta."""
    return _DORKS_BY_TYPE.get(query_type, [])


# ============================================================================
# FUSIÓN AUTOMÁTICA CON EL MÓDULO EXISTENTE
# ============================================================================
def generate_profiled_dorks(query: str, user_patterns: Optional[List[str]] = None) -> List[str]:
    """
    Genera dorks automáticamente basados en el tipo de consulta.

    Si el usuario pasa patrones: se usan directamente.
    Si NO pasa patrones: se generan automáticamente en base al tipo de dato.
    """
    if user_patterns:
        return [pattern.format(query) if "{}" in pattern else pattern for pattern in user_patterns]

    qtype = classify_query_type(query)
    base_dorks = get_dorks_for_type(qtype)

    # Expande {}
    expanded = [d.format(query) for d in base_dorks]

    return expanded


# Alias de funciones para mantener compatibilidad
search_dorks = search_google_dorks
search = search_google_dorks