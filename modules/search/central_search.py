# modules/search/central_search.py
"""
Central Search Coordinator — OSINT UX SAFE
✔ No ejecuta fuentes sensibles sin intención explícita
✔ Respeta modo pasivo / activo
✔ Devuelve estructura limpia y predecible
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Imports tolerantes
try:
    from . import general_search
except Exception:
    general_search = None

try:
    from . import people_search
except Exception:
    people_search = None

try:
    from . import emailint
except Exception:
    emailint = None

try:
    from .socmint.socmint import search_social_profiles
except Exception:
    search_social_profiles = None

# ✅ NUEVO: dorks (opcional) para ejecución explícita
try:
    from . import google_dorks
except Exception:
    google_dorks = None


class SearchCoordinator:

    SAFE_DEFAULT_SOURCES = {"general", "people"}
    SENSITIVE_SOURCES = {"darkweb", "dorks", "archive"}

    def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        mode: str = "passive",
        **kwargs
    ) -> Dict[str, Any]:

        logger.info("Central search | query=%s | sources=%s | mode=%s", query, sources, mode)

        results: Dict[str, Any] = {}
        uid = user_id or 1

        # ---------- Default seguro ----------
        selected_sources = set(sources) if sources else self.SAFE_DEFAULT_SOURCES

        # ---------- GENERAL (pasivo) ----------
        if "general" in selected_sources and general_search:
            results["general"] = general_search.search_general_real(
                query=query,
                user_id=uid,
                mode=mode
            )

        # ---------- PEOPLE ----------
        if "people" in selected_sources and people_search:
            if hasattr(people_search, "search_people_by_name"):
                results["people"] = {
                    "source": "people",
                    "results": people_search.search_people_by_name(query)
                }

        # ---------- EMAIL (solo si es email) ----------
        if "email" in selected_sources and emailint:
            if "@" in query:
                results["email"] = emailint.search_email_info(query, uid)
            else:
                results["email"] = {"source": "email", "skipped": "query_is_not_email"}

        # ---------- SOCIAL (SOLO si username explícito) ----------
        if "social" in selected_sources and search_social_profiles:
            username = kwargs.get("username")
            if username:
                results["social"] = search_social_profiles(username)
            else:
                results["social"] = {"source": "social", "skipped": "username_required"}

        # ---------- Sensibles: solo si intención explícita ----------
        allow_sensitive: bool = bool(kwargs.get("allow_sensitive", False))
        sensitive_allowed = (mode == "active") or allow_sensitive

        # DORKS (solo activo/explicito)
        if "dorks" in selected_sources:
            if sensitive_allowed and google_dorks and hasattr(google_dorks, "search_google_dorks"):
                dorks_file = (kwargs.get("dorks_file") or "").strip() or None
                max_results = kwargs.get("max_results", 10)
                max_patterns = kwargs.get("max_patterns")  # puede ser None

                try:
                    results["dorks"] = {
                        "source": "dorks",
                        "query": query,
                        "results": google_dorks.search_google_dorks(
                            query,
                            user_id=uid,
                            dorks_file=dorks_file,
                            max_results=max_results,
                            max_patterns=max_patterns,
                        ),
                        "has_data": True,
                        "errors": [],
                        "dorks_file": dorks_file,
                    }
                except Exception as e:
                    results["dorks"] = {
                        "source": "dorks",
                        "query": query,
                        "results": [],
                        "has_data": False,
                        "errors": [str(e)],
                        "dorks_file": dorks_file,
                    }
            else:
                results["dorks"] = {
                    "source": "dorks",
                    "skipped": "explicit_user_action_required",
                    "hint": "Use mode='active' o allow_sensitive=True"
                }

        # Bloqueo por defecto del resto sensibles
        for forbidden in ("darkweb", "archive"):
            if forbidden in selected_sources:
                results[forbidden] = {
                    "source": forbidden,
                    "skipped": "explicit_user_action_required"
                }

        return results


coordinator = SearchCoordinator()


def execute_search(
    query: str,
    sources: Optional[List[str]] = None,
    user_id: Optional[int] = None,
    mode: str = "passive",
    **kwargs
) -> Dict[str, Any]:
    return coordinator.search(
        query=query,
        sources=sources,
        user_id=user_id,
        mode=mode,
        **kwargs
    )
