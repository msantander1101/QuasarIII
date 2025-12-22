import streamlit as st
from typing import Any, Dict, List


def _render_subresults(subresults: List[Dict[str, Any]]):
    if not subresults:
        st.caption("Sin resultados devueltos por el motor; abre el dork en tu navegador para investigar manualmente.")
        return

    with st.expander(f"Ver resultados ({len(subresults)})", expanded=False):
        for hit in subresults:
            if not isinstance(hit, dict):
                continue

            title = hit.get("title") or hit.get("name") or "Sin título"
            url = hit.get("url") or hit.get("link") or "#"
            snippet = hit.get("snippet") or hit.get("description") or ""
            source = hit.get("source")
            confidence = hit.get("confidence")

            meta_bits = []
            if source:
                meta_bits.append(str(source))
            if confidence:
                meta_bits.append(f"conf: {confidence}")
            meta = f" ({', '.join(meta_bits)})" if meta_bits else ""

            st.markdown(f"- [{title}]({url}){meta}\n    \n    {snippet}")


def render_dorks_block(dorks_block: Dict[str, Any]):
    st.markdown("### 🕵️‍♂️ Google Dorks")

    if not isinstance(dorks_block, dict):
        st.info("No hay resultados de dorks")
        return

    for err in dorks_block.get("errors") or []:
        st.warning(f"Dorks: {err}")

    results = dorks_block.get("results") or []
    if not results:
        st.info("No hay resultados de dorks")
        return

    for entry in results:
        if not isinstance(entry, dict):
            continue

        pattern = entry.get("pattern") or entry.get("title") or "Dork"
        google_url = entry.get("google_url") or entry.get("url") or "#"
        dork_query = entry.get("query") or ""
        confidence = entry.get("confidence")
        desc = entry.get("description") or ""
        subresults = entry.get("results") if isinstance(entry.get("results"), list) else []

        st.markdown(f"**{pattern}**")
        st.caption(f"Consulta: `{dork_query}`")
        st.markdown(f"[Abrir en Google]({google_url})")

        if desc:
            st.write(desc)

        if confidence is not None:
            st.caption(f"Confianza: {confidence}")

        _render_subresults(subresults)
        st.markdown("---")
