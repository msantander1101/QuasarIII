"""
Módulo de Google Dorks para QuasarIII

Genera dorks y consulta SerpAPI, Google CSE o DuckDuckGo.
Las API keys se obtienen preferentemente desde ConfigManager (DB) por user_id.
"""

import time
import os
import logging
import requests
from typing import Any, List, Dict, Optional, Iterable
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
import re
from functools import lru_cache
from bs4 import BeautifulSoup

from utils.dorks_loader import load_dorks_txt, load_dorks_json, guess_loader
from core.config_manager import config_manager  # ✅ NUEVO

logger = logging.getLogger(__name__)


def _search_serpapi(dork_q: str, limit: int, serpapi_key: str) -> List[Dict[str, Any]]:
    if not serpapi_key:
        return []
    try:
        url = "https://serpapi.com/search"
        params = {"engine": "google", "q": dork_q, "api_key": serpapi_key, "num": limit}
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": "SerpAPI",
                    "engine": "serpapi",
                    "confidence": 0.90,
                    "timestamp": time.time(),
                }
                for item in data.get("organic_results", [])[:limit]
            ]
        logger.debug("SerpAPI non-200: %s %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.debug("SerpAPI exception: %s", e)
    return []


def _search_google_cse(dork_q: str, limit: int, google_api_key: str, google_cx: str) -> List[Dict[str, Any]]:
    if not (google_api_key and google_cx):
        return []
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": google_api_key, "cx": google_cx, "q": dork_q, "num": min(limit, 10)}
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": "Google CSE",
                    "engine": "google_cse",
                    "confidence": 0.85,
                    "timestamp": time.time(),
                }
                for item in data.get("items", [])[:limit]
            ]
        logger.debug("Google CSE non-200: %s %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.debug("Google CSE exception: %s", e)
    return []


def _extract_ddg_redirect(href: str) -> str:
    try:
        if not href:
            return href
        if href.startswith("/l/") or "duckduckgo.com/l/" in href:
            if href.startswith("/"):
                href = "https://duckduckgo.com" + href
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            if "uddg" in qs and qs["uddg"]:
                return unquote(qs["uddg"][0])
        return href
    except Exception:
        return href


def _search_duckduckgo(dork_q: str, limit: int) -> List[Dict[str, Any]]:
    # API JSON
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
                            'engine': 'ddg_api',
                            'confidence': 0.55,
                            'timestamp': time.time(),
                        })
                return subresults

            extracted = extract_topics(data.get('RelatedTopics', []))
            if extracted:
                return extracted[:limit]
    except Exception as e:
        logger.debug("DDG API exception: %s", e)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; QuasarIII/1.0)",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    # lite (más estable)
    try:
        html_resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": dork_q},
            headers=headers,
            timeout=15,
        )
        if html_resp.status_code == 200 and html_resp.text:
            soup = BeautifulSoup(html_resp.text, "html.parser")
            results: List[Dict[str, Any]] = []
            for a in soup.select("a.result-link"):
                title = a.get_text(strip=True) or "Sin título"
                href = a.get("href") or ""
                url = _extract_ddg_redirect(href)
                results.append({
                    "title": title,
                    "url": url or "#",
                    "snippet": "",
                    "source": "DuckDuckGo",
                    "engine": "ddg_lite",
                    "confidence": 0.65,
                    "timestamp": time.time(),
                })
                if len(results) >= limit:
                    break
            if results:
                return results
    except Exception as e:
        logger.debug("DDG lite exception: %s", e)

    return []


DEFAULT_DORKS = [
    'intext:"{}" site:linkedin.com/in',
    'intext:"{}" site:instagram.com',
    'intext:"{}" site:twitter.com',
    'intext:"{}" site:t.me',
    'intext:"{}" site:keybase.io',
    'intext:"powered by discourse" intext:"view user"',
    'intext:"index of /users"',
    'intext:"{}" site:pastebin.com',
    'intext:"{}" site:ghostbin.com',
    'intext:"{}" site:dpaste.org',
    'intext:"password" intext:"lastpass" filetype:txt',
    'intext:"password" intext:"admin" filetype:xls',
    'intext:"credentials exposed"',
    'intext:"{}" site:github.com "API_KEY"',
    'intext:"{}" site:github.com "SECRET_KEY"',
    'intext:"{}" site:gitlab.com "token"',
    'intext:"filename:.env" intext:"DB_PASSWORD"',
    'intext:"{}" filetype:pdf',
    'intext:"{}" filetype:xls',
    'intext:"{}" filetype:txt "confidential"',
    'intext:"index of" intext:"backup"',
    'intext:"index of" intext:"logs"',
    'intext:"{}" inurl:wp-config.php',
    'intext:"{}" inurl:wp-admin "index of"',
    'intext:"{}" site:*/wp-content/uploads',
    'intext:"{}" intitle:"WordPress Users"',
    'intext:"{}" site:amazonaws.com "index of"',
    'intext:"{}" site:storage.googleapis.com "index of"',
    'intext:"{}" "index of" "azure"',
    'intext:"Server at" intext:"port" intext:"Apache"',
    'intext:"Dashboard" intext:"login" intext:"admin"',
    'intext:"camera" intext:"inurl:view.shtml"',
    'intext:"index of" intext:"mysql dump"',
]


def _deduplicate_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _load_patterns_from_file(dorks_file: str) -> Dict[str, Any]:
    mode = guess_loader(dorks_file)
    if mode == "json":
        data = load_dorks_json(dorks_file)
        if not data:
            return {"patterns": None, "profiled_map": None}
        default = data.get("default") or []
        profiled = {k: v for k, v in data.items() if k != "default"}
        return {"patterns": default or None, "profiled_map": profiled or None}

    patterns = load_dorks_txt(dorks_file)
    return {"patterns": patterns or None, "profiled_map": None}


def build_dork_queries(query: str,
                       patterns: Optional[List[str]] = None,
                       include_profiled: bool = True,
                       max_patterns: Optional[int] = None) -> List[Dict[str, str]]:
    seed_patterns: List[str] = []
    if patterns:
        seed_patterns.extend(patterns)
    if include_profiled and not patterns:
        seed_patterns.extend(generate_profiled_dorks(query))
    if not seed_patterns:
        seed_patterns.extend(DEFAULT_DORKS)

    normalized_patterns = _deduplicate_preserve_order([p.strip() for p in seed_patterns if p])

    output: List[Dict[str, str]] = []
    for pattern in normalized_patterns:
        try:
            formatted_query = pattern.format(query) if ("{" in pattern and "}" in pattern) else pattern
        except Exception:
            formatted_query = pattern

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


def search_google_dorks(
    query: str,
    patterns: Optional[List[str]] = None,
    max_results: int = 10,
    serpapi_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
    google_cx: Optional[str] = None,
    max_patterns: Optional[int] = None,
    include_profiled: bool = True,
    dorks_file: Optional[str] = None,
    user_id: int = 1,  # ✅ NUEVO: para ConfigManager
) -> List[Dict[str, Any]]:
    if not query:
        return []

    # ✅ Prefer DB (ConfigManager), fallback a env por compatibilidad
    serpapi_key = serpapi_key or config_manager.get_config(user_id, "serpapi_api_key") or os.getenv("SERPAPI_API_KEY")
    google_api_key = google_api_key or config_manager.get_config(user_id, "google_api_key") or os.getenv("GOOGLE_API_KEY")
    google_cx = google_cx or config_manager.get_config(user_id, "google_custom_search_cx") or os.getenv("GOOGLE_CUSTOM_SEARCH_CX")

    dorks_file = dorks_file or os.getenv("QUASAR_DORKS_FILE")

    engine = "ddg"
    if serpapi_key:
        engine = "serpapi"
    elif google_api_key and google_cx:
        engine = "google_cse"

    if dorks_file:
        loaded = _load_patterns_from_file(dorks_file)
        if loaded.get("patterns"):
            patterns = loaded["patterns"]
            include_profiled = False

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

    results: List[Dict[str, Any]] = []
    for entry in dork_entries:
        dork_query = entry["query"]
        pattern = entry["pattern"]
        google_url = entry["google_url"]

        subresults = search_method(dork_query, min(5, max_results))
        if not isinstance(subresults, list):
            subresults = []

        results.append({
            "source": "google_dorks",
            "engine": engine,
            "query": dork_query,
            "pattern": pattern,
            "title": f"Google Dork: {pattern}",
            "url": google_url,
            "google_url": google_url,
            "description": f"Resultados de dork '{pattern}' para '{query}'",
            "timestamp": time.time(),
            "confidence": 0.80 if subresults else 0.50,
            "results": subresults,
        })

    return results


@lru_cache(maxsize=1024)
def classify_query_type(query: str) -> str:
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
    return "person"


_DORKS_BY_TYPE = {
    "person": [
        'intext:"{}" site:linkedin.com/in',
        'intext:"{}" site:facebook.com',
        'intext:"{}" site:instagram.com',
        'intext:"{}" "curriculum vitae"',
        'intext:"{}" "phone number"',
        'intext:"{}" "email"'
    ],
    "username": [
        'intext:"{}" site:github.com',
        'intext:"{}" site:gitlab.com',
        'intext:"{}" site:keybase.io',
        'intext:"{}" site:twitter.com',
        'intext:"{}" site:steamcommunity.com',
        'intext:"{}" "username" "profile"'
    ],
    "email": [
        'intext:"{}" site:pastebin.com',
        'intext:"{}" site:ghostbin.com',
        'intext:"{}" filetype:txt "password"',
        'intext:"{}" "data breach"',
        'intext:"{}" "leaked"',
        'intext:"{}" "credential"'
    ],
    "phone": [
        'intext:"{}" "WhatsApp"',
        'intext:"{}" "Telegram"',
        'intext:"{}" "contact"',
        'intext:"{}" "lookup"',
        'intext:"{}" "reverse phone"'
    ],
    "domain": [
        'site:{}/wp-admin',
        'site:{}/wp-content',
        'site:{}/.git',
        'site:{}/"index of"',
        'site:pastebin.com "{}"',
        'site:github.com "{}"',
    ],
    "ip": [
        'intext:"{}" "port"',
        'intext:"{}" "open"',
        'intext:"{}" "ssh"',
        'intext:"{}" "vulnerable"',
        'intext:"{}" "camera"',
    ],
    "subnet": [
        'intext:"{}" "IP range"',
        'intext:"{}" "open services"',
        'intext:"{}" "network"'
    ],
    "url": [
        'intext:"{}" "index of"',
        'intext:"{}" "backup"',
        'intext:"{}" "config"',
        'intext:"{}" "credentials"',
    ],
}


def get_dorks_for_type(query_type: str) -> List[str]:
    return _DORKS_BY_TYPE.get(query_type, [])


def generate_profiled_dorks(query: str, user_patterns: Optional[List[str]] = None) -> List[str]:
    if user_patterns:
        return [pattern.format(query) if ("{" in pattern and "}" in pattern) else pattern for pattern in user_patterns]

    qtype = classify_query_type(query)
    base_dorks = get_dorks_for_type(qtype)

    expanded: List[str] = []
    for d in base_dorks:
        try:
            expanded.append(d.format(query) if ("{" in d and "}" in d) else d)
        except Exception:
            expanded.append(d)

    return expanded


search_dorks = search_google_dorks
search = search_google_dorks
