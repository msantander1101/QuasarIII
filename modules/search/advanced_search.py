# modules/search/advanced_search.py
"""
Advanced Search Coordinator — versión endurecida y estable.
Todos los módulos (people, email, SOCMINT, domains, web, dorks)
devuelven estructuras coherentes para UI/Streamlit.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from modules.search.socmint.profile_unifier import unify_profile
from .correlation.profile_unifier import unify_profiles

logger = logging.getLogger(__name__)

# Importaciones tolerantes
try:
    from . import people_search
except Exception:
    people_search = None

try:
    from . import emailint
except Exception:
    emailint = None

try:
    from . import socmint
except Exception:
    socmint = None

try:
    from . import archive_search
except Exception:
    archive_search = None

try:
    from . import domainint
except Exception:
    domainint = None

try:
    from . import google_dorks
except Exception:
    google_dorks = None


class AdvancedSearcher:

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def _search_people(self, query: str) -> Dict[str, Any]:
        out = {"source": "people", "query": query, "results": [], "errors": [], "has_data": False}
        try:
            if not people_search or not hasattr(people_search, "search_people_by_name"):
                out["errors"].append("people_search module missing")
                return out

            res = people_search.search_people_by_name(query)
            if isinstance(res, list):
                out["results"] = res
                out["has_data"] = len(res) > 0
        except Exception as e:
            logger.exception("People search failed")
            out["errors"].append(str(e))
        return out

    def _search_email(self, query: str, email: str = "", user_id: int = 1) -> Dict[str, Any]:
        out = {"source": "email", "query": query, "results": [], "errors": [], "has_data": False}
        try:
            email_to_use = email or query
            if not email_to_use or "@" not in email_to_use:
                return out

            if not emailint or not hasattr(emailint, "search_email_info"):
                out["errors"].append("emailint module missing")
                return out

            info = emailint.search_email_info(email_to_use, user_id=user_id)
            out["results"] = [info]
            out["has_data"] = True
        except Exception as e:
            logger.exception("Email search failed")
            out["errors"].append(str(e))
        return out

    def _search_social(self, query: str, username: Optional[str] = None):
        out = {"source": "social", "query": query, "results": {}, "errors": [], "has_data": False}
        username_to_use = username or (query if "@" not in query else None)
        if not username_to_use:
            return out

        from modules.search.socmint.socmint import search_social_profiles
        raw = search_social_profiles(username_to_use)
        profiles = raw.get("social_profiles", {})

        valid_profiles = {k: v for k, v in profiles.items() if isinstance(v, dict) and not v.get("error")}
        if valid_profiles:
            out["results"] = valid_profiles
            out["has_data"] = True
        else:
            out["results"] = profiles
            out["has_data"] = False

        out["errors"].extend(raw.get("errors", []))
        return out

    def _search_domain(self, query: str) -> Dict[str, Any]:
        out = {"source": "domain", "query": query, "results": {}, "errors": [], "has_data": False}
        try:
            if domainint and hasattr(domainint, "whois_lookup"):
                whois = domainint.whois_lookup(query)
                dns = domainint.dns_lookup(query) if hasattr(domainint, "dns_lookup") else {}
                passive = domainint.passive_dns(query) if hasattr(domainint, "passive_dns") else {}
                out["results"] = {"whois": whois, "dns": dns, "passive": passive}
                out["has_data"] = True
                return out

            if archive_search and hasattr(archive_search, "search_web_archives"):
                arch = archive_search.search_web_archives(query, ["wayback"])
                out["results"] = {"archive": arch}
                out["has_data"] = bool(arch)
                return out

        except Exception as e:
            logger.exception("Domain search failed")
            out["errors"].append(str(e))

        return out

    def _search_web(self, query: str) -> Dict[str, Any]:
        out = {"source": "web", "query": query, "results": [], "errors": [], "has_data": False}
        try:
            import urllib.parse
            import requests

            api = (
                "https://api.duckduckgo.com/"
                f"?q={urllib.parse.quote_plus(query)}"
                "&format=json&no_redirect=1"
            )
            r = requests.get(api, timeout=10)

            if r.status_code == 200:
                data = r.json()
                topics = data.get("RelatedTopics", [])
                for t in topics:
                    if isinstance(t, dict) and t.get("FirstURL"):
                        out["results"].append({
                            "title": t.get("Text"),
                            "url": t.get("FirstURL"),
                            "snippet": t.get("Text"),
                            "confidence": 0.6,
                        })

            if out["results"]:
                out["has_data"] = True
            else:
                out["results"] = [{
                    "title": f"Search: {query}",
                    "url": f"https://duckduckgo.com/?q={query}",
                    "snippet": "",
                    "confidence": 0.3,
                }]

        except Exception as e:
            logger.exception("Web search failed")
            out["errors"].append(str(e))

        return out

    # ✅ DORKS con soporte user_id + dorks_file + límites
    def _search_dorks(
        self,
        query: str,
        extra_queries: Optional[List[str]] = None,
        dorks_file: Optional[str] = None,
        user_id: int = 1,
        max_results: int = 10,
        max_patterns: Optional[int] = None,
    ) -> Dict[str, Any]:
        out = {
            "source": "dorks",
            "query": query,
            "results": [],
            "errors": [],
            "has_data": False,
            "dorks_file": dorks_file,
        }

        try:
            if google_dorks and hasattr(google_dorks, "search_google_dorks"):
                queries: List[str] = [query]
                for candidate in extra_queries or []:
                    if candidate and candidate not in queries:
                        queries.append(candidate)

                aggregated: List[Dict[str, Any]] = []
                for q in queries:
                    q_results = google_dorks.search_google_dorks(
                        q,
                        user_id=user_id,
                        dorks_file=dorks_file,
                        max_results=max_results,
                        max_patterns=max_patterns,
                    )
                    if isinstance(q_results, list):
                        aggregated.extend(q_results)

                out["results"] = aggregated
                out["has_data"] = bool(aggregated)

        except Exception as e:
            logger.exception("Dorks search failed")
            out["errors"].append(str(e))

        return out

    def search_multiple_sources(
        self,
        query: str,
        sources: List[str],
        email: str = "",
        username: Optional[str] = None,
        user_id: int = 1,
        dorks_file: Optional[str] = None,
        dorks_max_results: int = 10,
        dorks_max_patterns: Optional[int] = None,
    ):
        start = time.time()
        results: Dict[str, Any] = {}
        searched: List[str] = []

        try:
            if "people" in sources:
                results["people"] = self._search_people(query)
                searched.append("people")

            if "email" in sources:
                results["email"] = self._search_email(query, email=email, user_id=user_id)
                searched.append("email")

            if "domain" in sources:
                results["domain"] = self._search_domain(query)
                searched.append("domain")

            if "web" in sources:
                results["web"] = self._search_web(query)
                searched.append("web")

            if "social" in sources:
                results["social"] = self._search_social(query, username=username)
                searched.append("social")

            if "dorks" in sources:
                extra_dorks: List[str] = []
                if email and "@" in email and email != query:
                    extra_dorks.append(email)

                results["dorks"] = self._search_dorks(
                    query,
                    extra_queries=extra_dorks,
                    dorks_file=dorks_file,
                    user_id=user_id,
                    max_results=dorks_max_results,
                    max_patterns=dorks_max_patterns,
                )
                searched.append("dorks")

        except Exception as e:
            logger.error("CRITICAL error in multi-source search", exc_info=True)
            results["fatal_error"] = str(e)

        results["_metadata"] = {
            "query": query,
            "search_time": round(time.time() - start, 3),
            "sources_searched": searched,
        }

        return results

    def search_with_filtering(self, query: str, sources: List[str], username=None, filters=None, user_id=1):
        base = self.search_multiple_sources(query, sources, username=username, user_id=user_id)
        return base


advanced_searcher = AdvancedSearcher()


def search_multiple_sources(
    query: str,
    selected_sources: Optional[List[str]] = None,
    email: str = "",
    username: Optional[str] = None,
    user_id: int = 1,
    dorks_file: Optional[str] = None,
    dorks_max_results: int = 10,
    dorks_max_patterns: Optional[int] = None,
):
    selected_sources = selected_sources or []

    results = advanced_searcher.search_multiple_sources(
        query,
        selected_sources,
        email=email or (query if "@" in query else ""),
        username=username,
        user_id=user_id,
        dorks_file=dorks_file,
        dorks_max_results=dorks_max_results,
        dorks_max_patterns=dorks_max_patterns,
    )

    try:
        unified_profile = unify_profiles(
            email_result=results.get("email"),
            social_result=results.get("social"),
        )
        if unified_profile and unified_profile.get("confidence_score", 0) > 0:
            results["unified_profile"] = unified_profile
    except Exception as e:
        logger.warning(f"Profile unification failed: {e}")

    return results


def search_with_filtering(
    query: str,
    selected_sources: Optional[List[str]] = None,
    username: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    user_id: int = 1,
):
    selected_sources = selected_sources or []
    return advanced_searcher.search_with_filtering(
        query,
        selected_sources,
        username=username,
        filters=filters,
        user_id=user_id,
    )
