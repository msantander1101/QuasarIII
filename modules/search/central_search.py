import logging
from typing import Dict, List, Any, Optional
from modules.search.socmint.socmint import search_social_profiles
from . import (
    general_search,
    people_search,
    emailint,
    darkweb,
    archive_search,
    google_dorks
)

logger = logging.getLogger(__name__)


class SearchCoordinator:

    def __init__(self, max_workers: int = 5):
        self.providers = {
            'general': general_search,
            'people': people_search,
            'email': emailint,
            'social': search_social_profiles,
            'darkweb': darkweb,
            'archive': archive_search,
            'dorks': google_dorks
        }
        self.max_workers = max_workers

    def search(self, query: str, sources: List[str] = None, user_id: int = None, **kwargs):

        logger.info(f"Realizando búsqueda centralizada: '{query}'")

        results = {}
        selected_sources = sources or list(self.providers.keys())

        for source in selected_sources:

            if source not in self.providers:
                results[source] = {"error": f"Fuente inexistente: {source}"}
                continue

            provider = self.providers[source]

            try:
                # GENERAL
                if source == 'general':
                    opts = kwargs.get('general_options', {})
                    max_results = opts.get('max_results', 10)
                    results[source] = provider.search_web_search_real(query, max_results=max_results)

                # PEOPLE
                elif source == 'people':
                    opts = kwargs.get('people_options', {})
                    criteria = {"name": query}
                    if opts.get("location"):
                        criteria["location"] = opts["location"]
                    results[source] = provider.advanced_search(criteria, "people")

                # EMAIL
                elif source == 'email':
                    opts = kwargs.get('email_options', {})
                    services = opts.get('services', ['hibp', 'skymem', 'ghunt'])
                    results[source] = provider.search_email_info(query, user_id=user_id, services=services)

                # SOCIAL (SOCMINT)
                elif source == 'social':
                    opts = kwargs.get('social_options', {})
                    username = opts.get("username")  # username manual directo
                    results[source] = { "results": search_social_profiles(query=query, username=username)}

                # DARKWEB
                elif source == 'darkweb':
                    opts = kwargs.get('darkweb_options', {})
                    max_results = opts.get("max_results", 5)
                    results[source] = provider.search_dark_web_catalog(query, max_results=max_results)

                # ARCHIVE
                elif source == 'archive':
                    opts = kwargs.get('archive_options', {})
                    sources_arch = opts.get("sources", ['wayback', 'archive'])
                    results[source] = provider.search_web_archives(query, sources_arch)

                # DORKS
                elif source == 'dorks':
                    opts = kwargs.get('dorks_options', {})
                    patterns = opts.get('patterns')
                    results[source] = provider.search_google_dorks(query, patterns)

            except Exception as e:
                logger.error(f"Error ejecutando fuente {source}: {e}")
                results[source] = {"error": str(e)}

        return results


# Instancia global
coordinator = SearchCoordinator()


def execute_search(query: str, sources: List[str] = None, user_id: Optional[int] = None, **kwargs):
    return coordinator.search(query, sources=sources, user_id=user_id, **kwargs)
