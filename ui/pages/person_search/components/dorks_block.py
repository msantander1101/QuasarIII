import streamlit as st
from typing import Any, Dict, List, Optional
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
        ">{text}</span>
        """,
        unsafe_allow_html=True,
    )


def _hit_card(hit: Dict[str, Any]):
    title = hit.get("title") or hit.get("name") or "Sin título"
    url = hit.get("url") or hit.get("link") or ""
    snippet = hit.get("snippet") or hit.get("description") or ""
    source = hit.get("source") or "motor"
    conf = hit.get("confidence")

    with st.container(border=True):
        cols = st.columns([0.82, 0.18])
        with cols[0]:
            st.markdown(f"**{title}**")
            if url:
                st.caption(f"{_host(url)}")
        with cols[1]:
            _badge(str(source))
            if conf is not None:
                _badge(f"conf {conf}")

        if snippet:
            st.write(snippet)

        # En vez de link feo, un botón “Abrir”
        if url:
            st.link_button("Abrir resultado", url, use_container_width=True)


def _dork_card(entry: Dict[str, Any]):
    pattern = entry.get("pattern") or entry.get("title") or "Dork"
    google_url = entry.get("google_url") or entry.get("url") or ""
    dork_query = entry.get("query") or ""
    desc = entry.get("description") or ""
    confidence = entry.get("confidence", None)

    subresults = entry.get("results") if isinstance(entry.get("results"), list) else []
    hits_count = len(subresults)

    with st.container(border=True):
        top = st.columns([0.75, 0.25])

        with top[0]:
            st.markdown(f"### {pattern}")
            st.caption(dork_query if dork_query else "Consulta vacía")

        with top[1]:
            _badge(f"hits {hits_count}")
            if confidence is not None:
                _badge(f"base {confidence}")

        if desc:
            st.write(desc)

        # CTA principal
        if google_url:
            st.link_button("Abrir búsqueda", google_url, use_container_width=True)

        # Resultados extraídos (si existen)
        if subresults:
            st.markdown("**Resultados extraídos**")
            for hit in subresults:
                if isinstance(hit, dict):
                    _hit_card(hit)
        else:
            st.info("Sin extracción automática en esta ejecución (puedes abrir la búsqueda para investigar manualmente).")


def render_dorks_block(dorks_block: Dict[str, Any]):
    st.markdown("## 🕵️‍♂️ Google Dorks")

    if not isinstance(dorks_block, dict):
        st.info("No hay resultados de dorks")
        return

    # Trazabilidad
    dorks_file = dorks_block.get("dorks_file")
    if dorks_file:
        st.caption(f"📄 Listado de dorks: `{dorks_file}`")

    for err in dorks_block.get("errors") or []:
        st.warning(f"Dorks: {err}")

    results = dorks_block.get("results") or []
    if not results:
        st.info("No hay resultados de dorks")
        return

    active_hits = [r for r in results if isinstance(r, dict) and r.get("results")]
    empty_hits = [r for r in results if isinstance(r, dict) and not r.get("results")]

    total_links = sum(len(r.get("results") or []) for r in active_hits)
    st.caption(
        f"{len(active_hits)} dorks con hallazgos • {total_links} enlaces extraídos • {len(empty_hits)} sin extracción"
    )

    # Pinta todo en cards (primero los que tienen hits)
    if active_hits:
        st.markdown("### ✅ Hallazgos")
        for entry in active_hits:
            _dork_card(entry)

    if empty_hits:
        st.markdown("### 🔎 Sin extracción (pero útiles)")
        with st.expander("Ver dorks ejecutados", expanded=False):
            for entry in empty_hits:
                _dork_card(entry)
