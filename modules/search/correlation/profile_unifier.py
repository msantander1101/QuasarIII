"""
Profile Unifier
Email → Username → Social correlation engine
"""

import re
from typing import Dict, Any, List


# -------------------------------------------------
# USERNAME EXTRACTION
# -------------------------------------------------

def extract_usernames_from_email(email: str) -> List[str]:
    """
    Genera candidatos de username desde email
    """
    if not email or "@" not in email:
        return []

    local = email.split("@")[0].lower()

    candidates = {
        local,
        local.replace(".", ""),
        local.replace("_", ""),
        local.replace("-", ""),
    }

    # separar números
    base = re.sub(r"\d+$", "", local)
    if base and base != local:
        candidates.add(base)

    return list(candidates)


# -------------------------------------------------
# SOCIAL NORMALIZATION
# -------------------------------------------------

def normalize_social_results(social_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normaliza Sherlock / Maigret a lista común
    """
    profiles = []

    if not isinstance(social_results, dict):
        return profiles

    for tool, payload in social_results.items():
        if not isinstance(payload, dict):
            continue

        data = payload.get("data")
        if not isinstance(data, dict):
            continue

        for site, info in data.items():
            if not isinstance(info, dict):
                continue

            profiles.append({
                "platform": site,
                "username": info.get("username"),
                "url": info.get("url"),
                "tool": tool,
                "confidence": 0.6
            })

    return profiles


# -------------------------------------------------
# UNIFICATION CORE
# -------------------------------------------------

def unify_profiles(
    email_result: Dict[str, Any] = None,
    social_result: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Devuelve un PERFIL UNIFICADO
    """

    unified = {
        "primary_identifier": None,
        "emails": [],
        "usernames": [],
        "social_profiles": [],
        "sources": [],
        "confidence_score": 0.0
    }

    score = 0.0

    # ---------------- EMAIL ----------------
    if email_result:
        email = email_result.get("query")
        if email:
            unified["primary_identifier"] = email
            unified["emails"].append(email)
            unified["sources"].append("email")
            score += 0.3

            # usernames desde email
            unified["usernames"].extend(
                extract_usernames_from_email(email)
            )

    # ---------------- SOCIAL ----------------
    if social_result:
        raw = social_result.get("results", {})
        profiles = normalize_social_results(raw)

        if profiles:
            unified["social_profiles"] = profiles
            unified["sources"].append("social")
            score += 0.4

            for p in profiles:
                if p.get("username"):
                    unified["usernames"].append(p["username"])

    # ---------------- CLEANUP ----------------
    unified["emails"] = list(set(unified["emails"]))
    unified["usernames"] = list(set(unified["usernames"]))

    unified["confidence_score"] = round(min(score, 1.0), 2)

    return unified
