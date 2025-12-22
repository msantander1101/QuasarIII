"""
Módulo de Google Dorks para QuasarIII

Este módulo genera consultas de búsqueda avanzadas (google dorks) y,
dependiendo de las claves disponibles, consulta SerpAPI, Google Custom Search
o DuckDuckGo para obtener resultados reales.
"""

import time
import os
import requests
from typing import List, Dict, Optional, Iterable
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
# USANDO intext: PARA BUSCAR TEXTOS EXACTOS
# -------------------------------------------------------------------------
DEFAULT_DORKS = [
    # ------------------------------
    # 🔎 Perfiles & Huella Digital
    # ------------------------------
    'intext:"{}" site:linkedin.com/in',
    'intext:"{}" site:instagram.com',
    'intext:"{}" site:twitter.com',
    'intext:"{}" site:t.me',
    'intext:"{}" site:keybase.io',
    'intext:"powered by discourse" intext:"view user"',
    'intext:"index of /users"',

    # ------------------------------
    # 🔐 Leaks y credenciales
    # ------------------------------
    'intext:"{}" site:pastebin.com',
    'intext:"{}" site:ghostbin.com',
    'intext:"{}" site:dpaste.org',
    'intext:"password" intext:"lastpass" filetype:txt',
    'intext:"password" intext:"admin" filetype:xls',
    'intext:"credentials exposed"',

    # -----------------------------------
    # 🧬 Repositorios (Github/GitLab leaks)
    # -----------------------------------
    'intext:"{}" site:github.com "API_KEY"',
    'intext:"{}" site:github.com "SECRET_KEY"',
    'intext:"{}" site:gitlab.com "token"',
    'intext:"filename:.env" intext:"DB_PASSWORD"',

    # -----------------------------------
    # 📄 Documentos sensibles
    # -----------------------------------
    'intext:"{}" filetype:pdf',
    'intext:"{}" filetype:xls',
    'intext:"{}" filetype:txt "confidential"',
    'intext:"index of" intext:"backup"',
    'intext:"index of" intext:"logs"',

    # -----------------------------------
    # 🔍 WordPress OSINT
    # -----------------------------------
    'intext:"{}" inurl:wp-config.php',
    'intext:"{}" inurl:wp-admin "index of"',
    'intext:"{}" site:*/wp-content/uploads',
    'intext:"{}" intitle:"WordPress Users"',

    # -----------------------------------
    # ☁️ Cloud Buckets Públicos
    # -----------------------------------
    'intext:"{}" site:amazonaws.com "index of"',
    'intext:"{}" site:storage.googleapis.com "index of"',
    'intext:"{}" "index of" "azure"',

    # -----------------------------------
    # 🛰️ Infraestructura expuesta
    # -----------------------------------
    'intext:"Server at" intext:"port" intext:"Apache"',
    'intext:"Dashboard" intext:"login" intext:"admin"',
    'intext:"camera" intext:"inurl:view.shtml"',
    'intext:"index of" intext:"mysql dump"',
]


def _deduplicate_preserve_order(items: Iterable[str]) -> List[str]:
    """Elimina duplicados preservando el orden de los elementos."""

    seen = set()
    unique_items = []

    for item in items:
        if item not in seen:
            unique_items.append(item)
            seen.add(item)

    return unique_items


def build_dork_queries(query: str,
                       patterns: Optional[List[str]] = None,
                       include_profiled: bool = True,
                       max_patterns: Optional[int] = None) -> List[Dict[str, str]]:
    """Normaliza y genera dorks listos para ejecutarse.

    Combina los patrones proporcionados con dorks sugeridos automáticamente
    según el tipo de consulta. Los dorks finales se devuelven ya formateados
    con la query original, listos para ser usados en buscadores.
    """

    seed_patterns: List[str] = []

    if patterns:
        seed_patterns.extend(patterns)

    if include_profiled and not patterns:
        # Solo añadimos los dorks perfilados cuando el usuario no ha
        # pasado patrones explícitos. Esto evita mezclar formatos
        # personalizados con los automáticos.
        seed_patterns.extend(generate_profiled_dorks(query))

    if not seed_patterns:
        seed_patterns.extend(DEFAULT_DORKS)

    normalized_patterns = _deduplicate_preserve_order(
        [p.strip() for p in seed_patterns if p]
    )

    output: List[Dict[str, str]] = []

    for pattern in normalized_patterns:
        formatted_query = pattern.format(query) if "{}" in pattern else pattern
        formatted_query = formatted_query.strip()

        if not formatted_query:
            continue

        output.append({
            "pattern": pattern,
            "query": formatted_query,
            "google_url": f"https://www.google.com/search?q={quote_plus(formatted_query)}",
        })

        if max_patterns and len(output) >= max_patterns:
            break

    return output


def search_google_dorks(query: str,
                        patterns: Optional[List[str]] = None,
                        max_results: int = 10,
                        serpapi_key: Optional[str] = None,
                        google_api_key: Optional[str] = None,
                        google_cx: Optional[str] = None,
                        max_patterns: Optional[int] = None,
                        include_profiled: bool = True) -> List[Dict[str, any]]:
    """
    Busca utilizando dorks en buscadores.

    Args:
        query (str): Consulta principal
        patterns (List[str], optional): Patrones a usar (por defecto DEFAULT_DORKS)
        max_results (int): Máximo número de resultados
        serpapi_key (str, optional): Clave SerpAPI
        google_api_key (str, optional): Clave Google Custom Search
        google_cx (str, optional): CX Google Custom Search
        max_patterns (int, optional): Número máximo de dorks a generar
        include_profiled (bool): Si True, añade dorks sugeridos según el tipo
            de dato (usuario, email, dominio, etc.)

    Returns:
        List[Dict]: Resultados de búsqueda
    """
    if not query:
        return []

    # Recuperación de claves vía entorno
    serpapi_key = serpapi_key or os.getenv('SERPAPI_API_KEY')
    google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
    google_cx = google_cx or os.getenv('GOOGLE_CUSTOM_SEARCH_CX')

    # Determinar qué motor de búsqueda usar
    if serpapi_key:
        search_method = lambda q, lim: _search_serpapi(q, lim, serpapi_key)
    elif google_api_key and google_cx:
        search_method = lambda q, lim: _search_google_cse(q, lim, google_api_key, google_cx)
    else:
        search_method = _search_duckduckgo

    dork_entries = build_dork_queries(
        query,
        patterns=patterns,
        include_profiled=include_profiled,
        max_patterns=max_patterns,
    )

    results: List[Dict[str, any]] = []
    for entry in dork_entries:
        dork_query = entry["query"]
        pattern = entry["pattern"]
        google_url = entry["google_url"]

        # Refuerzo de intext para patrones muy simples
        if "intext:" not in dork_query and query.strip():
            if not any(token in dork_query for token in ["site:", "filetype:", "inurl:"]):
                quoted = f'"{query}"' if " " in query else query
                dork_query = f"intext:{quoted} {dork_query}".strip()
                google_url = f"https://www.google.com/search?q={quote_plus(dork_query)}"

        subresults = search_method(dork_query, min(3, max_results))

        # Asegurar que subresults es una lista
        if not isinstance(subresults, list):
            subresults = []

        results.append({
            "source": "google_dorks",
            "query": dork_query,
            "pattern": pattern,
            "title": f"Google Dork: {pattern}",
            "url": google_url,
            "description": f"Resultados de dork '{pattern}' para '{query}'",
            "timestamp": time.time(),
            "confidence": 0.80 if subresults else 0.50,
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
        'intext:"{}" site:linkedin.com/in',
        'intext:"{}" site:facebook.com',
        'intext:"{}" site:instagram.com',
        'intext:"{}" "curriculum vitae"',
        'intext:"{}" "phone number"',
        'intext:"{}" "email"'
    ],

    # ---------------------------------------------------
    # USERNAME (alias)
    # ---------------------------------------------------
    "username": [
        'intext:"{}" site:github.com',
        'intext:"{}" site:gitlab.com',
        'intext:"{}" site:keybase.io',
        'intext:"{}" site:twitter.com',
        'intext:"{}" site:steamcommunity.com',
        'intext:"{}" "username" "profile"'
    ],

    # ---------------------------------------------------
    # EMAIL
    # ---------------------------------------------------
    "email": [
        'intext:"{}" site:pastebin.com',
        'intext:"{}" site:ghostbin.com',
        'intext:"{}" filetype:txt "password"',
        'intext:"{}" "data breach"',
        'intext:"{}" "leaked"',
        'intext:"{}" "credential"'
    ],

    # ---------------------------------------------------
    # TELÉFONO
    # ---------------------------------------------------
    "phone": [
        'intext:"{}" "WhatsApp"',
        'intext:"{}" "Telegram"',
        'intext:"{}" "contact"',
        'intext:"{}" "lookup"',
        'intext:"{}" "reverse phone"'
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
        'intext:"{}" "port"',
        'intext:"{}" "open"',
        'intext:"{}" "ssh"',
        'intext:"{}" "vulnerable"',
        'intext:"{}" "camera"',
    ],

    # ---------------------------------------------------
    # SUBRED
    # ---------------------------------------------------
    "subnet": [
        'intext:"{}" "IP range"',
        'intext:"{}" "open services"',
        'intext:"{}" "network"'
    ],

    # ---------------------------------------------------
    # URL
    # ---------------------------------------------------
    "url": [
        'intext:"{}" "index of"',
        'intext:"{}" "backup"',
        'intext:"{}" "config"',
        'intext:"{}" "credentials"',
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
        # Usar patrones del usuario tal cual, aplicando el formato
        return [pattern.format(query) if "{}" in pattern else pattern for pattern in user_patterns]

    qtype = classify_query_type(query)
    base_dorks = get_dorks_for_type(qtype)

    # Expande {}
    expanded = [d.format(query) for d in base_dorks]

    return expanded


# Alias de funciones para mantener compatibilidad
search_dorks = search_google_dorks
search = search_google_dorks