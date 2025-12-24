"""
Módulo de búsqueda de brechas/leaks (best-effort).

Diseñado para ejecución explícita (similar a "dorks"):
- Múltiples fuentes en paralelo
- Salida homogénea para la UI
- Errores controlados, nunca rompemos el flujo
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple, Callable
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)

TIMEOUT = 12
MAX_RESULTS = 25
MAX_WORKERS = 5  # ajustable si añades más proveedores


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def search_breaches(
    query: str,
    user_id: int = 1,
    max_results: int = MAX_RESULTS,
) -> Dict[str, Any]:
    """
    Busca filtraciones en múltiples fuentes públicas.

    Devuelve un diccionario con:
      - source: "breach"
      - query: consulta normalizada
      - user_id
      - timestamp: epoch en segundos
      - results: lista de hits normalizados
      - errors: lista de errores por proveedor (para debug/UI)
      - has_data: bool
      - search_time: tiempo total en segundos

    NOTA: La intención es que el contrato sea muy similar al módulo de dorks,
    manteniendo compatibilidad con la UI actual.
    """
    start = time.time()
    clean_query = (query or "").strip()

    out: Dict[str, Any] = {
        "source": "breach",
        "query": clean_query,
        "user_id": user_id,
        "timestamp": time.time(),
        "results": [],
        "errors": [],
        "has_data": False,
        "search_time": 0.0,
    }

    if not clean_query:
        out["errors"].append("empty_query")
        return out

    # Definición de proveedores: nombre lógico + función
    providers: List[Tuple[str, Callable[[str], Tuple[List[Dict[str, Any]], str]]]] = [
        ("haveibeenransom", _search_haveibeenransom),
        ("antipublic", _search_antipublic),
        ("based_re", _search_based_re),
        ("scatteredsecrets", _search_scattered_secrets),
        ("psbdmp", _search_psbdmp),
    ]

    # -----------------------------------------------------------------------
    # Ejecución en paralelo (estilo dorks: varios proveedores a la vez)
    # -----------------------------------------------------------------------
    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    with ThreadPoolExecutor(max_workers=min(len(providers), MAX_WORKERS)) as executor:
        future_to_provider = {
            executor.submit(_run_provider_safe, name, func, clean_query): name
            for name, func in providers
        }

        for future in as_completed(future_to_provider):
            name = future_to_provider[future]
            try:
                hits, err = future.result()
                if hits:
                    # Normalización mínima de campos comunes para UI
                    for h in hits:
                        h.setdefault("source", name)
                        h.setdefault("engine", name)        # 🆕 para chips UI
                        h.setdefault("type", "breach")
                        h.setdefault("entity_type", "leak")  # 🆕 icono "leak"
                        h.setdefault("match_type", "exact")  # 🆕 búsqueda directa
                        # relevance_score derivado de confidence si no viene
                        if "relevance_score" not in h:
                            conf = h.get("confidence")
                            try:
                                if conf is not None:
                                    h["relevance_score"] = int(round(float(conf) * 100))
                            except Exception:
                                pass
                    results.extend(hits)
                if err:
                    errors.append(f"{name}:{err}")
            except Exception as e:  # pragma: no cover - defensivo
                logger.exception("[breach:%s] unexpected error in future", name)
                errors.append(f"{name}:exception:{e}")

    # -----------------------------------------------------------------------
    # Post-procesado: deduplicado básico + recorte de resultados
    # -----------------------------------------------------------------------
    deduped_results: List[Dict[str, Any]] = []
    seen_keys = set()

    for r in results:
        # Clave de deduplicado: URL + título (simple pero efectivo)
        key = (r.get("url"), r.get("title"))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_results.append(r)

    max_results = max_results or MAX_RESULTS
    deduped_results = deduped_results[:max_results]

    out["results"] = deduped_results
    out["errors"] = errors
    out["has_data"] = bool(deduped_results)
    out["search_time"] = round(time.time() - start, 3)

    return out


# ---------------------------------------------------------------------------
# Infraestructura interna
# ---------------------------------------------------------------------------


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None


def _manual_result(url: str, title: str) -> List[Dict[str, Any]]:
    """
    Resultado "manual" de baja confianza cuando la API no responde o hay error.

    Sirve para que la UI pueda seguir ofreciendo un enlace al recurso,
    similar al comportamiento de fallback en el módulo de dorks.
    """
    conf = 0.3
    return [
        {
            "title": title,
            "url": url,
            "source": "manual",
            "engine": "manual",
            "type": "breach",
            "entity_type": "leak",
            "match_type": "contextual",
            "confidence": conf,
            "relevance_score": int(round(conf * 100)),
        }
    ]


def _run_provider_safe(
    name: str,
    func: Callable[[str], Tuple[List[Dict[str, Any]], str]],
    query: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Wrapper defensivo para proveedores.

    Garantiza que:
      - Nunca se propaga una excepción hacia arriba.
      - Siempre se devuelve (hits, error_str).
    """
    try:
        hits, err = func(query)
        return hits or [], err
    except Exception as e:  # pragma: no cover - defensivo
        logger.exception("[breach:%s] unhandled exception", name)
        # Devolvemos sin hits y con error, la llamada principal decidirá
        return [], f"exception:{e}"


# ---------------------------------------------------------------------------
# Proveedores
# ---------------------------------------------------------------------------


def _search_haveibeenransom(query: str) -> Tuple[List[Dict[str, Any]], str]:
    """Best-effort lookup against haveibeenransom.com."""
    api_url = "https://haveibeenransom.com/api/v1/search"
    manual_url = f"https://haveibeenransom.com/?search={quote_plus(query)}"

    try:
        r = requests.get(api_url, params={"query": query}, timeout=TIMEOUT)
        logger.debug("[breach:haveibeenransom] http=%s", r.status_code)

        if r.status_code == 200:
            data = _safe_json(r)
            hits: List[Dict[str, Any]] = []
            for item in data or []:
                date_val = item.get("date") or item.get("updated_at")
                conf = 0.75
                hits.append(
                    {
                        "title": item.get("title")
                        or item.get("name")
                        or "HaveIBeenRansom hit",
                        "url": item.get("link") or manual_url,
                        "date": date_val,
                        "timestamp": date_val,  # 🆕 alias para UI
                        "snippet": item.get("description") or item.get("summary"),
                        "confidence": conf,
                        # campos extra alineados con dorks_block (por si se usan directamente)
                        "entity_type": "leak",
                        "match_type": "exact",
                        "relevance_score": int(round(conf * 100)),
                    }
                )
            if hits:
                return hits, None

        # Fallback manual
        return _manual_result(manual_url, "Check HaveIBeenRansom manually"), f"http_{r.status_code}"
    except Exception as e:
        logger.warning("[breach:haveibeenransom] %s", e)
        return _manual_result(manual_url, "Check HaveIBeenRansom manually"), str(e)


def _search_antipublic(query: str) -> Tuple[List[Dict[str, Any]], str]:
    """Basic GET lookup on antipublic.net (best-effort, may require manual check)."""
    api_url = "https://antipublic.net/search"
    manual_url = f"{api_url}?q={quote_plus(query)}"

    try:
        r = requests.get(api_url, params={"q": query}, timeout=TIMEOUT)
        logger.debug("[breach:antipublic] http=%s", r.status_code)

        if r.status_code == 200:
            data = _safe_json(r)
            hits: List[Dict[str, Any]] = []
            for item in data or []:
                conf = 0.7
                hits.append(
                    {
                        "title": item.get("title") or "Antipublic hit",
                        "url": item.get("url") or manual_url,
                        "snippet": item.get("preview") or item.get("text"),
                        "confidence": conf,
                        "entity_type": "leak",
                        "match_type": "exact",
                        "relevance_score": int(round(conf * 100)),
                    }
                )
            if hits:
                return hits, None

        return _manual_result(manual_url, "Check Antipublic manually"), f"http_{r.status_code}"
    except Exception as e:
        logger.warning("[breach:antipublic] %s", e)
        return _manual_result(manual_url, "Check Antipublic manually"), str(e)


def _search_based_re(query: str) -> Tuple[List[Dict[str, Any]], str]:
    """Search on bf.based.re (BreachForums mirror)."""
    api_url = "https://bf.based.re/search"
    manual_url = f"{api_url}?q={quote_plus(query)}"

    try:
        r = requests.get(api_url, params={"q": query}, timeout=TIMEOUT)
        logger.debug("[breach:based.re] http=%s", r.status_code)

        if r.status_code == 200:
            data = _safe_json(r)
            hits: List[Dict[str, Any]] = []
            for item in data or []:
                conf = 0.65
                hits.append(
                    {
                        "title": item.get("title") or "BreachForums mirror hit",
                        "url": item.get("url") or manual_url,
                        "snippet": item.get("snippet") or item.get("summary"),
                        "confidence": conf,
                        "entity_type": "leak",
                        "match_type": "exact",
                        "relevance_score": int(round(conf * 100)),
                    }
                )
            if hits:
                return hits, None

        return _manual_result(manual_url, "Check bf.based.re manually"), f"http_{r.status_code}"
    except Exception as e:
        logger.warning("[breach:based.re] %s", e)
        return _manual_result(manual_url, "Check bf.based.re manually"), str(e)


def _search_scattered_secrets(query: str) -> Tuple[List[Dict[str, Any]], str]:
    """Scattered Secrets helper (often requires manual review)."""
    api_url = "https://scatteredsecrets.com/search"
    manual_url = f"{api_url}?q={quote_plus(query)}"

    try:
        r = requests.get(api_url, params={"q": query}, timeout=TIMEOUT)
        logger.debug("[breach:scatteredsecrets] http=%s", r.status_code)

        if r.status_code == 200:
            data = _safe_json(r)
            hits: List[Dict[str, Any]] = []
            for item in data or []:
                conf = 0.7
                hits.append(
                    {
                        "title": item.get("title") or "Scattered Secrets hit",
                        "url": item.get("url") or manual_url,
                        "snippet": item.get("password") or item.get("detail"),
                        "confidence": conf,
                        "entity_type": "leak",
                        "match_type": "exact",
                        "relevance_score": int(round(conf * 100)),
                    }
                )
            if hits:
                return hits, None

        return _manual_result(manual_url, "Check Scattered Secrets manually"), f"http_{r.status_code}"
    except Exception as e:
        logger.warning("[breach:scatteredsecrets] %s", e)
        return _manual_result(manual_url, "Check Scattered Secrets manually"), str(e)


def _search_psbdmp(query: str) -> Tuple[List[Dict[str, Any]], str]:
    """Search psbdmp.ws API (returns JSON)."""
    url = f"https://psbdmp.ws/api/v3/search/{query}"

    try:
        r = requests.get(url, timeout=TIMEOUT)
        logger.debug("[breach:psbdmp] http=%s", r.status_code)

        if r.status_code == 200:
            data = _safe_json(r) or {}
            raw_hits = data.get("data", []) if isinstance(data, dict) else []
            hits: List[Dict[str, Any]] = []
            for item in raw_hits:
                paste_id = item.get("id") or item.get("_id")
                conf = 0.9
                ts = item.get("date") or item.get("added")
                hits.append(
                    {
                        "title": item.get("title")
                        or (f"psbdmp result {paste_id}" if paste_id else "psbdmp result"),
                        "url": f"https://pastebin.com/{paste_id}" if paste_id else url,
                        "snippet": item.get("text")
                        or item.get("email")
                        or item.get("line"),
                        "timestamp": ts,
                        "confidence": conf,
                        "entity_type": "paste",
                        "match_type": "exact",
                        "relevance_score": int(round(conf * 100)),
                    }
                )
            if hits:
                return hits, None

        return _manual_result(url, "Check psbdmp.ws manually"), f"http_{r.status_code}"
    except Exception as e:
        logger.warning("[breach:psbdmp] %s", e)
        return _manual_result(url, "Check psbdmp.ws manually"), str(e)
