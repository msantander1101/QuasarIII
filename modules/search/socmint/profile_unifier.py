# modules/search/profile_unifier.py
"""
Profile Unifier
Unifica resultados OSINT en una identidad coherente.
"""

from typing import Dict, Any


def unify_profile(results: Dict[str, Any]) -> Dict[str, Any]:
    profile = {
        "identity": {
            "name": None,
            "username": None,
            "email": None,
        },
        "social_profiles": {},
        "confidence": 0.0,
        "sources": [],
    }

    # PEOPLE
    people = results.get("people", {}).get("results", [])
    if people:
        p = people[0]
        profile["identity"]["name"] = p.get("name")
        profile["confidence"] += 0.2
        profile["sources"].append("people")

    # EMAIL
    email_res = results.get("email", {}).get("results", [])
    if email_res:
        e = email_res[0]
        profile["identity"]["email"] = e.get("email")
        profile["confidence"] += 0.3
        profile["sources"].append("email")

    # SOCIAL
    social = results.get("social", {})
    if social.get("has_data"):
        profile["social_profiles"] = social.get("results", {})
        profile["confidence"] += 0.4
        profile["sources"].append("social")

    profile["confidence"] = round(min(profile["confidence"], 1.0), 2)

    return profile
