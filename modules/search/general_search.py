# modules/search/general_search.py
"""
General Search — OSINT Pasivo y Controlado
✔ No ejecuta fuentes sensibles automáticamente
✔ Diseñado como radar contextual (web, menciones, superficie)
✔ Compatible con arquitectura Quasar III
"""

import logging
import requests
import time
from typing import Dict, List, Any
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from core.config_manager import config_manager

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN GLOBAL
# ============================================================

PASSIVE_SOURCES = {
    "web_search",
    "google_search",
    "bing_search",
    "duckduckgo_search"
}

ACTIVE_OPTIONAL_SOURCES = {
    "serpapi",
    "openai",
    "predictasearch"
}

FORBIDDEN_SOURCES = {
    "hibp",
    "hunter",
    "shodan",
    "virustotal",
    "whoisxml"
}


class GeneralSearcher:
    """
    Buscador OSINT general PASIVO.
    No realiza enriquecimiento sensible ni correlación.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "QuasarIII-GeneralSearch/1.0"
        })
        self.timeout = 20

    # --------------------------------------------------------
    # FUENTES DISPONIBLES (solo informativo)
    # --------------------------------------------------------
    def get_user_sources(self, user_id: int) -> Dict[str, Dict]:
        sources = {}

        # Fuentes pasivas SIEMPRE disponibles
        for src in PASSIVE_SOURCES:
            sources[src] = {
                "enabled": True,
                "requires_api": False
            }

        # Fuentes activas opcionales (solo si hay API key)
        for key, name in {
            "serpapi": "serpapi",
            "openai_api_key": "openai",
            "predictasearch_api_key": "predictasearch"
        }.items():
            api_key = config_manager.get_config(user_id, key)
            if api_key:
                sources[name] = {
                    "enabled": True,
                    "requires_api": True,
                    "api_key": api_key
                }

        return sources

    # --------------------------------------------------------
    # BÚSQUEDA GENERAL
    # --------------------------------------------------------
    def search_general_real(
        self,
        query: str,
        user_id: int,
        sources: List[str] = None,
        mode: str = "passive",
        max_results: int = 10
    ) -> Dict[str, Any]:

        start = time.time()
        logger.info(f"[GeneralSearch] query='{query}' mode={mode}")

        # Modo pasivo seguro por defecto
        if not sources:
            sources = list(PASSIVE_SOURCES)

        # Filtrado por modo
        if mode == "passive":
            sources = [s for s in sources if s in PASSIVE_SOURCES]

        elif mode == "active":
            sources = [
                s for s in sources
                if s in PASSIVE_SOURCES or s in ACTIVE_OPTIONAL_SOURCES
            ]

        # Bloqueo duro de fuentes prohibidas
        sources = [s for s in sources if s not in FORBIDDEN_SOURCES]

        results = {
            "query": query,
            "intent": "contextual_search",
            "mode": mode,
            "sources_used": sources,
            "raw_results": {},
            "total_results": 0,
            "errors": [],
            "search_time": 0.0
        }

        if not sources:
            results["search_time"] = round(time.time() - start, 3)
            return results

        with ThreadPoolExecutor(max_workers=min(len(sources), 4)) as executor:
            futures = []

            for src in sources:
                futures.append(
                    executor.submit(self._search_single_source, query, src)
                )

            for src, future in zip(sources, futures):
                try:
                    data = future.result(timeout=20)
                    if data:
                        results["raw_results"][src] = data[:max_results]
                        results["total_results"] += len(data)
                except Exception as e:
                    logger.error(f"Error en fuente {src}: {e}")
                    results["errors"].append(f"{src}: {str(e)}")

        results["search_time"] = round(time.time() - start, 3)
        return results

    # --------------------------------------------------------
    # BÚSQUEDA POR FUENTE (PASIVA)
    # --------------------------------------------------------
    def _search_single_source(self, query: str, source: str) -> List[Dict[str, Any]]:
        if source == "web_search":
            return self._search_web(query, "web")

        if source == "google_search":
            return self._search_web(query, "google")

        if source == "bing_search":
            return self._search_web(query, "bing")

        if source == "duckduckgo_search":
            return self._search_web(query, "duckduckgo")

        return []

    # --------------------------------------------------------
    # SIMULACIÓN CONTROLADA DE BÚSQUEDA WEB
    # --------------------------------------------------------
    def _search_web(self, query: str, engine: str) -> List[Dict[str, Any]]:
        url_map = {
            "web": f"https://www.google.com/search?q={quote_plus(query)}",
            "google": f"https://www.google.com/search?q={quote_plus(query)}",
            "bing": f"https://www.bing.com/search?q={quote_plus(query)}",
            "duckduckgo": f"https://duckduckgo.com/?q={quote_plus(query)}"
        }

        return [{
            "title": f"Resultado público ({engine})",
            "url": url_map.get(engine),
            "snippet": f"Menciones públicas relacionadas con '{query}'",
            "confidence": 0.65,
            "source": engine,
            "timestamp": time.time()
        }]


# ============================================================
# API PÚBLICA DEL MÓDULO
# ============================================================

general_searcher = GeneralSearcher()


def search_general_real(
    query: str,
    user_id: int,
    sources: List[str] = None,
    mode: str = "passive",
    max_results: int = 10
) -> Dict[str, Any]:
    return general_searcher.search_general_real(
        query=query,
        user_id=user_id,
        sources=sources,
        mode=mode,
        max_results=max_results
    )


def get_available_sources(user_id: int) -> List[str]:
    return list(general_searcher.get_user_sources(user_id).keys())
