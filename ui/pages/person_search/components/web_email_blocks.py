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
# EMAIL2PHONENUMBER — RENDER OPERATIVO
# --------------------------------------------------

def _email2phone_score(parsed: dict) -> dict:
    lp = (parsed or {}).get("lastpass") or {}
    eb = (parsed or {}).get("ebay") or {}
    pp = (parsed or {}).get("paypal") or {}

    sources_hit = 0
    signals = []
    points = 0

    # LastPass
    lp_hit = False
    if lp.get("reported") is True and lp.get("last_digits"):
        lp_hit = True
        points += 25
        signals.append(f"LastPass: últimos 2 dígitos {lp.get('last_digits')}")
    if lp.get("length_without_cc") is not None:
        lp_hit = True
        points += 15
        signals.append(f"LastPass: longitud sin CC {lp.get('length_without_cc')}")
    if lp.get("non_us"):
        points += 5
        signals.append("LastPass: no US")
    if lp_hit:
        sources_hit += 1

    # eBay
    eb_hit = False
    if eb.get("reported") is True and eb.get("first_digit"):
        eb_hit = True
        points += 15
        signals.append(f"eBay: primer dígito {eb.get('first_digit')}")
    if eb.get("reported") is True and eb.get("last_digits"):
        eb_hit = True
        points += 20
        signals.append(f"eBay: últimos 2 dígitos {eb.get('last_digits')}")
    if eb_hit:
        sources_hit += 1

    # PayPal
    pp_hit = False
    if pp.get("reported") is True and pp.get("first_digit"):
        pp_hit = True
        points += 15
        signals.append(f"PayPal: primer dígito {pp.get('first_digit')}")
    if pp.get("reported") is True and pp.get("last_digits"):
        pp_hit = True
        cnt = pp.get("last_digits_count")
        bonus = 10 if (isinstance(cnt, int) and cnt >= 3) else 0
        points += 25 + bonus
        suffix = f" (x{cnt})" if cnt else ""
        signals.append(f"PayPal: últimos dígitos {pp.get('last_digits')}{suffix}")
    if pp.get("length_without_cc") is not None:
        pp_hit = True
        points += 10
        signals.append(f"PayPal: longitud sin CC {pp.get('length_without_cc')}")
    if pp_hit:
        sources_hit += 1

    # Bonus multi-fuente
    if sources_hit >= 2:
        points += 15
    if sources_hit >= 3:
        points += 10

    score = max(0, min(100, points))

    if score >= 70:
        level = "Alta"
        light = "🟢"
    elif score >= 35:
        level = "Media"
        light = "🟠"
    else:
        level = "Baja"
        light = "🔴"

    return {
        "score": score,
        "level": level,
        "light": light,
        "sources_hit": sources_hit,
        "signals": signals,
    }


def _render_email2phonenumber_operativo(e2p: dict):
    if not e2p:
        st.info("Email2PhoneNumber sin datos")
        return

    st.markdown("**Email2PhoneNumber (indicadores de teléfono)**")

    # errores duros
    if e2p.get("error"):
        st.error(f"🔴 Error: {e2p.get('error')}")
        repo = e2p.get("repo") or {}
        if repo.get("status") or repo.get("path"):
            st.caption(f"Repo: {repo.get('status')} — {repo.get('path')}")
        dep = e2p.get("dependency_check") or {}
        if dep.get("packages"):
            st.caption(f"Deps faltantes: {', '.join(dep.get('packages') or [])}")
        return

    parsed = e2p.get("parsed") or {}
    meta = _email2phone_score(parsed)

    st.markdown(
        f"{meta['light']} **Confianza: {meta['level']}** "
        f"(**{meta['score']}/100**, fuentes con señales: **{meta['sources_hit']}**) "
        f"— tiempo: `{e2p.get('elapsed', 0)}s`"
    )

    if not e2p.get("success"):
        st.warning(f"Email2PhoneNumber: ejecución no exitosa (returncode={e2p.get('returncode')})")

    signals = meta.get("signals") or []
    if signals:
        for s in signals[:6]:
            st.markdown(f"- {s}")
        if len(signals) > 6:
            st.caption(f"+{len(signals) - 6} señales adicionales (ver detalle)")
    else:
        st.info("Sin señales útiles (ningún servicio devolvió dígitos/longitud).")

    with st.expander("Detalle Email2PhoneNumber", expanded=False):
        msgs = (parsed.get("messages") or [])
        if msgs:
            st.code("\n".join(msgs), language="text")
        else:
            st.code(e2p.get("stdout") or "(sin stdout)", language="text")

        stderr = (e2p.get("stderr") or "").strip()
        if stderr:
            st.markdown("**stderr**")
            st.code(stderr, language="text")

        st.markdown("**Debug**")
        st.json({
            "returncode": e2p.get("returncode"),
            "repo": e2p.get("repo"),
            "dependency_check": e2p.get("dependency_check"),
        })


# --------------------------------------------------
# EMAILFINDER
# --------------------------------------------------

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

    stats = emailfinder.get("stats") or {}
    emails = emailfinder.get("emails") or []

    if emails:
        st.markdown(
            f"**EmailFinder (dominio: `{emailfinder.get('domain', '')}`)** — "
            f"Encontrados: **{stats.get('emails_found', len(emails))}** | "
            f"Exactos: **{stats.get('exact_matches', 0)}** | "
            f"Mismo dominio: **{stats.get('same_domain', 0)}**"
        )

        candidates = emailfinder.get("candidates") or []
        with st.expander("Emails deduplicados (con coincidencias)", expanded=False):
            for c in candidates:
                mail = c.get("email", "")
                tag = "✅ exacto" if c.get("exact_match") else ("🟦 mismo dominio" if c.get("same_domain") else "")
                st.markdown(f"- `{mail}`" + (f" — {tag}" if tag else ""))
    else:
        st.info("EmailFinder: no devolvió emails parseables (revisa salida cruda).")

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

        e2p_data = e.get("email2phonenumber")
        if e2p_data:
            _render_email2phonenumber_operativo(e2p_data)

        verification_data = e.get("verification")
        if verification_data:
            _render_verification(verification_data)

        emailfinder_data = e.get("emailfinder")
        if emailfinder_data:
            _render_emailfinder(emailfinder_data)

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
