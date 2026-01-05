import streamlit as st
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


# ------------------------------
# CSS: look profesional
# ------------------------------
_DORKS_CSS = """
<style>
/* Layout responsive */
.q3-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 900px) {
  .q3-grid { grid-template-columns: 1fr; }
}

/* Card */
.q3-card {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 14px 14px 12px 14px;
  background: rgba(255,255,255,0.03);
  box-shadow: 0 10px 26px rgba(0,0,0,0.22);
  transition: transform .08s ease, border-color .08s ease, background .08s ease;
}
.q3-card:hover{
  transform: translateY(-1px);
  border-color: rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.04);
}

/* Title */
.q3-title {
  font-size: 15.5px;
  font-weight: 700;
  margin: 0 0 6px 0;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Domain row */
.q3-domain-row{
  display:flex;
  align-items:center;
  gap:8px;
  color: rgba(255,255,255,0.70);
  font-size: 12.5px;
  margin-bottom: 10px;
}
.q3-favicon{
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  padding: 2px;
}

/* Snippet */
.q3-snippet{
  font-size: 13.5px;
  color: rgba(255,255,255,0.88);
  line-height: 1.35;
  margin: 0 0 10px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Chips */
.q3-chips{
  display:flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.q3-chip{
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.84);
}

/* Relevance */
.q3-rel-wrap{
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 10px;
  margin: 10px 0 10px 0;
}
.q3-rel-label{
  font-size: 12px;
  color: rgba(255,255,255,0.70);
  white-space: nowrap;
}
.q3-rel-bar{
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
}
.q3-rel-fill{
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255,255,255,0.35), rgba(255,255,255,0.75));
}
.q3-rel-badge{
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.86);
  white-space: nowrap;
}

/* Actions */
.q3-actions{
  display:flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.q3-btn{
  display:inline-block;
  text-decoration:none;
  font-size: 12.5px;
  font-weight: 700;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.92);
}
.q3-btn:hover{
  border-color: rgba(255,255,255,0.22);
  background: rgba(255,255,255,0.09);
}

/* Micro meta */
.q3-micro{
  margin-top: 6px;
  font-size: 12px;
  color: rgba(255,255,255,0.65);
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
"""


# ------------------------------
# Helpers
# ------------------------------
def _get_domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").replace("www.", "")
    except Exception:
        return ""


def _favicon_url(domain: str) -> str:
    if not domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"


def _fmt_conf(conf: Optional[Any]) -> Optional[str]:
    try:
        if conf is None:
            return None
        return f"{float(conf):.2f}"
    except Exception:
        return None


def _safe_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _risk_rank(risk: Optional[str]) -> int:
    r = (risk or "").lower()
    if r == "high":
        return 3
    if r == "medium":
        return 2
    return 1


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _chip(label: str) -> str:
    return f'<span class="q3-chip">{label}</span>'


def _entity_icon(entity_type: str) -> str:
    et = (entity_type or "").lower()
    if et in ("profile", "person"):
        return "👤"
    if et in ("company",):
        return "🏢"
    if et in ("repo", "issue"):
        return "💻"
    if et in ("paste",):
        return "🧪"
    if et in ("document",):
        return "📄"
    if et in ("forum", "community"):
        return "💬"
    if et in ("news",):
        return "📰"
    if et in ("event",):
        return "📅"
    if et in ("post",):
        return "🧩"
    if et in ("dork",):
        return "🔎"
    return "🔎"


def _risk_icon(risk: str) -> str:
    r = (risk or "").lower()
    if r == "high":
        return "🔴"
    if r == "medium":
        return "🟠"
    return "🟢"


def _match_icon(mt: str) -> str:
    m = (mt or "").lower()
    if m == "exact":
        return "🎯"
    if m == "partial":
        return "≈"
    return "🧩"


def _relevance_label(score: int) -> str:
    if score >= 80:
        return "Alta"
    if score >= 55:
        return "Media"
    return "Baja"


def _card_html(card: Dict[str, Any]) -> str:
    title = (card.get("title") or "Sin título").strip()
    url = (card.get("url") or "#").strip()
    snippet = (card.get("snippet") or "").strip()

    source = card.get("source")
    engine = card.get("engine")
    confidence = _fmt_conf(card.get("confidence"))

    entity_type = card.get("entity_type") or "unknown"
    match_type = card.get("match_type") or "contextual"
    relevance = _safe_int(card.get("relevance_score"), default=0) or 0
    risk_level = card.get("risk_level") or "low"
    published_at = card.get("published_at")
    location_hint = card.get("location_hint")

    domain = _get_domain(url)
    fav = _favicon_url(domain)

    chips = [
        _chip(f"{_entity_icon(entity_type)} {entity_type}"),
        _chip(f"{_match_icon(match_type)} {match_type}"),
        _chip(f"{_risk_icon(risk_level)} risk:{risk_level}"),
    ]
    if source:
        chips.append(_chip(f"src:{source}"))
    if engine:
        chips.append(_chip(f"eng:{engine}"))
    if confidence:
        chips.append(_chip(f"conf:{confidence}"))

    chips_html = "".join(chips)

    rel_pct = max(0, min(100, relevance))
    rel_lbl = _relevance_label(rel_pct)

    micro_bits = []
    if published_at:
        micro_bits.append(f"🕒 {published_at}")
    if location_hint:
        micro_bits.append(f"📍 {location_hint}")
    micro_html = " ".join([f"<span>{b}</span>" for b in micro_bits]) if micro_bits else ""

    return f"""
      <div class="q3-card">
        <div class="q3-title">{title}</div>

        <div class="q3-domain-row">
          {("<img class='q3-favicon' src='" + fav + "' />") if fav else ""}
          <div>{domain or "—"}</div>
        </div>

        <div class="q3-snippet">{snippet}</div>

        <div class="q3-chips">{chips_html}</div>

        <div class="q3-rel-wrap">
          <div class="q3-rel-label">Relevancia</div>
          <div class="q3-rel-bar"><div class="q3-rel-fill" style="width:{rel_pct}%"></div></div>
          <div class="q3-rel-badge">{rel_lbl} • {rel_pct}</div>
        </div>

        {("<div class='q3-micro'>" + micro_html + "</div>") if micro_html else ""}

        <div class="q3-actions">
          <a class="q3-btn" href="{url}" target="_blank" rel="noopener noreferrer">Abrir</a>
        </div>
      </div>
    """


def _flatten_dorks_results(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flat: List[Dict[str, Any]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue

        pattern = entry.get("pattern") or entry.get("title") or "Dork"
        q_used = entry.get("query") or entry.get("query_used") or ""
        source = entry.get("source") or "google_dorks"
        engine = entry.get("engine")
        confidence = entry.get("confidence")

        sub = entry.get("results")
        if isinstance(sub, list) and sub:
            for hit in sub:
                if not isinstance(hit, dict):
                    continue
                flat.append({
                    "title": hit.get("title") or "Sin título",
                    "url": hit.get("url") or hit.get("link") or "#",
                    "snippet": hit.get("snippet") or "",
                    "source": hit.get("source") or source,
                    "engine": hit.get("engine") or engine,
                    "confidence": hit.get("confidence") if hit.get("confidence") is not None else confidence,

                    # enriquecido (si existe)
                    "entity_type": hit.get("entity_type"),
                    "match_type": hit.get("match_type"),
                    "relevance_score": hit.get("relevance_score"),
                    "published_at": hit.get("published_at"),
                    "location_hint": hit.get("location_hint"),
                    "risk_level": hit.get("risk_level"),
                    "linked_to_profile": hit.get("linked_to_profile"),

                    # meta técnico
                    "query_used": q_used,
                    "pattern": pattern,
                })
    return flat


def _render_attempted_dorks_table(diag_entries: List[Dict[str, Any]]):
    if not diag_entries:
        return

    st.caption(f"Dorks intentados: {len(diag_entries)} (diagnóstico)")

    # UI compacta, sin romper el flujo
    for e in diag_entries[:50]:  # límite para no petar UI si hay muchos
        if not isinstance(e, dict):
            continue
        pat = (e.get("pattern") or "—").strip()
        q = (e.get("query") or "—").strip()
        eng = e.get("engine") or "—"
        hint = e.get("no_results_hint") or "—"
        gurl = e.get("google_url") or e.get("url")

        with st.expander(f"🔎 {pat} • eng={eng} • hint={hint}", expanded=False):
            st.caption("Consulta ejecutada")
            st.code(q)
            if gurl:
                st.markdown(f"[Abrir en navegador]({gurl})")
            st.caption("Métricas")
            st.json({
                "raw_hits_count": e.get("raw_hits_count"),
                "filtered_out": e.get("filtered_out"),
                "subresults_count": e.get("subresults_count"),
                "engine": eng,
                "hint": hint,
            })


def render_dorks_block(dorks_block: Dict[str, Any]):
    if not isinstance(dorks_block, dict):
        return

    st.markdown(_DORKS_CSS, unsafe_allow_html=True)
    st.markdown("### 🕵️‍♂️ Google Dorks")

    for err in dorks_block.get("errors") or []:
        st.warning(f"Dorks: {err}")

    entries = dorks_block.get("results") or []
    cards = _flatten_dorks_results(entries)

    if not cards:
        st.info(
            "No se encontraron **hits reales** para los dorks ejecutados.\n\n"
            "Posibles causas comunes:\n"
            "- El motor (DDG/Google) está bloqueando o limitando\n"
            "- `only_with_hits=True` descarta dorks sin resultados\n"
            "- La consulta es muy específica o poco indexada\n"
            "- Red/DNS/proxy (en tus logs aparece fallo de resolución)\n"
        )

        meta_bits = []
        dorks_file = dorks_block.get("dorks_file")
        if dorks_file:
            meta_bits.append(f"📄 dorks_file: `{dorks_file}`")
        used = dorks_block.get("query")
        if used:
            meta_bits.append(f"🔎 query: `{used}`")
        if meta_bits:
            st.caption(" | ".join(meta_bits))

        diag_entries = dorks_block.get("diagnostic") or []
        if diag_entries:
            st.markdown("#### 🔧 Diagnóstico (qué se intentó)")
            _render_attempted_dorks_table(diag_entries)
        else:
            with st.expander("🔧 Diagnóstico (raw)", expanded=False):
                st.json(dorks_block)
        return

    # Ordenación PRO
    def _sort_key(c: Dict[str, Any]):
        rel = _safe_int(c.get("relevance_score"), default=0) or 0
        risk = _risk_rank(c.get("risk_level"))
        conf = _to_float(c.get("confidence"), 0.0)
        dom = _get_domain((c.get("url") or "").strip())
        return (-rel, -risk, -conf, dom)

    cards.sort(key=_sort_key)

    st.caption(f"{len(cards)} resultados extraídos (ordenados por relevancia/riesgo/confianza)")

    # ✅ Grid HTML (como general_search)
    html_cards = "\n".join([_card_html(c) for c in cards])
    st.markdown(f'<div class="q3-grid">{html_cards}</div>', unsafe_allow_html=True)

    # ✅ Detalles técnicos (separado, no rompe el grid)
    with st.expander("🧷 Detalles técnicos (por resultado)", expanded=False):
        for i, c in enumerate(cards[:50], start=1):
            st.markdown(f"**#{i}** {c.get('title')}")
            if c.get("pattern"):
                st.caption("Dork / patrón")
                st.code(c.get("pattern"))
            if c.get("query_used"):
                st.caption("Consulta ejecutada")
                st.code(c.get("query_used"))
            st.caption("URL")
            st.code(c.get("url"))
            st.markdown("---")
import streamlit as st
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


# ------------------------------
# CSS: look profesional
# ------------------------------
_DORKS_CSS = """
<style>
/* Layout responsive */
.q3-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 900px) {
  .q3-grid { grid-template-columns: 1fr; }
}

/* Card */
.q3-card {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 14px 14px 12px 14px;
  background: rgba(255,255,255,0.03);
  box-shadow: 0 10px 26px rgba(0,0,0,0.22);
  transition: transform .08s ease, border-color .08s ease, background .08s ease;
}
.q3-card:hover{
  transform: translateY(-1px);
  border-color: rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.04);
}

/* Title */
.q3-title {
  font-size: 15.5px;
  font-weight: 700;
  margin: 0 0 6px 0;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Domain row */
.q3-domain-row{
  display:flex;
  align-items:center;
  gap:8px;
  color: rgba(255,255,255,0.70);
  font-size: 12.5px;
  margin-bottom: 10px;
}
.q3-favicon{
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  padding: 2px;
}

/* Snippet */
.q3-snippet{
  font-size: 13.5px;
  color: rgba(255,255,255,0.88);
  line-height: 1.35;
  margin: 0 0 10px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Chips */
.q3-chips{
  display:flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.q3-chip{
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.84);
}

/* Relevance */
.q3-rel-wrap{
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 10px;
  margin: 10px 0 10px 0;
}
.q3-rel-label{
  font-size: 12px;
  color: rgba(255,255,255,0.70);
  white-space: nowrap;
}
.q3-rel-bar{
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
}
.q3-rel-fill{
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255,255,255,0.35), rgba(255,255,255,0.75));
}
.q3-rel-badge{
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.86);
  white-space: nowrap;
}

/* Actions */
.q3-actions{
  display:flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
.q3-btn{
  display:inline-block;
  text-decoration:none;
  font-size: 12.5px;
  font-weight: 700;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.92);
}
.q3-btn:hover{
  border-color: rgba(255,255,255,0.22);
  background: rgba(255,255,255,0.09);
}

/* Micro meta */
.q3-micro{
  margin-top: 6px;
  font-size: 12px;
  color: rgba(255,255,255,0.65);
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
"""


# ------------------------------
# Helpers
# ------------------------------
def _get_domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").replace("www.", "")
    except Exception:
        return ""


def _favicon_url(domain: str) -> str:
    if not domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"


def _fmt_conf(conf: Optional[Any]) -> Optional[str]:
    try:
        if conf is None:
            return None
        return f"{float(conf):.2f}"
    except Exception:
        return None


def _safe_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _risk_rank(risk: Optional[str]) -> int:
    r = (risk or "").lower()
    if r == "high":
        return 3
    if r == "medium":
        return 2
    return 1


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _chip(label: str) -> str:
    return f'<span class="q3-chip">{label}</span>'


def _entity_icon(entity_type: str) -> str:
    et = (entity_type or "").lower()
    if et in ("profile", "person"):
        return "👤"
    if et in ("company",):
        return "🏢"
    if et in ("repo", "issue"):
        return "💻"
    if et in ("paste",):
        return "🧪"
    if et in ("document",):
        return "📄"
    if et in ("forum", "community"):
        return "💬"
    if et in ("news",):
        return "📰"
    if et in ("event",):
        return "📅"
    if et in ("post",):
        return "🧩"
    if et in ("dork",):
        return "🔎"
    return "🔎"


def _risk_icon(risk: str) -> str:
    r = (risk or "").lower()
    if r == "high":
        return "🔴"
    if r == "medium":
        return "🟠"
    return "🟢"


def _match_icon(mt: str) -> str:
    m = (mt or "").lower()
    if m == "exact":
        return "🎯"
    if m == "partial":
        return "≈"
    return "🧩"


def _relevance_label(score: int) -> str:
    if score >= 80:
        return "Alta"
    if score >= 55:
        return "Media"
    return "Baja"


def _card_html(card: Dict[str, Any]) -> str:
    title = (card.get("title") or "Sin título").strip()
    url = (card.get("url") or "#").strip()
    snippet = (card.get("snippet") or "").strip()

    source = card.get("source")
    engine = card.get("engine")
    confidence = _fmt_conf(card.get("confidence"))

    entity_type = card.get("entity_type") or "unknown"
    match_type = card.get("match_type") or "contextual"
    relevance = _safe_int(card.get("relevance_score"), default=0) or 0
    risk_level = card.get("risk_level") or "low"
    published_at = card.get("published_at")
    location_hint = card.get("location_hint")

    domain = _get_domain(url)
    fav = _favicon_url(domain)

    chips = [
        _chip(f"{_entity_icon(entity_type)} {entity_type}"),
        _chip(f"{_match_icon(match_type)} {match_type}"),
        _chip(f"{_risk_icon(risk_level)} risk:{risk_level}"),
    ]
    if source:
        chips.append(_chip(f"src:{source}"))
    if engine:
        chips.append(_chip(f"eng:{engine}"))
    if confidence:
        chips.append(_chip(f"conf:{confidence}"))

    chips_html = "".join(chips)

    rel_pct = max(0, min(100, relevance))
    rel_lbl = _relevance_label(rel_pct)

    micro_bits = []
    if published_at:
        micro_bits.append(f"🕒 {published_at}")
    if location_hint:
        micro_bits.append(f"📍 {location_hint}")
    micro_html = " ".join([f"<span>{b}</span>" for b in micro_bits]) if micro_bits else ""

    return f"""
      <div class="q3-card">
        <div class="q3-title">{title}</div>

        <div class="q3-domain-row">
          {("<img class='q3-favicon' src='" + fav + "' />") if fav else ""}
          <div>{domain or "—"}</div>
        </div>

        <div class="q3-snippet">{snippet}</div>

        <div class="q3-chips">{chips_html}</div>

        <div class="q3-rel-wrap">
          <div class="q3-rel-label">Relevancia</div>
          <div class="q3-rel-bar"><div class="q3-rel-fill" style="width:{rel_pct}%"></div></div>
          <div class="q3-rel-badge">{rel_lbl} • {rel_pct}</div>
        </div>

        {("<div class='q3-micro'>" + micro_html + "</div>") if micro_html else ""}

        <div class="q3-actions">
          <a class="q3-btn" href="{url}" target="_blank" rel="noopener noreferrer">Abrir</a>
        </div>
      </div>
    """


def _flatten_dorks_results(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flat: List[Dict[str, Any]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue

        pattern = entry.get("pattern") or entry.get("title") or "Dork"
        q_used = entry.get("query") or entry.get("query_used") or ""
        source = entry.get("source") or "google_dorks"
        engine = entry.get("engine")
        confidence = entry.get("confidence")

        sub = entry.get("results")
        if isinstance(sub, list) and sub:
            for hit in sub:
                if not isinstance(hit, dict):
                    continue
                flat.append({
                    "title": hit.get("title") or "Sin título",
                    "url": hit.get("url") or hit.get("link") or "#",
                    "snippet": hit.get("snippet") or "",
                    "source": hit.get("source") or source,
                    "engine": hit.get("engine") or engine,
                    "confidence": hit.get("confidence") if hit.get("confidence") is not None else confidence,

                    # enriquecido (si existe)
                    "entity_type": hit.get("entity_type"),
                    "match_type": hit.get("match_type"),
                    "relevance_score": hit.get("relevance_score"),
                    "published_at": hit.get("published_at"),
                    "location_hint": hit.get("location_hint"),
                    "risk_level": hit.get("risk_level"),
                    "linked_to_profile": hit.get("linked_to_profile"),

                    # meta técnico
                    "query_used": q_used,
                    "pattern": pattern,
                })
    return flat


def _render_attempted_dorks_table(diag_entries: List[Dict[str, Any]]):
    if not diag_entries:
        return

    st.caption(f"Dorks intentados: {len(diag_entries)} (diagnóstico)")

    # UI compacta, sin romper el flujo
    for e in diag_entries[:50]:  # límite para no petar UI si hay muchos
        if not isinstance(e, dict):
            continue
        pat = (e.get("pattern") or "—").strip()
        q = (e.get("query") or "—").strip()
        eng = e.get("engine") or "—"
        hint = e.get("no_results_hint") or "—"
        gurl = e.get("google_url") or e.get("url")

        with st.expander(f"🔎 {pat} • eng={eng} • hint={hint}", expanded=False):
            st.caption("Consulta ejecutada")
            st.code(q)
            if gurl:
                st.markdown(f"[Abrir en navegador]({gurl})")
            st.caption("Métricas")
            st.json({
                "raw_hits_count": e.get("raw_hits_count"),
                "filtered_out": e.get("filtered_out"),
                "subresults_count": e.get("subresults_count"),
                "engine": eng,
                "hint": hint,
            })


def render_dorks_block(dorks_block: Dict[str, Any]):
    if not isinstance(dorks_block, dict):
        return

    st.markdown(_DORKS_CSS, unsafe_allow_html=True)
    st.markdown("### 🕵️‍♂️ Google Dorks")

    for err in dorks_block.get("errors") or []:
        st.warning(f"Dorks: {err}")

    entries = dorks_block.get("results") or []
    cards = _flatten_dorks_results(entries)

    if not cards:
        st.info(
            "No se encontraron **hits reales** para los dorks ejecutados.\n\n"
            "Posibles causas comunes:\n"
            "- El motor (DDG/Google) está bloqueando o limitando\n"
            "- `only_with_hits=True` descarta dorks sin resultados\n"
            "- La consulta es muy específica o poco indexada\n"
            "- Red/DNS/proxy (en tus logs aparece fallo de resolución)\n"
        )

        meta_bits = []
        dorks_file = dorks_block.get("dorks_file")
        if dorks_file:
            meta_bits.append(f"📄 dorks_file: `{dorks_file}`")
        used = dorks_block.get("query")
        if used:
            meta_bits.append(f"🔎 query: `{used}`")
        if meta_bits:
            st.caption(" | ".join(meta_bits))

        diag_entries = dorks_block.get("diagnostic") or []
        if diag_entries:
            st.markdown("#### 🔧 Diagnóstico (qué se intentó)")
            _render_attempted_dorks_table(diag_entries)
        else:
            with st.expander("🔧 Diagnóstico (raw)", expanded=False):
                st.json(dorks_block)
        return

    # Ordenación PRO
    def _sort_key(c: Dict[str, Any]):
        rel = _safe_int(c.get("relevance_score"), default=0) or 0
        risk = _risk_rank(c.get("risk_level"))
        conf = _to_float(c.get("confidence"), 0.0)
        dom = _get_domain((c.get("url") or "").strip())
        return (-rel, -risk, -conf, dom)

    cards.sort(key=_sort_key)

    st.caption(f"{len(cards)} resultados extraídos (ordenados por relevancia/riesgo/confianza)")

    # ✅ Grid HTML (como general_search)
    html_cards = "\n".join([_card_html(c) for c in cards])
    st.markdown(f'<div class="q3-grid">{html_cards}</div>', unsafe_allow_html=True)

    # ✅ Detalles técnicos (separado, no rompe el grid)
    with st.expander("🧷 Detalles técnicos (por resultado)", expanded=False):
        for i, c in enumerate(cards[:50], start=1):
            st.markdown(f"**#{i}** {c.get('title')}")
            if c.get("pattern"):
                st.caption("Dork / patrón")
                st.code(c.get("pattern"))
            if c.get("query_used"):
                st.caption("Consulta ejecutada")
                st.code(c.get("query_used"))
            st.caption("URL")
            st.code(c.get("url"))
            st.markdown("---")
