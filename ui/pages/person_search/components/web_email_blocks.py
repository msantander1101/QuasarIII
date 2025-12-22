import streamlit as st


# --------------------------------------------------
# GHUNT
# --------------------------------------------------

def _render_ghunt(ghunt: dict):
    if not ghunt:
        st.info("GHunt sin datos")
        return

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


# --------------------------------------------------
# HASHTRAY — RENDER
# --------------------------------------------------

def _render_hashtray(hashtray: dict):
    if not hashtray:
        st.info("Hashtray sin datos")
        return

    st.markdown("**Hashtray (Gravatar pivot)**")

    # error duro del wrapper
    if hashtray.get("error"):
        st.warning(f"Hashtray: {hashtray.get('error')}")

        install = hashtray.get("install") or {}
        cmd = install.get("command")
        if cmd:
            st.caption("Instalación automática (si aplica):")
            st.code(cmd, language="bash")

        inst_err = (install.get("stderr") or "").strip()
        if inst_err:
            with st.expander("stderr instalación hashtray", expanded=False):
                st.code(inst_err, language="text")
        return

    ok = bool(hashtray.get("success"))
    found = hashtray.get("found")
    elapsed = hashtray.get("elapsed", 0)
    rc = hashtray.get("returncode")

    if ok and found is False:
        st.info(f"🟦 Gravatar no encontrado (404) — `{elapsed}s`")
    else:
        st.markdown(
            f"{'🟢' if ok else '🔴'} "
            f"Estado: **{'OK' if ok else 'Ejecución fallida'}**"
            f"{f' (rc={rc})' if rc is not None else ''} — "
            f"tiempo: `{elapsed}s`"
        )

    cmd = hashtray.get("command")
    if cmd:
        st.caption("Comando ejecutado:")
        st.code(cmd, language="bash")

    stdout = (hashtray.get("stdout") or "").strip()
    stderr = (hashtray.get("stderr") or "").strip()

    if stdout:
        with st.expander("Salida hashtray", expanded=found is True):
            st.code(stdout, language="text")

    if stderr:
        with st.expander("stderr hashtray", expanded=False):
            st.code(stderr, language="text")

    attempts = hashtray.get("attempts") or []
    if attempts:
        with st.expander("Debug hashtray", expanded=False):
            st.json(attempts)


# --------------------------------------------------
# VERIFICACIÓN
# --------------------------------------------------

def _render_verification(verification: dict):
    if not verification:
        return

    deliverable = verification.get("deliverable", "unknown")
    reason = verification.get("reason")

    status_label = {
        True: "Entregable",
        False: "No entregable",
        "unknown": "Sin comprobar",
    }.get(deliverable, "Sin comprobar")

    msg = f"**Estado de entrega**: {status_label}"
    if reason:
        msg += f" — Motivo: {reason}"

    st.markdown(msg)


# --------------------------------------------------
# FUENTES OSINT
# --------------------------------------------------

def _render_sources(sources: dict):
    if not sources:
        return

    st.markdown("**Fuentes OSINT**")

    groups = [
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

            meta = []
            if item.get("type"):
                meta.append(item["type"])
            if item.get("confidence"):
                meta.append(f"confianza: {item['confidence']}")

            suffix = f" — {', '.join(meta)}" if meta else ""
            st.markdown(f"- [{name}]({url}){suffix}")

            command = item.get("command")
            if command:
                st.code(command, language="bash")


# --------------------------------------------------
# MAIN EMAIL BLOCK
# --------------------------------------------------

def render_email_block(email_block: dict):
    st.markdown("### 📧 Emails")

    if not isinstance(email_block, dict):
        st.info("No hay resultados de email")
        return

    for err in email_block.get("errors") or []:
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

        ghunt_data = e.get("ghunt")
        if ghunt_data:
            _render_ghunt(ghunt_data)

        hashtray_data = e.get("hashtray")
        if hashtray_data:
            _render_hashtray(hashtray_data)

        verification_data = e.get("verification")
        if verification_data:
            _render_verification(verification_data)

        sources = e.get("sources")
        if sources:
            _render_sources(sources)

        st.markdown("---")


# --------------------------------------------------
# WEB BLOCK
# --------------------------------------------------

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
