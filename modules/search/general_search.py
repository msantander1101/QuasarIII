# modules/search/general_search.py
"""
General Search — OSINT Pasivo y Controlado
✔ No ejecuta fuentes sensibles automáticamente
✔ Diseñado como radar contextual (web, menciones, superficie)
✔ Compatible con arquitectura Quasar III
✔ Delegación de dorks avanzados al módulo google_dorks
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from urllib.parse import quote_plus

import requests

from core.config_manager import config_manager

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN GLOBAL
# ============================================================

PASSIVE_SOURCES = {
    "web_search",
    "google_search",
    "bing_search",
    "duckduckgo_search",
}

ACTIVE_OPTIONAL_SOURCES = {
    "serpapi",
    "openai",
    "predictasearch",
}

FORBIDDEN_SOURCES = {
    "hibp",
    "hunter",
    "shodan",
    "virustotal",
    "whoisxml",
}


@dataclass(frozen=True)
class SourceProfile:
    """Describe una fuente de búsqueda disponible."""

    name: str
    mode: str  # "passive" o "active"
    engine: str
    requires_api: bool = False
    api_key_name: str = ""


class GeneralSearcher:
    """
    Buscador OSINT general PASIVO.
    No realiza enriquecimiento sensible ni correlación.
    Se centra en un radar de superficie y delega dorks avanzados
    al módulo especializado de google_dorks.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "QuasarIII-GeneralSearch/1.0"
        })
        self.timeout = 20
        self.max_workers = 4

        self.source_catalog: Dict[str, SourceProfile] = {
            "web_search": SourceProfile("web_search", "passive", "web"),
            "google_search": SourceProfile("google_search", "passive", "google"),
            "bing_search": SourceProfile("bing_search", "passive", "bing"),
            "duckduckgo_search": SourceProfile("duckduckgo_search", "passive", "duckduckgo"),
            # Activos (placeholder si se habilitan en futuro)
            "serpapi": SourceProfile("serpapi", "active", "google", True, "serpapi_api_key"),
            "openai": SourceProfile("openai", "active", "openai", True, "openai_api_key"),
            "predictasearch": SourceProfile("predictasearch", "active", "predictasearch", True, "predictasearch_api_key"),
        }

    # --------------------------------------------------------
    # FUENTES DISPONIBLES (solo informativo)
    # --------------------------------------------------------
    def get_user_sources(self, user_id: int) -> Dict[str, Dict]:
        """Devuelve catálogo de fuentes y si el usuario tiene claves listas."""

        sources: Dict[str, Dict[str, Any]] = {}
        for name, profile in self.source_catalog.items():
            if profile.name in FORBIDDEN_SOURCES:
                continue

            info: Dict[str, Any] = {
                "enabled": profile.mode == "passive",
                "requires_api": profile.requires_api,
            }

            if profile.requires_api and profile.api_key_name:
                api_key = config_manager.get_config(user_id, profile.api_key_name)
                info["has_api_key"] = bool(api_key)
                info["enabled"] = bool(api_key)

            sources[name] = info

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
        clean_query = (query or "").strip()
        logger.info("[GeneralSearch] query='%s' mode=%s", clean_query, mode)

        if not clean_query:
            return {
                "query": clean_query,
                "intent": "contextual_search",
                "mode": mode,
                "sources_used": [],
                "raw_results": {},
                "total_results": 0,
                "errors": ["query_empty"],
                "skipped_sources": [],
                "search_time": round(time.time() - start, 3),
            }

        selected_sources, skipped = self._resolve_sources(clean_query, sources, mode, user_id)

        results: Dict[str, Any] = {
            "query": clean_query,
            "intent": "contextual_search",
            "mode": mode,
            "sources_used": selected_sources,
            "skipped_sources": skipped,
            "raw_results": {},
            "total_results": 0,
            "errors": [],
            "search_time": 0.0,
        }

        if not selected_sources:
            results["search_time"] = round(time.time() - start, 3)
            return results

        with ThreadPoolExecutor(max_workers=min(len(selected_sources), self.max_workers)) as executor:
            futures = [
                executor.submit(self._search_single_source, clean_query, src)
                for src in selected_sources
            ]

            for src, future in zip(selected_sources, futures):
                try:
                    data = future.result(timeout=self.timeout)
                    if data:
                        # Guardamos solo hasta max_results por fuente
                        sliced = data[:max_results]
                        results["raw_results"][src] = sliced
                        results["total_results"] += len(sliced)
                except Exception as e:
                    logger.error("Error en fuente %s: %s", src, e)
                    results["errors"].append(f"{src}: {str(e)}")

        results["search_time"] = round(time.time() - start, 3)
        return results

    def _resolve_sources(
        self,
        query: str,
        sources: List[str] | None,
        mode: str,
        user_id: int,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Filtra y normaliza fuentes solicitadas devolviendo seleccionadas y omitidas.
        """

        requested = sources or list(PASSIVE_SOURCES)
        normalized: List[str] = []
        skipped: List[Dict[str, Any]] = []

        for src in requested:
            name = (src or "").strip().lower()
            if not name or name in normalized:
                continue

            if name in FORBIDDEN_SOURCES:
                skipped.append({"source": name, "reason": "forbidden"})
                continue

            profile = self.source_catalog.get(name)
            if not profile:
                skipped.append({"source": name, "reason": "unknown_source"})
                continue

            if mode == "passive" and profile.mode != "passive":
                skipped.append({"source": name, "reason": "restricted_by_mode"})
                continue

            if profile.requires_api:
                api_key = config_manager.get_config(user_id, profile.api_key_name)
                if not api_key:
                    skipped.append({"source": name, "reason": "missing_api_key"})
                    continue

                # Placeholder: la fuente está definida pero aún no implementada
                skipped.append({"source": name, "reason": "not_implemented"})
                continue

            normalized.append(name)

        return normalized, skipped

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
    # (sin solaparse con las búsquedas de google_dorks)
    # --------------------------------------------------------
    def _search_web(self, query: str, engine: str) -> List[Dict[str, Any]]:
        """
        Genera únicamente una búsqueda general por motor.
        Cualquier dork avanzado (comillas, modificadores, etc.) se delega
        al módulo google_dorks para evitar solapamiento.
        """
        url_map = {
            "web": f"https://www.google.com/search?q={quote_plus(query)}",
            "google": f"https://www.google.com/search?q={quote_plus(query)}",
            "bing": f"https://www.bing.com/search?q={quote_plus(query)}",
            "duckduckgo": f"https://duckduckgo.com/?q={quote_plus(query)}",
        }

        base_url = url_map.get(engine)
        timestamp = time.time()
        context = query[:180]

        if not base_url:
            return []

        # 🔹 SOLO UN RESULTADO POR MOTOR, genérico
        return [
            {
                "title": f"Panorama general ({engine})",
                "url": base_url,
                "snippet": (
                    f"Vista inicial de resultados públicos sobre '{context}'. "
                    "Para dorks y consultas especializadas se utiliza el módulo "
                    "de búsqueda avanzada (google_dorks)."
                ),
                "confidence": 0.65,
                "source": engine,
                "timestamp": timestamp,
            }
        ]


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
