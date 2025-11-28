# modules/search/advanced_search.py
import logging
import requests
import time
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import streamlit as st

from core.config_manager import config_manager

logger = logging.getLogger(__name__)

# Importar los módulos reales
from . import people_search, emailint, socmint, google_dorks, archive_search


@dataclass
class SearchResult:
    """Clase para estructurar resultados de búsqueda"""
    source: str
    query: str
    data: Dict[str, Any]
    confidence: float
    timestamp: float
    metadata: Dict[str, Any] = None


class AdvancedSearcher:
    """Sistema avanzado de búsqueda multifunción con múltiples fuentes reales"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'QuasarIII-OSINT/1.0',
            'Accept': 'application/json'
        })
        self.max_workers = 4  # Máximo de hilos concurrentes

    def search_multiple_sources(self, query: str, sources: List[str] = None, username: str = None) -> Dict[str, Any]:
        """
        Búsqueda múltiple en fuentes especificadas.
        `username` es opcional y se usa únicamente para SOCMINT (si está proporcionado).
        """
        if sources is None:
            sources = ['people', 'email', 'social', 'web', 'domain', 'dorks']

        start_time = time.time()
        results = {}

        try:
            max_workers = min(len(sources), 4)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for source in sources:
                    if source == 'people':
                        futures[executor.submit(self._search_people_with_social, query)] = source
                    elif source == 'email':
                        futures[executor.submit(self._search_email, query)] = source
                    elif source == 'social':
                        # Ejecutar búsqueda social: si hay username explícito, pásalo, si no, intentamos usar query como username (solo si parece username)
                        futures[executor.submit(self._search_social, query, username)] = source
                    elif source == 'web':
                        futures[executor.submit(self._search_web, query)] = source
                    elif source == 'domain':
                        futures[executor.submit(self._search_domain, query)] = source
                    elif source == 'dorks':
                        futures[executor.submit(self._search_dorks, query)] = source
                    else:
                        futures[executor.submit(self._search_generic, source, query)] = source

                for future in as_completed(futures.keys()):
                    source = futures[future]
                    try:
                        result = future.result(timeout=60)
                        if result:
                            results[source] = result
                    except Exception as e:
                        logger.error(f"Error en búsqueda en {source}: {e}")
                        results[source] = {"error": str(e)}

            logger.info(f"Búsqueda múltiple completada en {time.time() - start_time:.2f}s")
            # Añadimos metadata global
            results["_metadata"] = {"total_sources": len(results), "search_time": time.time() - start_time}
            return results

        except Exception as e:
            logger.error(f"Error en búsqueda múltiple: {e}")
            return {"error": f"Error de búsqueda: {str(e)}"}

    def search_with_filtering(self, criteria: Dict[str, Any],
                              sources: List[str] = None,
                              filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Búsqueda avanzada con filtros"""
        start_time = time.time()
        query = criteria.get('query') or ' '.join([str(v) for v in criteria.values()])
        username = criteria.get('username') if isinstance(criteria, dict) else None

        results = self.search_multiple_sources(query, sources or ['people', 'email', 'social'], username=username)

        if filters:
            results = self._apply_filters(results, filters)

        logger.info(f"Búsqueda con filtros completada en {time.time() - start_time:.2f}s")
        return results

    # ------------------ Búsquedas por fuente ------------------
    def _search_people(self, query: str) -> Dict[str, Any]:
        try:
            results = people_search.search_people_by_name(query)
            total = len(results) if isinstance(results, list) else (0 if results is None else 1)
            return {"source": "people", "query": query, "results": results,
                    "metadata": {"total_results": total, "search_time": time.time()}}
        except Exception as e:
            return {"source": "people", "query": query, "error": f"Búsqueda personas: {e}"}

    def _search_people_with_social(self, query: str) -> Dict[str, Any]:
        """
        Búsqueda de personas + SOCMINT únicamente si hay username dentro de cada persona.
        No sobrescribe la lista de personas.
        """
        try:
            people_results = self._search_people(query)

            if "results" in people_results and isinstance(people_results["results"], list):
                new_list = []
                for person in people_results["results"]:
                    if not isinstance(person, dict):
                        new_list.append(person)
                        continue

                    person_copy = person.copy()

                    # Preferimos username explícito de la persona; si no, intentar extraer del email
                    username = None
                    if person_copy.get("username") and isinstance(person_copy.get("username"), str):
                        username = person_copy.get("username").strip()
                    elif person_copy.get("email") and isinstance(person_copy.get("email"), str) and "@" in person_copy.get("email"):
                        username = person_copy.get("email").split("@")[0].strip()

                    if username and len(username) > 1:
                        try:
                            social_result = socmint.search_social_profiles(username=username, platforms=["maigret", "sherlock"])
                            # Guardar social_profiles dentro de la persona — no sustituir people.results
                            person_copy["social_profiles"] = social_result.get("social_profiles", {})
                        except Exception as e:
                            logger.warning(f"Error SOCMINT para {username}: {e}")
                            person_copy["social_profiles"] = {"error": str(e)}

                    new_list.append(person_copy)

                people_results["results"] = new_list

            return people_results

        except Exception as e:
            logger.error(f"Error en búsqueda avanzada de personas con sociales: {e}")
            return {"source": "people_social", "query": query, "error": f"Búsqueda personas con sociales: {str(e)}"}

    def _search_email(self, query: str) -> Dict[str, Any]:
        try:
            user_id = st.session_state.get('current_user_id')
            if not isinstance(query, str) or not query or '@' not in query:
                return {"source": "email", "query": query, "results": []}

            if query and isinstance(query, str) and '@' in query and '.' in query.split('@')[1]:
                if not emailint.verify_email_format(query):
                    return {"source": "email", "query": query, "error": "Formato de email inválido"}
            else:
                return {"source": "email", "query": query, "results": []}

            return emailint.search_email_info(email=query, user_id=user_id)

        except Exception as e:
            return {"source": "email", "query": query, "error": f"Búsqueda email: {str(e)}"}

    def _search_social(self, query: str, username_override: str = None) -> Dict[str, Any]:
        """
        Búsqueda de perfiles sociales: usa username_override si está disponible,
        si no y query parece username (no contiene @) lo usa.
        """
        try:
            username_to_use = None
            if username_override and isinstance(username_override, str) and len(username_override.strip()) > 1:
                username_to_use = username_override.strip()
            else:
                # si query es un email no lo usamos; si es username (no contiene '@') lo usamos
                if isinstance(query, str) and "@" not in query and len(query.strip()) > 1:
                    username_to_use = query.strip()

            if not username_to_use:
                return {"source": "social", "query": query, "results": [], "metadata": {"total_results": 0}}

            social_data = socmint.search_social_profiles(username=username_to_use)
            profiles = social_data.get('social_profiles', {})
            # Normalizar: devolver estructura útil para UI
            return {"source": "social", "query": username_to_use, "results": profiles, "metadata": {"total_results": len(profiles) if isinstance(profiles, dict) else 1}}

        except Exception as e:
            return {"source": "social", "query": query, "error": f"Búsqueda social: {str(e)}"}

    def _search_web(self, query: str) -> Dict[str, Any]:
        try:
            import urllib.parse
            results: List[Dict[str, Any]] = []
            api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(query)}&format=json&no_redirect=1&skip_disambig=1"
            response = self.session.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()

                def extract_topics(topics):
                    for item in topics:
                        if isinstance(item, dict) and 'Topics' in item:
                            extract_topics(item['Topics'])
                        elif isinstance(item, dict) and 'FirstURL' in item and 'Text' in item:
                            results.append({"title": item['Text'], "url": item['FirstURL'],
                                            "snippet": item['Text'], "source": "DuckDuckGo",
                                            "confidence": 0.8, "timestamp": time.time()})

                if 'RelatedTopics' in data:
                    extract_topics(data['RelatedTopics'])

            if not results:
                results = [{"title": f"Búsqueda para '{query}'",
                            "url": f"https://duckduckgo.com/?q={urllib.parse.quote_plus(query)}",
                            "snippet": "No se encontraron resultados detallados.",
                            "source": "DuckDuckGo",
                            "confidence": 0.5,
                            "timestamp": time.time()}]

            return {"source": "web", "query": query, "results": results,
                    "metadata": {"total_results": len(results), "search_time": time.time()}}

        except Exception as e:
            return {"source": "web", "query": query, "error": f"Búsqueda web: {e}"}

    def _search_domain(self, query: str) -> Dict[str, Any]:
        try:
            history_results = archive_search.search_domain_history(query, 5)
            wayback_results = archive_search.search_wayback_machine(query, 2000, 2024) if '.' in query else []
            return {"source": "domain", "query": query,
                    "results": {"history": history_results, "wayback_snapshots": wayback_results},
                    "metadata": {"search_time": time.time()}}
        except Exception as e:
            return {"source": "domain", "query": query, "error": f"Búsqueda dominio: {e}"}

    def _search_dorks(self, query: str) -> Dict[str, Any]:
        try:
            serpapi_key = config_manager.get_config(st.session_state.get('current_user_id'), 'serpapi') or None
            google_api_key = config_manager.get_config(st.session_state.get('current_user_id'),
                                                       'google_api_key') or None
            google_cx = config_manager.get_config(st.session_state.get('current_user_id'),
                                                  'google_custom_search_cx') or None

            import os
            serpapi_key = serpapi_key or os.getenv('SERPAPI_API_KEY')
            google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
            google_cx = google_cx or os.getenv('GOOGLE_CUSTOM_SEARCH_CX')

            dork_results = google_dorks.search_google_dorks(query, serpapi_key=serpapi_key,
                                                            google_api_key=google_api_key, google_cx=google_cx)
            return {"source": "dorks", "query": query, "results": dork_results,
                    "metadata": {"total_results": len(dork_results), "search_time": time.time()}}
        except Exception as e:
            return {"source": "dorks", "query": query, "error": f"Búsqueda dorks: {e}"}

    def _search_generic(self, source: str, query: str) -> Dict[str, Any]:
        return {"source": source, "query": query, "results": [], "metadata": {"search_time": time.time()}}

    def _apply_filters(self, results: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        if not filters:
            return results
        filtered_results = {}
        for source, data in results.items():
            if isinstance(data, dict) and 'results' in data:
                filtered_data = data['results']
                if filters.get('min_confidence'):
                    filtered_data = [r for r in filtered_data if r.get('confidence', 0) >= filters['min_confidence']]
                if filters.get('location_filter'):
                    filtered_data = [r for r in filtered_data if
                                     filters['location_filter'] in str(r.get('location', ''))]
                filtered_results[source] = data
                filtered_results[source]['results'] = filtered_data
                if 'metadata' not in filtered_results[source]:
                    filtered_results[source]['metadata'] = {}
                filtered_results[source]['metadata']['filtered_results'] = len(filtered_data)
            else:
                filtered_results[source] = data
        return filtered_results


# ------------------ Instancia global y funciones públicas ------------------
advanced_searcher = AdvancedSearcher()


def search_multiple_sources(query: str, sources: List[str] = None, username: str = None) -> Dict[str, Any]:
    return advanced_searcher.search_multiple_sources(query, sources, username=username)


def search_with_filtering(criteria: Dict[str, Any], sources: List[str] = None,
                          filters: Dict[str, Any] = None) -> Dict[str, Any]:
    return advanced_searcher.search_with_filtering(criteria, sources, filters)
