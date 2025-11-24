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
    socmint,
    darkweb,
    archive_search,
    google_dorks
)

logger = logging.getLogger(__name__)


class SearchCoordinator:
    """
    Coordinador de búsqueda central que integra todos los módulos reales y confiables
    """

    def __init__(self):
        self.providers = {
            'general': general_search,
            'people': people_search,
            'email': emailint,
            'social': socmint,
            'darkweb': darkweb,
            'archive': archive_search,
            # Nuevo proveedor de búsqueda: Google Dorks
            'dorks': google_dorks
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
                        # El módulo emailint ya tiene el acceso a hibp_key
                        hibp_key = kwargs.get('hibp_api_key')
                        if query and '@' in query:
                            search_kwargs = kwargs.get('email_options', {})
                            result = provider.search_email_info(query, user_id=None, services=None)  # user_id no requerido aquí
                            results[source_name] = result
                        else:
                            results[source_name] = {
                                "warning": "Búsqueda por email requiere formato válido (ej: juan@empresa.com)"
                            }

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
                        # Búsqueda real en catálogo oscuro (con API real si está disponible)
                        darkweb_options = kwargs.get('darkweb_options', {})
                        result = provider.search_dark_web_catalog(query, max_results=darkweb_options.get('max_results', 5))
                        results[source_name] = result

                    elif source_name == 'archive':
                        # Búsqueda en arquitectura web (Wayback, Archive)
                        archive_options = kwargs.get('archive_options', {})
                        result = provider.search_web_archives(query, archive_options.get('sources', ['wayback', 'archive']))
                        results[source_name] = result

                    elif source_name == 'dorks':
                        # Búsqueda mediante Google Dorks
                        dorks_options = kwargs.get('dorks_options', {})
                        patterns = dorks_options.get('patterns')
                        # El módulo google_dorks expone "search_google_dorks"
                        try:
                            result = provider.search_google_dorks(query, patterns)
                        except AttributeError:
                            # Compatibilidad con wrappers "search_dorks" o "search"
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


# Instancia global para uso simple
coordinator = SearchCoordinator()


def execute_search(query: str, sources: List[str] = None, user_id: int = None, **kwargs) -> Dict[str, Any]:
    """
    Función directa para ejecutar búsqueda centralizada con datos reales
    """
    # Solo si se requieren fuentes avanzadas (con API real), usamos auth
    real_sources = [
        'predictasearch', 'theirstack', 'analystresearchtools',
        'carnetai', 'vehicleai', 'osintnova'
    ]
    if sources and any(s in real_sources for s in sources):
        return general_search.search_general_real(query, user_id, sources)

    # Búsqueda estándar para fuentes reales (HIBP, SkyMem, etc.)
    logger.info(f"Realizando búsqueda estándar: {query}, fuentes: {sources}")
    results = {}

    if sources is None:
        sources = list(coordinator.providers.keys())

    for source_name in sources:
        if source_name in coordinator.providers:
            try:
                logger.debug(f"Ejecutando módulo '{source_name}' para consulta: '{query}'")

                # Aseguramos que la función exista
                search_func = None
                if hasattr(coordinator.providers[source_name], 'search_' + source_name):
                    search_func = getattr(coordinator.providers[source_name], 'search_' + source_name)
                elif hasattr(coordinator.providers[source_name], source_name + '_search'):
                    search_func = getattr(coordinator.providers[source_name], source_name + '_search')
                elif hasattr(coordinator.providers[source_name], 'search'):
                    search_func = getattr(coordinator.providers[source_name], 'search')

                if not search_func or not callable(search_func):
                    logger.warning(f"No se encontró función de búsqueda en {source_name}")
                    results[source_name] = {"error": "Función no encontrada"}
                    continue

                # Pasamos el user_id solo si es necesario (por ejemplo en emailint)
                search_kwargs = kwargs.get(f"{source_name}_options", {})
                if source_name == 'email':
                    hibp_key = kwargs.get('hibp_api_key')
                    # Se pasará directamente al módulo emailint
                    search_kwargs['hibp_api_key'] = hibp_key

                if source_name == 'email':
                    result = search_func(query, hibp_key=hibp_key, **search_kwargs)
                else:
                    result = search_func(query, **search_kwargs)

                results[source_name] = result
            except Exception as e:
                logger.error(f"Error en {source_name}: {str(e)}")
                results[source_name] = {"error": str(e)}
        else:
            results[source_name] = {"error": f"Fuente no soportada: {source_name}"}

    return results