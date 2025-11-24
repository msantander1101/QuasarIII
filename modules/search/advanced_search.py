# modules/search/advanced_search.py
import logging
import requests
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import streamlit as st

from core.config_manager import config_manager

logger = logging.getLogger(__name__)

# Importar los módulos reales
from . import people_search, emailint
# Importar módulo de Google Dorks para integrar búsquedas avanzadas
from . import google_dorks


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
    """
    Sistema avanzado de búsqueda multifunción con múltiples fuentes reales
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'QuasarIII-OSINT/1.0',
            'Accept': 'application/json'
        })
        self.max_workers = 4  # Máximo de hilos concurrentes

    def search_multiple_sources(self, query: str, sources: List[str] = None) -> Dict[str, Any]:
        """
        Búsqueda múltiple en fuentes especificadas con datos reales
        """
        if sources is None:
            # Incluir 'dorks' como fuente opcional.  Se omite por defecto para
            # no sobrecargar búsquedas, pero se puede pasar explícitamente.
            sources = ['people', 'email', 'social', 'web']

        start_time = time.time()
        results = {}

        try:
            # Ejecutar búsqueda en paralelo
            with ThreadPoolExecutor(max_workers=min(len(sources), self.max_workers)) as executor:
                # Crear tareas para cada fuente
                futures = {}
                for source in sources:
                    if source == 'people':
                        futures[executor.submit(self._search_people, query)] = source
                    elif source == 'email':
                        futures[executor.submit(self._search_email, query)] = source
                    elif source == 'social':
                        futures[executor.submit(self._search_social, query)] = source
                    elif source == 'web':
                        futures[executor.submit(self._search_web, query)] = source
                    elif source == 'domain':
                        futures[executor.submit(self._search_domain, query)] = source
                    elif source == 'dorks':
                        # Integrar búsqueda de Google Dorks
                        futures[executor.submit(self._search_dorks, query)] = source
                    else:
                        futures[executor.submit(self._search_generic, source, query)] = source

                # Recopilar resultados
                for future in as_completed(futures.keys()):
                    source = futures[future]
                    try:
                        result = future.result(timeout=30)
                        if result:
                            results[source] = result
                    except Exception as e:
                        logger.error(f"Error en búsqueda en {source}: {e}")
                        results[source] = {"error": str(e)}

            logger.info(f"Búsqueda múltiple completada en {time.time() - start_time:.2f}s")
            return results

        except Exception as e:
            logger.error(f"Error en búsqueda múltiple: {e}")
            return {"error": f"Error de búsqueda: {str(e)}"}

    def search_with_filtering(self, criteria: Dict[str, Any],
                              sources: List[str] = None,
                              filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Búsqueda avanzada con filtros y criterios complejos usando datos reales
        """
        start_time = time.time()

        # Preparar búsquedas basadas en criterios
        queries = []
        if criteria.get('name'):
            queries.append({'type': 'person', 'value': criteria['name']})
        if criteria.get('email'):
            queries.append({'type': 'email', 'value': criteria['email']})
        if criteria.get('phone'):
            queries.append({'type': 'phone', 'value': criteria['phone']})
        if criteria.get('location'):
            queries.append({'type': 'location', 'value': criteria['location']})

        # Ejecutar búsqueda
        results = self.search_multiple_sources(
            criteria.get('query') or ' '.join([str(v) for v in criteria.values()]),
            sources or ['people', 'email', 'social']
        )

        # Aplicar filtros si se especifican
        if filters:
            results = self._apply_filters(results, filters)

        logger.info(f"Búsqueda con filtros completada en {time.time() - start_time:.2f}s")
        return results

    def _search_people(self, query: str) -> Dict[str, Any]:
        """Búsqueda avanzada de personas real"""
        try:
            # Aquí conectamos con APIs reales
            results = people_search.search_people_by_name(query)
            return {
                "source": "people",
                "query": query,
                "results": results,
                "metadata": {
                    "total_results": len(results),
                    "search_time": time.time()
                }
            }
        except Exception as e:
            return {"error": f"Búsqueda personas: {str(e)}"}

    def _search_email(self, query: str) -> Dict[str, Any]:
        """
        Búsqueda de información de email y adaptación a la estructura que espera la interfaz.

        Este método llama al módulo ``emailint`` para obtener información sobre
        brechas de seguridad y otros datos de un correo electrónico. Luego
        transforma el resultado en una lista de entradas resumidas para que
        puedan mostrarse correctamente en la UI. Si no hay información o el
        correo tiene formato incorrecto, se devuelve una lista con un único
        elemento que incluye el mensaje de error o la advertencia.
        """
        try:
            # Obtener la clave de HIBP configurada (si la hay)
            try:
                user_id = st.session_state.get('current_user_id')
                hibp_key = config_manager.get_config(user_id, "hibp")
                if not hibp_key:
                    hibp_key = None
            except Exception:
                hibp_key = None

            # Realizar la búsqueda de email. ``email_data`` es un dict con
            # información sobre brechas (breeches_info), pastes, y verificación.
            email_data = emailint.search_email_info(query, hibp_key)

            results_list: List[Dict[str, Any]] = []

            # Manejar errores globales (como formato inválido)
            if isinstance(email_data, dict) and email_data.get("error"):
                results_list.append({
                    "email": query,
                    "breached": False,
                    "breach_count": 0,
                    "sources": "N/A",
                    "error": email_data.get("error")
                })
            else:
                # Extraer información de brechas.  Nota: en ``emailint`` la
                # clave se denomina ``breeches_info`` (con doble 'e').  Pero
                # añadimos también ``breaches_info`` por compatibilidad.
                breach_info = {}
                if isinstance(email_data, dict):
                    breach_info = email_data.get('breeches_info') or email_data.get('breaches_info') or {}

                breached = False
                breach_count = 0
                sources = []

                if isinstance(breach_info, dict):
                    if breach_info.get('error'):
                        sources.append(f"Error: {breach_info.get('error')}")
                    else:
                        breached = breach_info.get('breached', False)
                        breach_count = breach_info.get('breach_count', 0)
                        src = breach_info.get('source')
                        if src:
                            sources.append(src)

                results_list.append({
                    "email": query,
                    "breached": breached,
                    "breach_count": breach_count,
                    "sources": sources if sources else "API",
                })

            return {
                "source": "email",
                "query": query,
                "results": results_list,
                "metadata": {
                    "search_time": time.time()
                }
            }

        except Exception as e:
            return {"error": f"Búsqueda email: {str(e)}"}

    def _search_social(self, query: str) -> Dict[str, Any]:
        """Búsqueda de redes sociales real"""
        try:
            # Conectar con el módulo SOCMINT para obtener perfiles sociales reales o simulados
            from . import socmint
            # Utilizar el nombre de usuario tal cual o derivar uno del query
            username = query.strip()
            # Ejecutar la búsqueda de perfiles sociales
            social_data = socmint.search_social_profiles(username)
            profiles = social_data.get('profiles_found', [])
            total_profiles = social_data.get('total_profiles', len(profiles))
            return {
                "source": "social",
                "query": query,
                "results": profiles,
                "metadata": {
                    "total_results": total_profiles,
                    "search_time": time.time()
                }
            }
        except Exception as e:
            return {"error": f"Búsqueda social: {str(e)}"}

    def _search_web(self, query: str) -> Dict[str, Any]:
        """
        Búsqueda web utilizando la API pública de DuckDuckGo.

        Este método consulta DuckDuckGo para obtener resultados relacionados con la
        búsqueda.  Si la llamada falla o no hay resultados, devuelve un único
        resultado simulando un enlace genérico.  Se limita el número de
        resultados a tres para mantener la interfaz limpia.
        """
        try:
            results: List[Dict[str, Any]] = []
            import urllib.parse
            # Construir URL de consulta. La API de DuckDuckGo no requiere clave.
            api_url = (
                f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(query)}"
                "&format=json&no_redirect=1&skip_disambig=1"
            )
            response = self.session.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # DuckDuckGo devuelve RelatedTopics con enlaces y textos
                def extract_topics(topics):
                    for item in topics:
                        # Si hay subtemas, procesarlos recursivamente
                        if isinstance(item, dict) and 'Topics' in item:
                            extract_topics(item['Topics'])
                        else:
                            if isinstance(item, dict) and 'FirstURL' in item and 'Text' in item:
                                results.append({
                                    "title": item.get('Text', 'Sin título'),
                                    "url": item.get('FirstURL', '#'),
                                    "snippet": item.get('Text', ''),
                                    "source": "DuckDuckGo",
                                    "confidence": 0.8,
                                    "timestamp": time.time()
                                })
                if 'RelatedTopics' in data:
                    extract_topics(data['RelatedTopics'])
            # Limitar a 3 primeros resultados
            if results:
                results = results[:3]
            else:
                # Resultado predeterminado si no hay nada
                results = [{
                    "title": f"Búsqueda para '{query}'",
                    "url": f"https://duckduckgo.com/?q={urllib.parse.quote_plus(query)}",
                    "snippet": "No se encontraron resultados detallados.",
                    "source": "DuckDuckGo",
                    "confidence": 0.5,
                    "timestamp": time.time()
                }]
            return {
                "source": "web",
                "query": query,
                "results": results,
                "metadata": {
                    "total_results": len(results),
                    "search_time": time.time()
                }
            }
        except Exception as e:
            return {"error": f"Búsqueda web: {str(e)}"}

    def _search_domain(self, query: str) -> Dict[str, Any]:
        """Busqueda de historicos"""
        try:
            domain_results = []
            from . import archive_search
            history_results = archive_search.search_domain_history(query, 5)
            if '.' in query and not '/' in query:
                wayback_results = archive_search.search_wayback_machine(query, 2000, 2024)
            else:
                wayback_results = []
            domain_results = {
                "domain": query,
                "history": history_results,
                "wayback_snapshots": wayback_results,
                "metadata": {
                    "search_time": time.time(),
                    "total_snapshots": len(wayback_results) if wayback_results else 0,
                    "total_history_entries": len(history_results) if history_results else 0
                }
            }
            return {
                "source": "domain",
                "query": query,
                "results": domain_results,
                "metadata": {
                    "search_time": time.time()
                }
            }
        except Exception as e:
            return {"error": f"Búsqueda dominio: {str(e)}"}

    def _search_dorks(self, query: str) -> Dict[str, Any]:
        """Búsqueda de Google Dorks para el término dado.

        Este método usa el módulo ``google_dorks`` para generar consultas dorks
        combinando patrones avanzados de búsqueda con la consulta del usuario.
        Devuelve un diccionario con la estructura estándar esperada por la UI.

        Args:
            query: El término a investigar.

        Returns:
            Diccionario con los resultados encontrados o un mensaje de error.
        """
        try:
            dork_results = google_dorks.search_google_dorks(query)
            return {
                "source": "dorks",
                "query": query,
                "results": dork_results,
                "metadata": {
                    "total_results": len(dork_results),
                    "search_time": time.time()
                }
            }
        except Exception as e:
            return {"error": f"Búsqueda dorks: {str(e)}"}


    def _search_generic(self, source: str, query: str) -> Dict[str, Any]:
        """Búsqueda genérica"""
        try:
            from . import archive_search
            if source in ["archive", "wayback", "web_archives"]:
                if source == "archive":
                    return {"source": source, "query": query, "results": archive_search.search_archive_org(query)}
                elif source == "wayback":
                    return {"source": source, "query": query, "results": archive_search.search_wayback_machine(query)}
                else:
                    return {"source": source, "query": query, "results": []}
            else:
                return {
                    "source": source,
                    "query": query,
                    "results": [],
                    "metadata": {
                        "search_time": time.time()
                    }
                }
        except Exception as e:
            return {"error": f"Búsqueda genérica {source}: {str(e)}"}


    def _apply_filters(self, results: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Aplicar filtros avanzados a resultados"""
        if not filters:
            return results

        filtered_results = {}
        for source, data in results.items():
            if isinstance(data, dict) and 'results' in data:
                filtered_results[source] = data

                # Aplicar filtros específicos
                filtered_data = data['results']
                if filters.get('min_confidence'):
                    filtered_data = [r for r in filtered_data if r.get('confidence', 0) >= filters['min_confidence']]
                if filters.get('location_filter'):
                    filtered_data = [r for r in filtered_data if
                                     filters['location_filter'] in str(r.get('location', ''))]

                filtered_results[source]['results'] = filtered_data
                filtered_results[source]['metadata']['filtered_results'] = len(filtered_data)
            else:
                filtered_results[source] = data

        return filtered_results


# Instancia global
advanced_searcher = AdvancedSearcher()


# Funciones públicas
def search_multiple_sources(query: str, sources: List[str] = None) -> Dict[str, Any]:
    """Función pública para búsqueda múltiple"""
    return advanced_searcher.search_multiple_sources(query, sources)


def search_with_filtering(criteria: Dict[str, Any],
                          sources: List[str] = None,
                          filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Búsqueda avanzada con filtros"""
    return advanced_searcher.search_with_filtering(criteria, sources, filters)


def search_advanced(query: str, **kwargs) -> Dict[str, Any]:
    """Búsqueda avanzada completa con múltiples parámetros"""
    sources = kwargs.get('sources', ['people', 'email', 'social'])
    filters = kwargs.get('filters')

    return advanced_searcher.search_multiple_sources(query, sources)