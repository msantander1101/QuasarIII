import streamlit as st

def _render_hibp(hibp: dict):
    if not hibp:
        st.info("No se pudieron cargar datos de HIBP")
        return

    if hibp.get("error"):
        st.warning(f"HIBP: {hibp.get('error')}")
        return

    breached = hibp.get("breached")
    breach_count = hibp.get("breach_count", 0)
    st.markdown(f"**Breaches**: {'Sí' if breached else 'No'} | **Total**: {breach_count}")


def _render_ghunt(ghunt: dict):
    if not ghunt:
        st.info("GHunt sin datos")
        return

    if not ghunt.get("success"):
        st.warning(f"GHunt: {ghunt.get('error', 'ejecución no exitosa')}")
        return

    output = ghunt.get("output") or "(sin salida capturada)"
    with st.expander("Ver salida GHunt cruda", expanded=False):
        st.code(output, language="text")


def render_email_block(email_block: dict):
    if not email_block:
        return
    st.markdown("### 📧 Emails")
    results = email_block.get("results") if isinstance(email_block, dict) else None
    if not results:
        st.info("No hay resultados de email")
        return

    for e in results:
        email_value = e.get("email", "N/A") if isinstance(e, dict) else "N/A"
        st.markdown(f"#### {email_value}")

        hibp_data = e.get("hibp") if isinstance(e, dict) else None
        if hibp_data:
            _render_hibp(hibp_data)

        ghunt_data = e.get("ghunt") if isinstance(e, dict) else None
        if ghunt_data:
            _render_ghunt(ghunt_data)

        st.markdown("---")




def render_web_block(web_block: dict):
    if not web_block:
        return
    st.markdown("### 🌍 Resultados Web")
    results = web_block.get("results") if isinstance(web_block, dict) else []
    for item in results:
        title = item.get('title') or item.get('name') or 'Sin título'
        url = item.get('url') or item.get('link') or '#'
        snippet = item.get('snippet', '')
        st.markdown(f"- [{title}]({url}) — {snippet}")
