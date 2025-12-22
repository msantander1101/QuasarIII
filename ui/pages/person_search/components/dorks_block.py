import streamlit as st
from typing import Any, Dict, List


def _render_subresults(subresults: List[Dict[str, Any]]):
    if not subresults:
        st.caption(
            "Sin resultados devueltos por el motor en esta ejecución; abre el dork en tu navegador para investigar manualmente."
        )
        return

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

        st.markdown(
            f"- **[{title}]({url})**{meta}\n"
            f"  \n  <small>{snippet}</small>",
            unsafe_allow_html=True,
        )


def render_dorks_block(dorks_block: Dict[str, Any]):
    st.markdown("### 🕵️‍♂️ Google Dorks (búsqueda activa)")

    if not isinstance(dorks_block, dict):
        st.info("No hay resultados de dorks")
        return

    for err in dorks_block.get("errors") or []:
        st.warning(f"Dorks: {err}")

    results = dorks_block.get("results") or []
    active_hits = [r for r in results if isinstance(r, dict) and r.get("results")]
    empty_hits = [r for r in results if isinstance(r, dict) and not r.get("results")]

    total_links = sum(len(r.get("results") or []) for r in active_hits)
    st.caption(
        f"{len(active_hits)} dorks con hallazgos • {total_links} enlaces extraídos • {len(empty_hits)} sin hits directos"
    )

    if not results:
        st.info("No hay resultados de dorks")
        return

    if active_hits:
        st.markdown("#### Resultados obtenidos ahora")
        for entry in active_hits:
            pattern = entry.get("pattern") or entry.get("title") or "Dork"
            google_url = entry.get("google_url") or entry.get("url") or "#"
            dork_query = entry.get("query") or ""
            desc = entry.get("description") or ""
            subresults = entry.get("results") if isinstance(entry.get("results"), list) else []

            st.markdown(f"**{pattern}**")
            st.caption(f"Consulta ejecutada: `{dork_query}`")
            st.markdown(f"[Abrir en Google]({google_url})")

            if desc:
                st.write(desc)

            _render_subresults(subresults)
            st.markdown("---")

    if empty_hits:
        with st.expander("Dorks sin resultados directos en esta ejecución", expanded=False):
            for entry in empty_hits:
                pattern = entry.get("pattern") or entry.get("title") or "Dork"
                google_url = entry.get("google_url") or entry.get("url") or "#"
                dork_query = entry.get("query") or ""
                confidence = entry.get("confidence")

                st.markdown(f"**{pattern}**")
                st.caption(f"Consulta ejecutada: `{dork_query}`")
                st.markdown(f"[Abrir en Google]({google_url})")

                if confidence is not None:
                    st.caption(f"Confianza base: {confidence}")
