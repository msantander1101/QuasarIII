# modules/search/central_search.py

"""
Módulo central optimizado para coordinar búsquedas OSINT en diferentes tipos de fuentes
con integración real y ejecución paralela opcional.
"""

import logging
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import (
    general_search,
    people_search,
    emailint,
    socmint,
    darkweb,
    archive_search,
    google_dorks
)

logger = logging.getLogger(__name__)


class SearchCoordinator:
    """
    Coordinador de búsqueda central que integra todos los módulos OSINT reales
    """

    def __init__(self, max_workers: int = 5):
        self.providers = {
            'general': general_search,
            'people': people_search,
            'email': emailint,
            'social': socmint,
            'darkweb': darkweb,
            'archive': archive_search,
            'dorks': google_dorks
        }
        self.max_workers = max_workers

    def _run_source(self, source_name: str, query: str, user_id: Optional[int], options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la búsqueda para un módulo fuente específico
        """
        if source_name not in self.providers:
            return {"success": False, "error": f"Fuente inexistente: {source_name}", "source": source_name}

        provider = self.providers[source_name]

        try:
            search_func = None
            if hasattr(provider, 'search_' + source_name):
                search_func = getattr(provider, 'search_' + source_name)
            elif hasattr(provider, source_name + '_search'):
                search_func = getattr(provider, source_name + '_search')
            elif hasattr(provider, 'search'):
                search_func = getattr(provider, 'search')

            if not search_func or not callable(search_func):
                return {"success": False, "error": "Función de búsqueda no encontrada", "source": source_name}

            # Ajustes especiales por módulo
            if source_name == 'email':
                # Pasamos user_id y api_keys opcionalmente
                return search_func(query, user_id=user_id, **options)
            elif source_name == 'people':
                return search_func(query, **options)
            elif source_name in ['general', 'darkweb', 'archive', 'social', 'dorks']:
                return search_func(query, **options)
            else:
                return search_func(query, **options)

        except Exception as e:
            logger.error(f"Error en módulo {source_name}: {e}")
            return {"success": False, "error": str(e), "source": source_name}

    def search(self, query: str, sources: List[str] = None, user_id: int = None, **kwargs) -> Dict[str, Any]:
        """
        Realiza una búsqueda general usando las fuentes especificadas
        """
        logger.info(f"Realizando búsqueda centralizada con consulta: '{query}', fuentes: {sources or 'todas'}")

        results = {}
        selected_sources = sources or list(self.providers.keys())

        for source_name in selected_sources:
            if source_name in self.providers:
                try:
                    provider = self.providers[source_name]

                    # Manejo por fuente
                    if source_name == 'general':
                        search_kwargs = kwargs.get('general_options', {})
                        result = provider.general_web_search(query, max_results=search_kwargs.get('max_results', 10))
                        results[source_name] = result

                    elif source_name == 'people':
                        search_kwargs = kwargs.get('people_options', {})
                        search_type = search_kwargs.get('type', 'people')
                        criteria = {'name': query}
                        if search_kwargs.get('location'):
                            criteria['location'] = search_kwargs['location']
                        result = provider.advanced_search(criteria, search_type)
                        results[source_name] = result

                    elif source_name == 'email':
                        search_kwargs = kwargs.get('email_options', {})
                        # GHunt agregado automáticamente como servicio
                        services = search_kwargs.get('services', ['hibp', 'skymem', 'ghunt'])
                        result = provider.search_email_info(query, user_id=user_id, services=services)
                        results[source_name] = result

                    elif source_name == 'social':
                        search_kwargs = kwargs.get('social_options', {})
                        usernames = search_kwargs.get('usernames', [query])
                        platforms = search_kwargs.get('platforms', ['twitter', 'linkedin'])
                        api_configs = search_kwargs.get('api_configs', {})
                        if usernames and platforms:
                            social_results = provider.search_multiple_social_profiles(usernames, platforms, api_configs)
                            results[source_name] = social_results
                        else:
                            results[source_name] = {
                                "warning": "Necesita usernames y plataformas para búsqueda social"
                            }

                    elif source_name == 'darkweb':
                        darkweb_options = kwargs.get('darkweb_options', {})
                        result = provider.search_dark_web_catalog(query,
                                                                  max_results=darkweb_options.get('max_results', 5))
                        results[source_name] = result

                    elif source_name == 'archive':
                        archive_options = kwargs.get('archive_options', {})
                        result = provider.search_web_archives(query,
                                                              archive_options.get('sources', ['wayback', 'archive']))
                        results[source_name] = result

                    elif source_name == 'dorks':
                        dorks_options = kwargs.get('dorks_options', {})
                        patterns = dorks_options.get('patterns')
                        try:
                            result = provider.search_google_dorks(query, patterns)
                        except AttributeError:
                            if hasattr(provider, 'search_dorks'):
                                result = provider.search_dorks(query, patterns)
                            else:
                                result = provider.search(query, patterns=patterns)
                        results[source_name] = result

                    else:
                        results[source_name] = {"warning": f"Fuente no soportada: {source_name}"}

                except Exception as e:
                    logger.error(f"Error al ejecutar búsqueda en fuente {source_name}: {e}")
                    results[source_name] = {"error": str(e)}
            else:
                results[source_name] = {"error": f"Fuente inexistente: {source_name}"}

        return results


# Instancia global
coordinator = SearchCoordinator()


def execute_search(
    query: str,
    sources: List[str] = None,
    user_id: Optional[int] = None,
    parallel: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Función directa para ejecutar búsqueda centralizada de manera estandarizada
    """
    return coordinator.search(query, sources=sources, user_id=user_id, parallel=parallel, **kwargs)
