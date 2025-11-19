# modules/search/central_search.py
"""
Módulo central para coordinar búsquedas en diferentes tipos.
"""

import logging
from typing import Dict, List, Any, Union

# Importar módulos de búsqueda sin usar '*' para evitar importaciones circulares
import modules.search.general_search
import modules.search.webosint
import modules.search.socmint
import modules.search.people_search
import modules.search.pastesearch
# import modules.search.breachdata
import modules.search.emailint
import modules.search.domainint
import modules.search.archive_search
import modules.search.darkweb
import modules.search.imageint
import modules.search.geoint
import modules.search.publicdata
import modules.search.cryptocurrencies
import modules.search.digital_comm
import modules.search.mobile_osint
import modules.search.phoneint
import modules.search.documentint

logger = logging.getLogger(__name__)


class SearchCoordinator:
    def __init__(self):
        self.modules = {
            'general': modules.search.general_search,
            'web': modules.search.webosint,
            'social': modules.search.socmint,
            'people': modules.search.people_search,
            'pastes': modules.search.pastesearch,
            # 'breaches': modules.search.breachdata,
            'emails': modules.search.emailint,
            'domains': modules.search.domainint,
            'archives': modules.search.archive_search,
            'darkweb': modules.search.darkweb,
            'images': modules.search.imageint,
            'geo': modules.search.geoint,
            'public_data': modules.search.publicdata,
            'crypto': modules.search.cryptocurrencies,
            'communications': modules.search.digital_comm,
            'mobile': modules.search.mobile_osint,
            'phones': modules.search.phoneint,
            'documents': modules.search.documentint,
        }

    def search(self, query: str, sources: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Realiza una búsqueda general según los tipos especificados.

        Args:
            query: Término de búsqueda principal.
            sources: Tipos de búsqueda: 'general', 'web', 'social', 'people', etc.
            **kwargs: Argumentos adicionales para los motores de búsqueda específicos.

        Returns:
            Dict con resultados agrupados por tipo de fuente.
        """
        logger.info(f"Realizando búsqueda centralizada para el término '{query}' en fuentes: {sources or 'todas'}")
        results = {}

        if sources is None:
            sources = list(self.modules.keys())

        missing_modules = [src for src in sources if src not in self.modules]
        if missing_modules:
            logger.warning(f"Tipos de búsqueda no disponibles: {missing_modules}")

        for source_name in sources:
            if source_name in self.modules:
                try:
                    logger.debug(f"Ejecutando módulo '{source_name}' para búsqueda: '{query}'")
                    # Obtener función de búsqueda del módulo
                    source_module = self.modules[source_name]
                    # Definir el nombre de la función según el tipo
                    search_func = None

                    # Tratar de encontrar la función específica
                    if hasattr(source_module, 'search_' + source_name):
                        search_func = getattr(source_module, 'search_' + source_name)
                    elif hasattr(source_module, source_name + '_search'):
                        search_func = getattr(source_module, source_name + '_search')
                    elif hasattr(source_module, 'search'):
                        search_func = getattr(source_module, 'search')

                    if search_func and callable(search_func):
                        # Llamada con argumentos
                        search_kwargs = kwargs.get(f"{source_name}_options", {})
                        if source_name == 'emails':  # Para email search necesitamos pasar el query
                            result = search_func(query, **search_kwargs)
                        else:
                            result = search_func(query, **search_kwargs)
                        results[source_name] = result
                    else:
                        # Fallback - llamada con `query` único como ejemplo general
                        if hasattr(source_module, 'general_search'):
                            result = source_module.general_search(query, **kwargs)
                            results[source_name] = result
                        elif hasattr(source_module, 'search'):
                            # Si no hay función específica, probar con la función genérica
                            result = source_module.search(query, **kwargs)
                            results[source_name] = result
                        else:
                            # Ejecutar una función estándar si no hay función explícita
                            logger.warning(f"No se encontró función de búsqueda específica en {source_name}")
                            continue  # Saltar este módulo
                except Exception as e:
                    logger.error(f"Error al ejecutar búsqueda en modulo '{source_name}': {str(e)}")
                    results[source_name] = {"error": str(e)}
            else:
                results[source_name] = {"error": "Fuente de búsqueda no soportada"}

        return results


# Exportar una instancia global para uso fácil
coordinator = SearchCoordinator()


# Función auxiliar conveniente para uso rápido
def execute_search(query: str, sources: List[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Función rápida de búsqueda general integrada.
    """
    return coordinator.search(query, sources, **kwargs)