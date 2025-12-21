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


def _render_verification(verification: dict):
    if not verification:
        return

    deliverable = verification.get("deliverable", "unknown")
    reason = verification.get("reason")

    status_label = {
        True: "Entregable",
        False: "No entregable",
        "unknown": "Sin comprobar"
    }.get(deliverable, "Sin comprobar")

    msg = f"**Estado de entrega**: {status_label}"
    if reason:
        msg += f" — Motivo: {reason}"

    st.markdown(msg)


def _render_sources(sources: dict):
    if not sources:
        return

    st.markdown("**Fuentes OSINT**")

    groups = [
        ("Generación de leads", sources.get("lead_generation", [])),
        ("Información de email", sources.get("email_info", [])),
        ("Verificación", sources.get("verification", [])),
    ]

    for label, items in groups:
        if not items:
            continue

        st.markdown(f"*{label}*")
        for item in items:
            name = item.get("name", "Fuente")
            url = item.get("url", "#")
            st.markdown(f"- [{name}]({url})")


def render_email_block(email_block: dict):
    st.markdown("### 📧 Emails")

    if not isinstance(email_block, dict):
        st.info("No hay resultados de email")
        return

    errors = email_block.get("errors") or []
    for err in errors:
        st.warning(f"Email: {err}")

    results = email_block.get("results")
    if not results:
        st.info("No hay resultados de email")
        return

    for e in results:
        if not isinstance(e, dict):
            continue

        email_value = e.get("email", "N/A")
        st.markdown(f"#### {email_value}")

        hibp_data = e.get("hibp")
        if hibp_data:
            _render_hibp(hibp_data)

        ghunt_data = e.get("ghunt")
        if ghunt_data:
            _render_ghunt(ghunt_data)

        verification_data = e.get("verification")
        if verification_data:
            _render_verification(verification_data)

        source_links = e.get("sources")
        if source_links:
            _render_sources(source_links)

        st.markdown("---")


def render_web_block(web_block: dict):
    if not web_block:
        return

    st.markdown("### 🌍 Resultados Web")

    results = web_block.get("results") if isinstance(web_block, dict) else []
    for item in results:
        if not isinstance(item, dict):
            continue

        title = item.get("title") or item.get("name") or "Sin título"
        url = item.get("url") or item.get("link") or "#"
        snippet = item.get("snippet", "")
        st.markdown(f"- [{title}]({url}) — {snippet}")
