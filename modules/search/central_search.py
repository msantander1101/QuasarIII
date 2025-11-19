# modules/search/central_search.py
"""
Módulo central para coordinar búsquedas en diferentes tipos con integración real
"""

import logging
from typing import Dict, List, Any
from . import (
    general_search,
    people_search,
    emailint,
    socmint
)

logger = logging.getLogger(__name__)


class SearchCoordinator:
    """
    Coordinador de búsqueda central que integra todos los módulos reales
    """

    def __init__(self):
        self.providers = {
            'general': general_search,
            'people': people_search,
            'email': emailint,
            'social': socmint
        }

    def search(self, query: str, sources: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Realiza una búsqueda general usando las fuentes especificadas
        """
        logger.info(f"Realizando búsqueda centralizada con consulta: '{query}', fuentes: {sources or 'todas'}")

        results = {}
        selected_sources = sources or list(self.providers.keys())

        for source_name in selected_sources:
            if source_name in self.providers:
                try:
                    # Proveer los argumentos adecuados para cada fuente
                    provider = self.providers[source_name]

                    if source_name == 'general':
                        # Búsqueda general usando motores reales
                        search_kwargs = kwargs.get('general_options', {})
                        result = provider.general_web_search(query, search_kwargs.get('max_results', 10))
                        results[source_name] = result

                    elif source_name == 'people':
                        # Búsqueda avanzada de personas
                        search_kwargs = kwargs.get('people_options', {})
                        search_type = search_kwargs.get('type', 'people')
                        criteria = {'name': query}
                        if search_kwargs.get('location'):
                            criteria['location'] = search_kwargs['location']
                        result = provider.advanced_search(criteria, search_type)
                        results[source_name] = result

                    elif source_name == 'email':
                        # Búsqueda de información por email real
                        hibp_key = kwargs.get('hibp_api_key')
                        if query and '@' in query:
                            search_kwargs = kwargs.get('email_options', {})
                            result = provider.search_email_info(query, hibp_key)
                            results[source_name] = result
                        else:
                            results[source_name] = {"warning": "Búsqueda por email requiere formato válido"}

                    elif source_name == 'social':
                        # Búsqueda social con credenciales reales
                        search_kwargs = kwargs.get('social_options', {})
                        usernames = search_kwargs.get('usernames', [query])
                        platforms = search_kwargs.get('platforms', ['twitter', 'linkedin'])
                        api_configs = search_kwargs.get('api_configs', {})
                        if usernames and platforms:
                            social_results = provider.search_multiple_social_profiles(usernames, platforms, api_configs)
                            results[source_name] = social_results
                        else:
                            results[source_name] = {"warning": "Necesita usernames y plataformas para búsqueda social"}

                    else:
                        # Fallback general
                        results[source_name] = {"warning": f"No se pudo completar búsqueda en {source_name}"}

                except Exception as e:
                    logger.error(f"Error en buscar en fuente {source_name}: {e}")
                    results[source_name] = {"error": str(e)}
            else:
                results[source_name] = {"error": f"Fuente de búsqueda '{source_name}' no soportada"}

        return results


# Instancia global para uso simple
coordinator = SearchCoordinator()


def execute_search(query: str, sources: List[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Función directa para ejecutar búsqueda centralizada
    """
    return coordinator.search(query, sources, **kwargs)