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


# ============================================================
# COORDINADOR CENTRAL
# ============================================================

class SearchCoordinator:

    SAFE_DEFAULT_SOURCES = {"general", "people"}

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

        # ---------- Default seguro ----------
        selected_sources = set(sources) if sources else self.SAFE_DEFAULT_SOURCES

        # ---------- GENERAL (pasivo) ----------
        if "general" in selected_sources and general_search:
            results["general"] = general_search.search_general_real(
                query=query,
                user_id=user_id or 1,
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
                results["email"] = emailint.search_email_info(query, user_id or 1)
            else:
                results["email"] = {
                    "source": "email",
                    "skipped": "query_is_not_email"
                }

        # ---------- SOCIAL (SOLO si username explícito) ----------
        if "social" in selected_sources and search_social_profiles:
            username = kwargs.get("username")
            if username:
                results["social"] = search_social_profiles(username)
            else:
                results["social"] = {
                    "source": "social",
                    "skipped": "username_required"
                }

        # ---------- BLOQUEAR FUENTES SENSIBLES ----------
        for forbidden in ("darkweb", "dorks", "archive"):
            if forbidden in selected_sources:
                results[forbidden] = {
                    "source": forbidden,
                    "skipped": "explicit_user_action_required"
                }

        return results


# ============================================================
# API PÚBLICA
# ============================================================

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
