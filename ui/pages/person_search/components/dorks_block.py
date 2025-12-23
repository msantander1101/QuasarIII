import streamlit as st
from typing import Any, Dict, List
from urllib.parse import urlparse


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def _badge(text: str):
    st.markdown(
        f"""
        <span style="
            display:inline-block;
            padding:2px 10px;
            border-radius:999px;
            background:rgba(0,0,0,0.06);
            font-size:12px;
            margin-right:6px;
            margin-bottom:6px;
        ">{text}</span>
        """,
        unsafe_allow_html=True,
    )


def _hit_card(hit: Dict[str, Any]):
    title = hit.get("title") or hit.get("name") or "Sin título"
    url = hit.get("url") or hit.get("link") or ""
    snippet = hit.get("snippet") or hit.get("description") or ""
    source = hit.get("source") or "motor"
    engine = hit.get("engine")
    conf = hit.get("confidence")

    with st.container(border=True):
        st.markdown(f"**{title}**")
        if url:
            st.caption(_host(url))

        _badge(str(source))
        if engine:
            _badge(str(engine))
        if conf is not None:
            _badge(f"conf {conf}")

        if snippet:
            st.write(snippet)

        if url:
            st.link_button("Abrir resultado", url, use_container_width=True)


def _dork_card(entry: Dict[str, Any]):
    pattern = entry.get("pattern") or entry.get("title") or "Dork"
    google_url = entry.get("google_url") or entry.get("url") or ""
    dork_query = entry.get("query") or ""
    desc = entry.get("description") or ""

    confidence = entry.get("confidence")
    engine = entry.get("engine") or "unknown"
    engine_has_key = entry.get("engine_has_key", False)
    subcount = entry.get("subresults_count")
    limit_used = entry.get("limit_used")
    hint = entry.get("no_results_hint")

    subresults = entry.get("results") if isinstance(entry.get("results"), list) else []

    with st.container(border=True):
        st.markdown(f"### {pattern}")
        if dork_query:
            st.caption(dork_query)

        _badge(f"engine: {engine}")
        _badge("SERP ✅" if engine_has_key else "SERP ❌ (sin key)")
        if subcount is not None:
            _badge(f"hits: {subcount}")
        else:
            _badge(f"hits: {len(subresults)}")
        if limit_used is not None:
            _badge(f"lim: {limit_used}")
        if confidence is not None:
            _badge(f"base: {confidence}")

        if desc:
            st.write(desc)

        if google_url:
            st.link_button("Abrir búsqueda", google_url, use_container_width=True)

        if subresults:
            st.markdown("**Resultados extraídos**")
            for hit in subresults:
                if isinstance(hit, dict):
                    _hit_card(hit)
        else:
            # Mensaje pro según hint
            if hint == "serpapi_no_results":
                st.info("Google/SerpAPI no devuelve resultados para este dork (normal en algunos targets). Prueba pivots más amplios o apóyate en fuentes de leaks (HIBP).")
            elif hint == "no_serp_hits_or_filtered":
                st.info("Sin resultados SERP para este dork (o filtrados por site:). Prueba dorks más amplios/pivots o usa fuentes de leaks (HIBP).")
            else:
                st.info("Sin extracción automática en esta ejecución.")


def render_dorks_block(dorks_block: Dict[str, Any]):
    st.markdown("## 🕵️‍♂️ Google Dorks")

    if not isinstance(dorks_block, dict):
        st.info("No hay resultados de dorks")
        return

    dorks_file = dorks_block.get("dorks_file")
    if dorks_file:
        st.caption(f"📄 Listado de dorks: `{dorks_file}`")

    for err in dorks_block.get("errors") or []:
        st.warning(f"Dorks: {err}")

    results = dorks_block.get("results") or []
    if not results:
        st.info("No hay resultados de dorks")
        return

    # ✅ Deduplicar por (query, pattern)
    seen = set()
    unique_results: List[Dict[str, Any]] = []
    for r in results:
        if not isinstance(r, dict):
            continue
        key = (r.get("query"), r.get("pattern"))
        if key in seen:
            continue
        seen.add(key)
        unique_results.append(r)
    results = unique_results

    active_hits = [r for r in results if isinstance(r, dict) and r.get("results")]
    empty_hits = [r for r in results if isinstance(r, dict) and not r.get("results")]

    total_links = sum(len(r.get("results") or []) for r in active_hits)
    st.caption(
        f"{len(active_hits)} dorks con hallazgos • {total_links} enlaces extraídos • {len(empty_hits)} sin extracción"
    )

    def render_grid(items: List[Dict[str, Any]]):
        cols = st.columns(2)
        for idx, entry in enumerate(items):
            with cols[idx % 2]:
                _dork_card(entry)

    if active_hits:
        st.markdown("### ✅ Hallazgos")
        render_grid(active_hits)

    if empty_hits:
        st.markdown("### 🔎 Sin extracción (pero útiles)")
        with st.expander("Ver dorks ejecutados", expanded=False):
            render_grid(empty_hits)
