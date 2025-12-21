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

    # cuando se “skippea” por no ser gmail
    if ghunt.get("skipped"):
        st.info(f"GHunt: {ghunt.get('skipped')}")
        return

    if not ghunt.get("success"):
        st.warning(f"GHunt: {ghunt.get('error', 'ejecución no exitosa')}")
        return

    output = ghunt.get("output") or "(sin salida capturada)"
    warnings = ghunt.get("warnings") or []
    if warnings:
        for w in warnings:
            st.warning(w)

    with st.expander("Ver salida GHunt cruda", expanded=False):
        st.code(output, language="text")


def _render_emailfinder(emailfinder: dict):
    if not emailfinder:
        return

    if not emailfinder.get("success"):
        error_msg = emailfinder.get("error") or emailfinder.get("stderr") or "Ejecución fallida"
        st.warning(f"EmailFinder: {error_msg}")

        command = emailfinder.get("command")
        if command:
            st.code(command, language="bash")

        install = emailfinder.get("install")
        if install:
            st.info("Instala EmailFinder la primera vez:")
            st.code(install, language="bash")
        return

    # --- resumen / stats ---
    stats = emailfinder.get("stats") or {}
    emails = emailfinder.get("emails") or []

    if emails:
        st.markdown(
            f"**EmailFinder (dominio: `{emailfinder.get('domain', '')}`)** — "
            f"Encontrados: **{stats.get('emails_found', len(emails))}** | "
            f"Exactos: **{stats.get('exact_matches', 0)}** | "
            f"Mismo dominio: **{stats.get('same_domain', 0)}**"
        )

        # lista deduplicada con etiquetas
        candidates = emailfinder.get("candidates") or []
        with st.expander("Emails deduplicados (con coincidencias)", expanded=False):
            for c in candidates:
                mail = c.get("email", "")
                tag = "✅ exacto" if c.get("exact_match") else ("🟦 mismo dominio" if c.get("same_domain") else "")
                if tag:
                    st.markdown(f"- `{mail}` — {tag}")
                else:
                    st.markdown(f"- `{mail}`")
    else:
        st.info("EmailFinder: no devolvió emails parseables (revisa salida cruda).")

    # salida cruda siempre disponible
    output = emailfinder.get("output") or "(sin salida de EmailFinder)"
    stderr = emailfinder.get("stderr") or ""
    with st.expander("Salida cruda EmailFinder", expanded=False):
        st.code(output, language="text")
        if stderr.strip():
            st.markdown("**stderr**")
            st.code(stderr, language="text")


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

            meta_parts = []
            if item.get("type"):
                meta_parts.append(item["type"])
            if item.get("confidence"):
                meta_parts.append(f"confianza: {item['confidence']}")

            suffix = f" — {', '.join(meta_parts)}" if meta_parts else ""
            bullet = f"- [{name}]({url}){suffix}" if url else f"- {name}{suffix}"
            st.markdown(bullet)

            command = item.get("command")
            if command:
                st.code(command, language="bash")


def _render_emailfinder_enriched(enriched: list):
    """
    Muestra el cruce HIBP/GHunt para candidatos devueltos por EmailFinder.
    """
    if not enriched:
        return

    with st.expander("Cruce HIBP/GHunt de candidatos (EmailFinder)", expanded=False):
        for item in enriched:
            if not isinstance(item, dict):
                continue
            email_value = item.get("email", "N/A")
            st.markdown(f"#### {email_value}")

            hibp_data = item.get("hibp")
            if hibp_data:
                _render_hibp(hibp_data)

            ghunt_data = item.get("ghunt")
            if ghunt_data:
                _render_ghunt(ghunt_data)

            st.markdown("---")


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

        emailfinder_data = e.get("emailfinder")
        if emailfinder_data:
            _render_emailfinder(emailfinder_data)

        # nuevo: cruce enriquecido
        enriched = e.get("emailfinder_enriched") or []
        _render_emailfinder_enriched(enriched)

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
