# modules/search/pastesearch.py
"""
Paste & Leak Search — MANUAL ONLY
Este módulo:
- NO se ejecuta automáticamente
- NO depende de Streamlit
- SOLO se llama bajo acción explícita del usuario

Fuentes:
- HIBP (breaches, solo email)
- GitHub Gist
- Google Site Search (básico)
"""

import logging
import requests
import time
import re
from typing import List, Dict, Any
from urllib.parse import quote_plus

from core.config_manager import config_manager

logger = logging.getLogger(__name__)

HIBP_BASE_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"

EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
TIMEOUT = 10
MAX_RESULTS = 10


# ---------------------------------------------------------
# ENTRY POINT (MANUAL)
# ---------------------------------------------------------

def search_pastes(query: str, user_id: int) -> List[Dict[str, Any]]:
    """
    Ejecuta búsqueda de pastes SOLO bajo llamada explícita.
    """
    results: List[Dict[str, Any]] = []

    if not query or len(query.strip()) < 4:
        return results

    query = query.strip()

    # 1️⃣ HIBP (solo email)
    if EMAIL_RE.match(query):
        results.extend(_search_hibp(query, user_id))

    # 2️⃣ GitHub Gist
    results.extend(_search_github_gist(query))

    # 3️⃣ Google Site Search (ligero)
    results.extend(_search_google_site(query))

    return results[:MAX_RESULTS]


# ---------------------------------------------------------
# HIBP
# ---------------------------------------------------------

def _search_hibp(email: str, user_id: int) -> List[Dict[str, Any]]:
    hibp_key = config_manager.get_config(user_id, "hibp")
    if not hibp_key:
        return []

    headers = {
        "x-apikey": hibp_key,
        "User-Agent": "QuasarIII-PasteSearch/1.0"
    }

    try:
        url = f"{HIBP_BASE_URL}/{quote_plus(email.lower())}"
        r = requests.get(url, headers=headers, timeout=TIMEOUT)

        if r.status_code == 200:
            data = r.json()
            return [{
                "title": breach.get("Name"),
                "date": breach.get("Date"),
                "url": breach.get("Link"),
                "source": "HIBP",
                "type": "breach"
            } for breach in data]

    except Exception as e:
        logger.warning(f"HIBP paste error: {e}")

    return []


# ---------------------------------------------------------
# GITHUB GIST
# ---------------------------------------------------------

def _search_github_gist(query: str) -> List[Dict[str, Any]]:
    results = []

    try:
        headers = {"User-Agent": "QuasarIII/1.0"}
        params = {"q": query, "per_page": 5}

        r = requests.get(
            "https://api.github.com/search/gists",
            headers=headers,
            params=params,
            timeout=TIMEOUT
        )

        if r.status_code == 200:
            data = r.json().get("items", [])
            for gist in data:
                results.append({
                    "title": gist.get("description") or "GitHub Gist",
                    "url": gist.get("html_url"),
                    "source": "GitHub Gist",
                    "type": "paste"
                })

    except Exception as e:
        logger.warning(f"Gist search error: {e}")

    return results


# ---------------------------------------------------------
# GOOGLE SITE SEARCH (LIGHT)
# ---------------------------------------------------------

def _search_google_site(query: str) -> List[Dict[str, Any]]:
    return [{
        "title": f"Possible Pastebin result for {query}",
        "url": f"https://pastebin.com/search?q={quote_plus(query)}",
        "source": "Google (site:pastebin)",
        "type": "paste"
    }]
