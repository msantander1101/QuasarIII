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
    """Genera búsquedas de Google Dorks y devuelve detalles de resultados.

    Si no se pasan claves explícitas, intenta leerlas de las variables de entorno
    SERPAPI_API_KEY, GOOGLE_API_KEY y GOOGLE_CUSTOM_SEARCH_CX. En ausencia de
    claves, se recurre a DuckDuckGo.

    Args:
        query: Término que se quiere investigar.
        patterns: Lista de patrones dork (ej.: 'site:pastebin.com').
        max_results: No usado actualmente (reservado).
        serpapi_key: Clave de SerpAPI (prioridad 1).
        google_api_key: Clave de Google Custom Search (prioridad 2).
        google_cx: ID de Search Engine de Google (prioridad 2).

    Returns:
        Una lista de resultados donde cada entrada contiene:
          - 'title': título del dork
          - 'query': consulta dork completa
          - 'url': enlace directo a Google con el dork
          - 'results': lista de subresultados (título, url, snippet, fuente, confianza)
    """
    if not query:
        return []

    # Dorks por defecto
    if patterns is None:
        patterns = [
            'site:pastebin.com',
            'site:github.com "password"',
            'site:linkedin.com',
            'filetype:pdf',
            'filetype:xls',
        ]

    # Fallback a variables de entorno si no vienen claves
    serpapi_key = serpapi_key or os.getenv('SERPAPI_API_KEY')
    google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
    google_cx = google_cx or os.getenv('GOOGLE_CUSTOM_SEARCH_CX')

    results: List[Dict[str, any]] = []

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
