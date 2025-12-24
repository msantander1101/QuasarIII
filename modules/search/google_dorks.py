"""
Módulo de Google Dorks para QuasarIII

Genera dorks y consulta SerpAPI, Google CSE o DuckDuckGo (best-effort).
✅ Keys desde ConfigManager (DB) por user_id (con fallback env).
✅ Filtrado por site: para evitar falsos positivos (con normalización de redirects).
✅ Fallback inteligente con variantes y por motor (SerpAPI → CSE → DDG).
✅ Devuelve metadata útil para UI (engine, has_key, counts, hint...).
✅ Logging útil (engine, queries, hits, hints, errores SERP).
✅ Soporta only_with_hits: si True, devuelve SOLO entries con hits reales.
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
# URL helpers (redirect normalization)
# ---------------------------------------------------------------------

def _domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _normalize_redirect_url(u: str) -> str:
    """
    Normaliza URLs típicas de redirect:
      - https://www.google.com/url?q=<REAL_URL>&...
      - https://duckduckgo.com/l/?uddg=<REAL_URL>
    Devuelve la URL real si puede, sino la original.
    """
    try:
        if not u:
            return u

        parsed = urlparse(u)
        host = (parsed.netloc or "").lower()

        # Google redirect
        if "google." in host and parsed.path.startswith("/url"):
            qs = parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                return qs["q"][0]

        # DuckDuckGo redirect
        if "duckduckgo.com" in host and (parsed.path.startswith("/l/") or parsed.path.startswith("/l")):
            qs = parse_qs(parsed.query)
            if "uddg" in qs and qs["uddg"]:
                return unquote(qs["uddg"][0])

        return u
    except Exception:
        return u


def _filter_by_site_operator(dork_query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Si el dork lleva site:example.com, filtra hits para que coincidan con ese dominio.
    IMPORTANTE: normaliza redirects antes de extraer el dominio.
    """
    m = re.search(r"site:([a-zA-Z0-9\.\-]+)", dork_query)
    if not m:
        return hits

    site = m.group(1).lower().lstrip("www.")
    filtered: List[Dict[str, Any]] = []

    for h in hits:
        raw_url = (h.get("url") or "").strip()
        real_url = _normalize_redirect_url(raw_url) or raw_url

        # guardamos la url real para la UI
        if real_url and real_url != raw_url:
            h["url_original"] = raw_url
            h["url"] = real_url

        d = _domain(real_url).lstrip("www.")
        if d == site or d.endswith("." + site):
            filtered.append(h)

    return filtered


# ---------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------

def _search_serpapi_raw(dork_q: str, limit: int, serpapi_key: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not serpapi_key:
        return [], None

    try:
        url = "https://serpapi.com/search"
        params = {"engine": "google", "q": dork_q, "api_key": serpapi_key, "num": limit}

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

        hits = []
        for item in data.get("organic_results", [])[:limit]:
            hits.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "source": "SerpAPI",
                "engine": "serpapi",
                "confidence": 0.90,
                "timestamp": time.time(),
            })

        logger.debug("[dorks:serpapi] hits=%s", len(hits))
        return hits, err

    except Exception:
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
            hits = [{
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "source": "Google CSE",
                "engine": "google_cse",
                "confidence": 0.85,
                "timestamp": time.time(),
            } for item in items]
            logger.debug("[dorks:cse] hits=%s", len(hits))
            return hits

        try:
            logger.debug("[dorks:cse] body=%s", (resp.text or "")[:200])
        except Exception:
            pass

    except Exception:
        logger.exception("[dorks:cse] exception")

    return []


def _search_duckduckgo(dork_q: str, limit: int) -> List[Dict[str, Any]]:
    # 1) JSON API
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

    # 2) lite scraping
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; QuasarIII/1.0)",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }

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
                url = _normalize_redirect_url(href)

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
    'site:linkedin.com/in "{}"',
    'site:instagram.com "{}"',
    'site:x.com "{}"',
    'site:twitter.com "{}"',
    'site:t.me "{}"',
    'site:keybase.io "{}"',
    'site:github.com "{}"',
    'site:gitlab.com "{}"',
    '"{}" (cv OR "curriculum vitae" OR resume)',
    '"{}" (bio OR biography OR "about me")',
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
    trace_id: Optional[str] = None,
    only_with_hits: bool = False,   # ✅ IMPORTANTE
) -> List[Dict[str, Any]]:
    if not query:
        return []

    serpapi_key = serpapi_key or config_manager.get_config(user_id, "serpapi_api_key") or os.getenv("SERPAPI_API_KEY")
    google_api_key = google_api_key or config_manager.get_config(user_id, "google_api_key") or os.getenv("GOOGLE_API_KEY")
    google_cx = google_cx or config_manager.get_config(user_id, "google_custom_search_cx") or os.getenv("GOOGLE_CUSTOM_SEARCH_CX")

    dorks_file = dorks_file or os.getenv("QUASAR_DORKS_FILE")

    # ⚙️ Orden de motores: SerpAPI -> CSE -> DDG (fallback)
    engine_order: List[str] = []
    if serpapi_key:
        engine_order.append("serpapi")
    if google_api_key and google_cx:
        engine_order.append("google_cse")
    engine_order.append("ddg")

    primary_engine = engine_order[0]
    engine_has_key = primary_engine in ("serpapi", "google_cse")

    logger.info(
        "[trace=%s] [dorks] engine_order=%s primary=%s has_key=%s user_id=%s max_patterns=%s max_results=%s file=%s only_with_hits=%s",
        trace_id, engine_order, primary_engine, engine_has_key, user_id, max_patterns, max_results, dorks_file, only_with_hits
    )

    if dorks_file:
        loaded = _load_patterns_from_file(dorks_file)
        if loaded.get("patterns"):
            patterns = loaded["patterns"]
            include_profiled = False
            logger.info(
                "[trace=%s] [dorks] patterns loaded from file | count=%s | include_profiled=%s",
                trace_id, len(patterns), include_profiled
            )

    dork_entries = build_dork_queries(
        query,
        patterns=patterns,
        include_profiled=include_profiled,
        max_patterns=max_patterns,
    )

    per_dork_limit = min(5, max_results)

    results: List[Dict[str, Any]] = []

    email_local = query.split("@")[0] if "@" in query else ""

    t_all = time.time()
    executed = 0
    skipped_no_hits = 0
    total_hits = 0
    serpapi_disabled = False  # si da error de pago/cuota, se desactiva para el resto

    for entry in dork_entries:
        executed += 1
        pattern = entry["pattern"]
        base_q = entry["query"]

        logger.debug("[trace=%s] [dorks] run pattern=%s | base_q=%s", trace_id, pattern, base_q)

        variants = [base_q]
        if "@" in query and "site:pastebin.com" in base_q and email_local:
            variants = [
                base_q,
                f'site:pastebin.com "{email_local}"',
                f'"{email_local}" pastebin',
            ]
            logger.debug("[trace=%s] [dorks] variants=%s", trace_id, variants)

        raw_hits_count = 0
        filtered_out = 0
        used_query = base_q
        subresults: List[Dict[str, Any]] = []
        last_error: Optional[str] = None
        engine_used: Optional[str] = None

        for vq in variants:
            # Probar motores en orden
            for eng in engine_order:
                if eng == "serpapi" and serpapi_disabled:
                    continue

                if eng == "serpapi":
                    tmp, err = _search_serpapi_raw(vq, per_dork_limit, serpapi_key or "")
                    last_error = err or last_error

                    # detectar errores de cuota / pago y desactivar serpapi
                    if err and isinstance(err, str):
                        low = err.lower()
                        if any(x in low for x in ["payment", "insufficient", "balance", "quota", "limit"]):
                            logger.warning("[trace=%s] [dorks] disabling serpapi for this run due to error=%s", trace_id, err)
                            serpapi_disabled = True
                elif eng == "google_cse":
                    tmp = _search_google_cse(vq, per_dork_limit, google_api_key or "", google_cx or "")
                    err = None
                else:  # ddg
                    tmp = _search_duckduckgo(vq, per_dork_limit)
                    err = None

                if not isinstance(tmp, list):
                    tmp = []

                before = len(tmp)
                raw_hits_count = max(raw_hits_count, before)

                tmp2 = _filter_by_site_operator(vq, tmp)
                after = len(tmp2)
                filtered_out += max(0, before - after)

                if before != after:
                    logger.debug(
                        "[trace=%s] [dorks] site-filter %s -> %s for q=%s via %s",
                        trace_id, before, after, vq, eng
                    )

                if tmp2:
                    subresults = tmp2
                    used_query = vq
                    engine_used = eng
                    break  # no probamos más motores para esta variante

            if subresults:
                break  # ya tenemos hits, no probamos más variantes

        no_results_hint = None
        if not subresults:
            no_results_hint = "no_serp_hits_or_filtered"
            if isinstance(last_error, str) and "hasn't returned any results" in last_error.lower():
                no_results_hint = "serpapi_no_results"

        total_hits += len(subresults)

        # Si quieres ocultar dorks vacíos (lo que pediste)
        if only_with_hits and not subresults:
            skipped_no_hits += 1
            continue

        google_url = f"https://www.google.com/search?q={quote_plus(used_query)}"

        logger.info(
            "[trace=%s] [dorks] done | pattern=%s | hits=%s | raw_hits=%s | filtered_out=%s | used_query=%s | engine_used=%s | hint=%s",
            trace_id, pattern, len(subresults), raw_hits_count, filtered_out, used_query, engine_used, no_results_hint
        )

        results.append({
            "source": "google_dorks",
            "engine": engine_used or primary_engine,
            "engine_has_key": engine_has_key,
            "limit_used": per_dork_limit,

            "query": used_query,
            "pattern": pattern,
            "title": f"Google Dork: {pattern}",
            "url": google_url,
            "google_url": google_url,
            "description": f"Resultados de dork '{pattern}' para '{query}'",
            "timestamp": time.time(),
            "confidence": 0.80 if subresults else 0.50,
            "results": subresults,

            # métricas para debug/UI
            "subresults_count": len(subresults),
            "raw_hits_count": raw_hits_count,
            "filtered_out": filtered_out,
            "no_results_hint": no_results_hint,
        })

    dt_all = round(time.time() - t_all, 3)
    logger.info(
        "[trace=%s] [dorks] finished | patterns_total=%s executed=%s returned_entries=%s skipped_no_hits=%s total_hits=%s total_time=%ss",
        trace_id, len(dork_entries), executed, len(results), skipped_no_hits, total_hits, dt_all
    )

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
        'site:linkedin.com/in "{}"',
        'site:about.me "{}"',
        'site:medium.com "{}"',
        '"{}" (cv OR "curriculum vitae" OR resume)',
        '"{}" (bio OR biography OR "about me")',
    ],
    "username": [
        'site:github.com "{}"',
        'site:gitlab.com "{}"',
        'site:keybase.io "{}"',
        'site:twitter.com "{}"',
        'site:x.com "{}"',
        'site:reddit.com "{}"',
    ],
    "email": [
        '"{}" (mail OR email OR correo)',
        '"{}" (filetype:pdf OR filetype:doc OR filetype:docx)',
    ],
    "phone": [
        '"{}" ("WhatsApp" OR "Telegram" OR "Signal")',
        '"{}" ("contact" OR "contacto")',
    ],
    "domain": [
        'site:{}',
        'site:{} (contact OR about OR team)',
    ],
    "ip": [
        '"{}" (port OR open OR service)',
    ],
    "subnet": [
        '"{}" ("IP range" OR "network")',
    ],
    "url": [
        '"{}"',
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


search_dorks = search_google_dorks
search = search_google_dorks
