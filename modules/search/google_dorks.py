"""
Módulo de Google Dorks para QuasarIII

Genera dorks y consulta SerpAPI, Google CSE o DuckDuckGo (best-effort).
✅ Keys desde ConfigManager (DB) por user_id (con fallback env).
✅ Filtrado por site: para evitar falsos positivos.
✅ Fallback inteligente con variantes para aumentar hallazgos.
✅ Devuelve metadata útil para UI (engine, has_key, counts, hint...).
✅ Logging útil (engine, queries, hits, hints, errores SERP).
"""

import time
import os
import logging
import requests
from typing import Any, List, Dict, Optional, Iterable, Tuple
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
import re
from functools import lru_cache
from bs4 import BeautifulSoup

from utils.dorks_loader import load_dorks_txt, load_dorks_json, guess_loader
from core.config_manager import config_manager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Helpers URL / site filtering
# ---------------------------------------------------------------------

def _domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _filter_by_site_operator(dork_query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Si el dork lleva site:example.com, filtra hits para que coincidan con ese dominio.
    Evita falsos positivos (ej: devuelve LinkedIn aunque el dork diga pastebin).
    """
    m = re.search(r"site:([a-zA-Z0-9\.\-]+)", dork_query)
    if not m:
        return hits

    site = m.group(1).lower().lstrip("www.")
    filtered: List[Dict[str, Any]] = []

    for h in hits:
        u = (h.get("url") or "").strip()
        d = _domain(u).lstrip("www.")
        if d == site or d.endswith("." + site):
            filtered.append(h)

    return filtered


# ---------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------

def _search_serpapi_raw(dork_q: str, limit: int, serpapi_key: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Devuelve (hits, error_msg).
    error_msg puede contener el campo "error" de SerpAPI, p.ej:
    "Google hasn't returned any results for this query."
    """
    if not serpapi_key:
        return [], None

    try:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": dork_q,
            "api_key": serpapi_key,
            "num": limit,
        }

        t0 = time.time()
        resp = requests.get(url, params=params, timeout=30)
        dt = round(time.time() - t0, 3)

        logger.debug("[dorks:serpapi] http=%s time=%ss q=%s", resp.status_code, dt, dork_q)

        if resp.status_code != 200:
            return [], f"serpapi_http_{resp.status_code}"

        data = resp.json() if resp.text else {}
        err = data.get("error")
        if err:
            logger.debug("[dorks:serpapi] api_error=%s", err)

        hits = [
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

        logger.debug("[dorks:serpapi] hits=%s", len(hits))
        return hits, err

    except Exception as e:
        logger.exception("[dorks:serpapi] exception")
        return [], "serpapi_exception"


def _search_google_cse(dork_q: str, limit: int, google_api_key: str, google_cx: str) -> List[Dict[str, Any]]:
    if not (google_api_key and google_cx):
        return []

    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": google_api_key, "cx": google_cx, "q": dork_q, "num": min(limit, 10)}

        t0 = time.time()
        resp = requests.get(url, params=params, timeout=20)
        dt = round(time.time() - t0, 3)

        logger.debug("[dorks:cse] http=%s time=%ss q=%s", resp.status_code, dt, dork_q)

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])[:limit]
            hits = [
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": "Google CSE",
                    "engine": "google_cse",
                    "confidence": 0.85,
                    "timestamp": time.time(),
                }
                for item in items
            ]
            logger.debug("[dorks:cse] hits=%s", len(hits))
            return hits

        # si falla, intenta loguear cuerpo corto
        try:
            logger.debug("[dorks:cse] body=%s", (resp.text or "")[:200])
        except Exception:
            pass

    except Exception:
        logger.exception("[dorks:cse] exception")

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
    """
    Best-effort sin key.
    """
    # 1) JSON API (no siempre devuelve SERP real)
    try:
        api_url = (
            f"https://api.duckduckgo.com/?q={quote_plus(dork_q)}"
            "&format=json&no_redirect=1&skip_disambig=1"
        )
        t0 = time.time()
        response = requests.get(api_url, timeout=10)
        dt = round(time.time() - t0, 3)

        logger.debug("[dorks:ddg_api] http=%s time=%ss q=%s", response.status_code, dt, dork_q)

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
    except Exception:
        pass

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; QuasarIII/1.0)",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

    # 2) lite (mejor para scraping básico)
    try:
        t0 = time.time()
        html_resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": dork_q},
            headers=headers,
            timeout=15,
        )
        dt = round(time.time() - t0, 3)

        logger.debug("[dorks:ddg_lite] http=%s time=%ss q=%s", html_resp.status_code, dt, dork_q)

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
    except Exception:
        pass

    return []


# ---------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------

DEFAULT_DORKS = [
    'intext:"{}" site:linkedin.com/in',
    'intext:"{}" site:instagram.com',
    'intext:"{}" site:twitter.com',
    'intext:"{}" site:t.me',
    'intext:"{}" site:keybase.io',
    'intext:"{}" site:pastebin.com',
    'intext:"{}" site:ghostbin.com',
    'intext:"{}" site:dpaste.org',
    'intext:"{}" filetype:txt "password"',
    'intext:"{}" "data breach"',
    'intext:"{}" "leaked"',
    'intext:"{}" "credential"',
]


def _deduplicate_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
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


def build_dork_queries(
    query: str,
    patterns: Optional[List[str]] = None,
    include_profiled: bool = True,
    max_patterns: Optional[int] = None
) -> List[Dict[str, str]]:
    seed: List[str] = []

    if patterns:
        seed.extend(patterns)

    if include_profiled and not patterns:
        seed.extend(generate_profiled_dorks(query))

    if not seed:
        seed.extend(DEFAULT_DORKS)

    normalized = _deduplicate_preserve_order([p.strip() for p in seed if p and p.strip()])

    out: List[Dict[str, str]] = []
    for pattern in normalized:
        try:
            formatted = pattern.format(query) if ("{" in pattern and "}" in pattern) else pattern
        except Exception:
            formatted = pattern

        formatted = formatted.strip()
        if not formatted:
            continue

        out.append({
            "pattern": pattern,
            "query": formatted,
            "google_url": f"https://www.google.com/search?q={quote_plus(formatted)}",
        })

        if max_patterns and len(out) >= max_patterns:
            break

    return out


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

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
    user_id: int = 1,
) -> List[Dict[str, Any]]:
    if not query:
        return []

    # Keys: DB first, env fallback
    serpapi_key = serpapi_key or config_manager.get_config(user_id, "serpapi_api_key") or os.getenv("SERPAPI_API_KEY")
    google_api_key = google_api_key or config_manager.get_config(user_id, "google_api_key") or os.getenv("GOOGLE_API_KEY")
    google_cx = google_cx or config_manager.get_config(user_id, "google_custom_search_cx") or os.getenv("GOOGLE_CUSTOM_SEARCH_CX")

    # dorks file: param first, env fallback
    dorks_file = dorks_file or os.getenv("QUASAR_DORKS_FILE")

    engine = "ddg"
    engine_has_key = False

    if serpapi_key:
        engine = "serpapi"
        engine_has_key = True
    elif google_api_key and google_cx:
        engine = "google_cse"
        engine_has_key = True
    else:
        engine = "ddg"
        engine_has_key = False

    logger.info(
        "[dorks] engine=%s has_key=%s user_id=%s max_patterns=%s max_results=%s dorks_file=%s",
        engine, engine_has_key, user_id, max_patterns, max_results, dorks_file
    )

    # load patterns if file provided
    if dorks_file:
        loaded = _load_patterns_from_file(dorks_file)
        if loaded.get("patterns"):
            patterns = loaded["patterns"]
            include_profiled = False
            logger.info("[dorks] patterns loaded from file | count=%s | include_profiled=%s",
                        len(patterns), include_profiled)

    dork_entries = build_dork_queries(
        query,
        patterns=patterns,
        include_profiled=include_profiled,
        max_patterns=max_patterns,
    )

    per_dork_limit = min(5, max_results)
    logger.debug("[dorks] entries=%s per_dork_limit=%s", len(dork_entries), per_dork_limit)

    def _run_search(dq: str, limit: int) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """(hits, error_msg)"""
        if engine == "serpapi":
            return _search_serpapi_raw(dq, limit, serpapi_key or "")
        if engine == "google_cse":
            return _search_google_cse(dq, limit, google_api_key or "", google_cx or ""), None
        return _search_duckduckgo(dq, limit), None

    results: List[Dict[str, Any]] = []

    # Para fallbacks “email pastebin”
    email_local = query.split("@")[0] if "@" in query else ""

    t_all = time.time()

    for entry in dork_entries:
        dork_query = entry["query"]
        pattern = entry["pattern"]

        logger.debug("[dorks] run pattern=%s | q=%s", pattern, dork_query)

        # ✅ Variantes + filtrado por site:
        variants = [dork_query]

        # Email + pastebin: Google puede devolver "no results"; pivot a variantes más amplias
        if "@" in query and "site:pastebin.com" in dork_query and email_local:
            variants = [
                dork_query,
                f'site:pastebin.com intext:"{email_local}"',
                f'"{email_local}" pastebin',
            ]
            logger.debug("[dorks] variants=%s", variants)

        subresults: List[Dict[str, Any]] = []
        used_query = dork_query
        last_error: Optional[str] = None

        for vq in variants:
            tmp, err = _run_search(vq, per_dork_limit)
            last_error = err or last_error

            if err:
                logger.debug("[dorks] engine_error=%s q=%s", err, vq)

            if not isinstance(tmp, list):
                tmp = []

            before = len(tmp)
            tmp = _filter_by_site_operator(vq, tmp)
            after = len(tmp)
            if before != after:
                logger.debug("[dorks] site-filter reduced hits %s -> %s for q=%s", before, after, vq)

            if tmp:
                subresults = tmp
                used_query = vq
                break

        dork_query = used_query
        google_url = f"https://www.google.com/search?q={quote_plus(dork_query)}"

        # Hint para UI
        no_results_hint = None
        if not subresults:
            no_results_hint = "no_serp_hits_or_filtered"
            if isinstance(last_error, str) and "hasn't returned any results" in last_error.lower():
                no_results_hint = "serpapi_no_results"

        logger.info("[dorks] done | pattern=%s | hits=%s | used_query=%s | hint=%s",
                    pattern, len(subresults), dork_query, no_results_hint)

        results.append({
            "source": "google_dorks",
            "engine": engine,
            "engine_has_key": engine_has_key,
            "limit_used": per_dork_limit,
            "subresults_count": len(subresults),

            "query": dork_query,
            "pattern": pattern,
            "title": f"Google Dork: {pattern}",
            "url": google_url,
            "google_url": google_url,
            "description": f"Resultados de dork '{pattern}' para '{query}'",
            "timestamp": time.time(),
            "confidence": 0.80 if subresults else 0.50,
            "results": subresults,
            "no_results_hint": no_results_hint,
        })

    logger.info("[dorks] finished | total_entries=%s | total_time=%ss",
                len(results), round(time.time() - t_all, 3))

    return results


# ---------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------

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
        return [p.format(query) if ("{" in p and "}" in p) else p for p in user_patterns]

    qtype = classify_query_type(query)
    base = get_dorks_for_type(qtype)

    expanded: List[str] = []
    for d in base:
        try:
            expanded.append(d.format(query) if ("{" in d and "}" in d) else d)
        except Exception:
            expanded.append(d)

    return expanded


# Alias
search_dorks = search_google_dorks
search = search_google_dorks
