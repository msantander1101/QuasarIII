# modules/search/advanced_search.py
"""
Advanced Search Coordinator — versión endurecida y estable.
Todos los módulos (people, email, SOCMINT, domains, web, dorks)
devuelven estructuras coherentes para UI/Streamlit.
✅ Logging con trace_id por búsqueda.
✅ Logs por fuente con has_data + counts.
"""

import time
import logging
import uuid
from typing import Dict, Any, List, Optional

from .correlation.profile_unifier import unify_profiles

logger = logging.getLogger(__name__)

try:
    from . import people_search
except Exception:
    people_search = None

try:
    from . import emailint
except Exception:
    emailint = None

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
            t0 = time.time()
            r = requests.get(api, timeout=10)
            dt = round(time.time() - t0, 3)

            logger.debug("[web] ddg_api http=%s time=%ss q=%s", r.status_code, dt, query)

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

    def _search_dorks(
        self,
        query: str,
        extra_queries: Optional[List[str]] = None,
        dorks_file: Optional[str] = None,
        user_id: int = 1,
        max_results: int = 10,
        max_patterns: Optional[int] = None,
        trace_id: Optional[str] = None,
        only_with_hits: bool = True,  # ✅ lo que quieres para UI
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

                logger.info(
                    "[trace=%s] dorks start | queries=%s | file=%s | max_results=%s | max_patterns=%s | only_with_hits=%s",
                    trace_id, len(queries), dorks_file, max_results, max_patterns, only_with_hits
                )

                aggregated: List[Dict[str, Any]] = []
                for q in queries:
                    q_results = google_dorks.search_google_dorks(
                        q,
                        user_id=user_id,
                        dorks_file=dorks_file,
                        max_results=max_results,
                        max_patterns=max_patterns,
                        trace_id=trace_id,              # ✅ nuevo
                        only_with_hits=only_with_hits,  # ✅ nuevo
                    )
                    if isinstance(q_results, list):
                        aggregated.extend(q_results)

                out["results"] = aggregated
                out["has_data"] = bool(aggregated)

                engines = {}
                total_hits = 0
                for e in aggregated:
                    if isinstance(e, dict):
                        eng = e.get("engine") or "unknown"
                        engines[eng] = engines.get(eng, 0) + 1
                        total_hits += int(e.get("subresults_count") or 0)

                logger.info(
                    "[trace=%s] dorks done | entries=%s | total_hits=%s | engines=%s | has_data=%s",
                    trace_id, len(aggregated), total_hits, engines, out["has_data"]
                )

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
        trace_id = str(uuid.uuid4())[:8]
        start = time.time()

        results: Dict[str, Any] = {}
        searched: List[str] = []

        logger.info("[trace=%s] search start | query=%s | sources=%s | user_id=%s", trace_id, query, sources, user_id)

        try:
            if "people" in sources:
                t0 = time.time()
                results["people"] = self._search_people(query)
                searched.append("people")
                logger.info("[trace=%s] people done | has_data=%s n=%s time=%ss",
                            trace_id,
                            results["people"].get("has_data"),
                            len(results["people"].get("results") or []),
                            round(time.time() - t0, 3))

            if "email" in sources:
                t0 = time.time()
                results["email"] = self._search_email(query, email=email, user_id=user_id)
                searched.append("email")
                logger.info("[trace=%s] email done | has_data=%s time=%ss",
                            trace_id,
                            results["email"].get("has_data"),
                            round(time.time() - t0, 3))

            if "domain" in sources:
                t0 = time.time()
                results["domain"] = self._search_domain(query)
                searched.append("domain")
                logger.info("[trace=%s] domain done | has_data=%s time=%ss",
                            trace_id,
                            results["domain"].get("has_data"),
                            round(time.time() - t0, 3))

            if "web" in sources:
                t0 = time.time()
                results["web"] = self._search_web(query)
                searched.append("web")
                logger.info("[trace=%s] web done | has_data=%s n=%s time=%ss",
                            trace_id,
                            results["web"].get("has_data"),
                            len(results["web"].get("results") or []),
                            round(time.time() - t0, 3))

            if "dorks" in sources:
                extra_dorks: List[str] = []
                if email and "@" in email and email != query:
                    extra_dorks.append(email)

                t0 = time.time()
                results["dorks"] = self._search_dorks(
                    query,
                    extra_queries=extra_dorks,
                    dorks_file=dorks_file,
                    user_id=user_id,
                    max_results=dorks_max_results,
                    max_patterns=dorks_max_patterns,
                    trace_id=trace_id,
                    only_with_hits=True,   # ✅ lo que quieres para UI
                )
                searched.append("dorks")
                logger.info("[trace=%s] dorks wrapper done | has_data=%s entries=%s time=%ss",
                            trace_id,
                            results["dorks"].get("has_data"),
                            len(results["dorks"].get("results") or []),
                            round(time.time() - t0, 3))

        except Exception as e:
            logger.error("[trace=%s] CRITICAL error in multi-source search", trace_id, exc_info=True)
            results["fatal_error"] = str(e)

        results["_metadata"] = {
            "query": query,
            "search_time": round(time.time() - start, 3),
            "sources_searched": searched,
            "trace_id": trace_id,
        }

        logger.info("[trace=%s] search end | time=%ss | searched=%s", trace_id, results["_metadata"]["search_time"], searched)

        return results

    def search_with_filtering(self, query: str, sources: List[str], username=None, filters=None, user_id=1):
        return self.search_multiple_sources(query, sources, username=username, user_id=user_id)


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
            logger.info("[trace=%s] unify_profiles ok | score=%s",
                        results.get("_metadata", {}).get("trace_id"),
                        unified_profile.get("confidence_score"))
    except Exception as e:
        logger.warning("[trace=%s] Profile unification failed: %s",
                       results.get("_metadata", {}).get("trace_id"), e)

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
