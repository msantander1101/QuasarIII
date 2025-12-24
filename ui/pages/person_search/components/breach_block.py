import streamlit as st
from typing import Any, Dict, List, Optional

# 👇 Ajusta el import según dónde tengas dorks_block
from .dorks_block import (
    _DORKS_CSS,
    _render_card,
    _get_domain,
    _safe_int,
    _to_float,
    _risk_rank,
)


def _risk_from_conf(conf: Optional[Any]) -> str:
    """
    Heurística simple de riesgo a partir de la confianza.
    Puedes endurecerla si quieres.
    """
    c = _to_float(conf, 0.5)
    if c >= 0.8:
        return "high"
    if c >= 0.5:
        return "medium"
    return "low"


def _relevance_from_conf(conf: Optional[Any]) -> int:
    """
    Relevancia derivada directamente de la confianza [0-1] -> [0-100].
    """
    return int(round(_to_float(conf, 0.0) * 100))


def _flatten_breach_results(breach_block: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Adapta el resultado de breach_search.search_breaches al formato de tarjetas
    esperado por _render_card (mismo que dorks).

    breach_block esperado:
    {
      "source": "breach",
      "query": str,
      "user_id": int,
      "timestamp": float,
      "results": [ hits... ],
      "errors": [ ... ],
      "has_data": bool,
      "search_time": float,
    }

    Cada hit suele tener:
      - title, url, snippet, date/timestamp, confidence, source (haveibeenransom, psbdmp, etc.)
    """
    hits = breach_block.get("results") or []
    query = breach_block.get("query") or ""
    flat: List[Dict[str, Any]] = []

    for h in hits:
        if not isinstance(h, dict):
            continue

        title = h.get("title") or "Breach hit"
        url = h.get("url") or h.get("link") or "#"
        snippet = h.get("snippet") or h.get("description") or ""

        provider = h.get("source") or "breach"
        confidence = h.get("confidence")
        ts = h.get("timestamp") or h.get("date") or h.get("updated_at")

        # Heurísticas para integrarlo en el mismo modelo visual
        risk_level = h.get("risk_level") or _risk_from_conf(confidence)
        relevance = h.get("relevance_score")
        if relevance is None:
            relevance = _relevance_from_conf(confidence)

        # Tipificamos como "leak"/"paste" para el iconito
        entity_type = h.get("entity_type") or "leak"
        match_type = h.get("match_type") or "exact"  # puedes cambiar a "contextual" si lo prefieres

        flat.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": provider,
                # usamos provider también como "engine" para chip visual
                "engine": h.get("engine") or provider,
                "confidence": confidence,

                "entity_type": entity_type,
                "match_type": match_type,
                "relevance_score": relevance,
                "published_at": ts,
                "location_hint": h.get("location_hint"),
                "risk_level": risk_level,
                "linked_to_profile": h.get("linked_to_profile"),

                # meta técnico (igual que dorks)
                "query_used": h.get("query_used") or query,
                "pattern": h.get("pattern"),  # normalmente None en brechas, pero por si acaso
            }
        )

    return flat


def render_breach_block(breach_block: Dict[str, Any]):
    """
    Render de resultados de breach_search con EXACTAMENTE el mismo formato visual
    que las tarjetas de dorks.
    """
    if not isinstance(breach_block, dict):
        return

    # CSS compartido con dorks
    st.markdown(_DORKS_CSS, unsafe_allow_html=True)

    # Mensajes de error del módulo de brechas (si quieres verlos)
    for err in breach_block.get("errors") or []:
        st.warning(f"Breach search: {err}")

    cards = _flatten_breach_results(breach_block)

    # Si no hay nada útil, no pintamos sección
    if not cards:
        return

    # Ordenamos igual que en dorks_block: relevance desc → risk desc → conf desc → domain asc
    def _sort_key(c: Dict[str, Any]):
        rel = _safe_int(c.get("relevance_score"), default=0) or 0
        risk = _risk_rank(c.get("risk_level"))
        conf = _to_float(c.get("confidence"), 0.0)
        dom = _get_domain((c.get("url") or "").strip())
        return (-rel, -risk, -conf, dom)

    cards.sort(key=_sort_key)

    st.markdown("### 💥 Brechas y filtraciones")
    st.caption(f"{len(cards)} resultados consolidados (ordenados por relevancia/riesgo/confianza)")

    cols = st.columns(2)
    for i, card in enumerate(cards):
        with cols[i % 2]:
            _render_card(card)
import streamlit as st
from typing import Any, Dict, List, Optional

# 👇 Ajusta el import según dónde tengas dorks_block
from .dorks_block import (
    _DORKS_CSS,
    _render_card,
    _get_domain,
    _safe_int,
    _to_float,
    _risk_rank,
)


def _risk_from_conf(conf: Optional[Any]) -> str:
    """
    Heurística simple de riesgo a partir de la confianza.
    Puedes endurecerla si quieres.
    """
    c = _to_float(conf, 0.5)
    if c >= 0.8:
        return "high"
    if c >= 0.5:
        return "medium"
    return "low"


def _relevance_from_conf(conf: Optional[Any]) -> int:
    """
    Relevancia derivada directamente de la confianza [0-1] -> [0-100].
    """
    return int(round(_to_float(conf, 0.0) * 100))


def _flatten_breach_results(breach_block: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Adapta el resultado de breach_search.search_breaches al formato de tarjetas
    esperado por _render_card (mismo que dorks).

    breach_block esperado:
    {
      "source": "breach",
      "query": str,
      "user_id": int,
      "timestamp": float,
      "results": [ hits... ],
      "errors": [ ... ],
      "has_data": bool,
      "search_time": float,
    }

    Cada hit suele tener:
      - title, url, snippet, date/timestamp, confidence, source (haveibeenransom, psbdmp, etc.)
    """
    hits = breach_block.get("results") or []
    query = breach_block.get("query") or ""
    flat: List[Dict[str, Any]] = []

    for h in hits:
        if not isinstance(h, dict):
            continue

        title = h.get("title") or "Breach hit"
        url = h.get("url") or h.get("link") or "#"
        snippet = h.get("snippet") or h.get("description") or ""

        provider = h.get("source") or "breach"
        confidence = h.get("confidence")
        ts = h.get("timestamp") or h.get("date") or h.get("updated_at")

        # Heurísticas para integrarlo en el mismo modelo visual
        risk_level = h.get("risk_level") or _risk_from_conf(confidence)
        relevance = h.get("relevance_score")
        if relevance is None:
            relevance = _relevance_from_conf(confidence)

        # Tipificamos como "leak"/"paste" para el iconito
        entity_type = h.get("entity_type") or "leak"
        match_type = h.get("match_type") or "exact"  # puedes cambiar a "contextual" si lo prefieres

        flat.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": provider,
                # usamos provider también como "engine" para chip visual
                "engine": h.get("engine") or provider,
                "confidence": confidence,

                "entity_type": entity_type,
                "match_type": match_type,
                "relevance_score": relevance,
                "published_at": ts,
                "location_hint": h.get("location_hint"),
                "risk_level": risk_level,
                "linked_to_profile": h.get("linked_to_profile"),

                # meta técnico (igual que dorks)
                "query_used": h.get("query_used") or query,
                "pattern": h.get("pattern"),  # normalmente None en brechas, pero por si acaso
            }
        )

    return flat


def render_breach_block(breach_block: Dict[str, Any]):
    """
    Render de resultados de breach_search con EXACTAMENTE el mismo formato visual
    que las tarjetas de dorks.
    """
    if not isinstance(breach_block, dict):
        return

    # CSS compartido con dorks
    st.markdown(_DORKS_CSS, unsafe_allow_html=True)

    # Mensajes de error del módulo de brechas (si quieres verlos)
    for err in breach_block.get("errors") or []:
        st.warning(f"Breach search: {err}")

    cards = _flatten_breach_results(breach_block)

    # Si no hay nada útil, no pintamos sección
    if not cards:
        return

    # Ordenamos igual que en dorks_block: relevance desc → risk desc → conf desc → domain asc
    def _sort_key(c: Dict[str, Any]):
        rel = _safe_int(c.get("relevance_score"), default=0) or 0
        risk = _risk_rank(c.get("risk_level"))
        conf = _to_float(c.get("confidence"), 0.0)
        dom = _get_domain((c.get("url") or "").strip())
        return (-rel, -risk, -conf, dom)

    cards.sort(key=_sort_key)

    st.markdown("### 💥 Brechas y filtraciones")
    st.caption(f"{len(cards)} resultados consolidados (ordenados por relevancia/riesgo/confianza)")

    cols = st.columns(2)
    for i, card in enumerate(cards):
        with cols[i % 2]:
            _render_card(card)
