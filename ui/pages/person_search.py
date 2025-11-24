# ui/pages/person_search.py

import streamlit as st
from modules.search.advanced_search import search_multiple_sources, search_with_filtering
from modules.search.relationship_search import suggest_relationships, find_connections
from modules.search.emailint import check_email_breach
from modules.search import archive_search
from modules.search.darkweb import search_dark_web_catalog, get_available_onion_search_engines, \
    check_onion_connectivity, get_darkweb_stats
from modules.search.pastesearch import search_paste_sites, search_leaks
from core.db_manager import create_person, get_persons_by_user
import json
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def show_person_search_ui():
    """
    Interfaz moderna y robusta con búsqueda avanzada multifuncional.
    Mejora en claridad, seguridad, manejo de errores, UX y escalabilidad.
    """
    # Header moderno con diseño SaaS y fondo oscuro (azul profesional)
    st.markdown("""
        <div style="background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%);
                    padding: 25px; border-radius: 15px; margin-bottom: 25px; 
                    box-shadow: 0 8px 25px rgba(0,0,0,0.15); border: 1px solid #1a1a2e;">
            <h1 style="color: white; text-align: center; margin: 0; font-size: 28px; font-weight: 600;">
                🚀 Búsqueda Avanzada Multifuncional
            </h1>
            <p style="color: rgba(255,255,255,0.85); text-align: center; margin: 15px 0; font-size: 16px; font-weight: 300;">
                Búsqueda inteligente, conexiones automáticas y análisis completo y seguro.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Variables de estado para evitar problemas de sesión
    search_name = st.session_state.get("search_name", "")
    search_email = st.session_state.get("search_email", "")
    search_location = st.session_state.get("search_location", "")
    search_phone = st.session_state.get("search_phone", "")
    search_domain = st.session_state.get("search_domain", "")
    search_files = st.session_state.get("search_files", "")
    search_company = st.session_state.get("search_company", "")
    search_role = st.session_state.get("search_role", "")
    search_date_start = st.session_state.get("date_start")
    search_date_end = st.session_state.get("date_end")
    search_sources = st.session_state.get("search_sources", ["people", "email", "social", "darkweb"])
    search_relationship = st.session_state.get("search_relationship", "Todas")
    search_confidence = st.session_state.get("search_confidence", 0.7)

    # Panel de búsqueda con múltiples criterios (inputs mejorados)
    st.markdown("### 🔍 Criterios de Búsqueda Avanzada")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search_name = st.text_input("🔍 Nombre", key="search_name",
                                    placeholder="Juan Pérez, María García",
                                    help="Nombre completo de la persona")

    with col2:
        search_email = st.text_input("✉️ Email", key="search_email",
                                     placeholder="nombre@dominio.com",
                                     help="Dirección de correo electrónico")

    with col3:
        search_location = st.text_input("📍 Ubicación", key="search_location",
                                        placeholder="Ciudad, País",
                                        help="Ubicación geográfica")

    with col4:
        search_phone = st.text_input("📱 Teléfono", key="search_phone",
                                     placeholder="+1-555-0123",
                                     help="Número de teléfono")

    # Filtros adicionales
    st.markdown("### 📜 Historial Histórico")
    col_hist = st.columns(2)
    with col_hist[0]:
        search_domain = st.text_input("🌐 Dominio", key="search_domain",
                                      placeholder="ejemplo.com",
                                      help="Dominio a analizar")

    with col_hist[1]:
        search_files = st.text_input("📄 Archivos", key="search_files",
                                     placeholder="/docs/estandares.pdf",
                                     help="Ruta de archivos específicos")

    st.markdown("### 🧩 Filtros Avanzados")

    col_filters = st.columns(3)

    with col_filters[0]:
        search_company = st.text_input("🏢 Empresa", key="search_company",
                                       placeholder="Nombre de la empresa")
        search_role = st.text_input("💼 Cargo", key="search_role",
                                    placeholder="Cargo profesional")

    with col_filters[1]:
        search_date_start = st.date_input("📅 Desde", value=None if not search_date_start else search_date_start,
                                          key="date_start")
        search_date_end = st.date_input("📅 Hasta", value=None if not search_date_end else search_date_end,
                                        key="date_end")

        # Selector de fuentes (con mejor UX y validación)
        search_sources = st.multiselect(
            "🌐 Fuentes",
            options=["all", "people", "email", "social", "domain", "web", "darkweb", "dorks"],
            default=["all"],
            key="search_sources",
            help="Selecciona las fuentes a usar en la búsqueda"
        )

    with col_filters[2]:
        # ✅ Corregido: No se pasa una lista, se pasa un entero
        relationship_options = ["Todas", "Colaborador", "Familiar", "Amigo", "Contacto"]
        default_index = 0

        # Buscar índice según valor actual (seguro)
        current_value = st.session_state.get("search_relationship", "Todas")
        if current_value in relationship_options:
            default_index = relationship_options.index(current_value)

        search_relationship = st.selectbox(
            "🔍 Tipo Relación",
            options=relationship_options,
            index=default_index,
            key="search_relationship"
        )

        search_confidence = st.slider("🎯 Confianza Mínima", 0.0, 1.0, 0.7, step=0.1,
                                      key="search_confidence",
                                      help="Mínimo nivel de confianza para mostrar resultados")

    # --- Acciones de búsqueda ---
    st.markdown("### ⚙️ Acciones de Búsqueda")

    col_actions = st.columns(5)

    with col_actions[0]:
        if st.button("🔍 Buscar Personas", use_container_width=True, key="btn_search",
                     help="Buscar personas con criterios"):
            # Validar al menos un campo no vacío
            query_input = search_name or search_email or search_location or search_phone or search_domain
            if not query_input:
                st.warning("⚠️ Por favor, introduce al menos un criterio de búsqueda.")
                return

            # Construir datos de búsqueda
            criteria = {
                "query": query_input,
                "name": search_name,
                "email": search_email,
                "location": search_location,
                "phone": search_phone,
                "domain": search_domain,
                "files": search_files,
                "company": search_company,
                "role": search_role,
                "date_range": {
                    "start": str(search_date_start) if search_date_start else None,
                    "end": str(search_date_end) if search_date_end else None
                }
            }

            try:
                with st.spinner("🔍 Realizando búsqueda avanzada con múltiples fuentes..."):
                    # Determinar fuentes reales a usar
                    # Si el usuario elige "all", incluir todas las fuentes disponibles, incluido dorks
                    if "all" in search_sources:
                        # Enumerar todas las fuentes soportadas por el buscador avanzado.  Se incluye
                        # la opción "dorks" para aprovechar las búsquedas Google Dorks
                        selected_sources = [
                            "people",
                            "email",
                            "social",
                            "domain",
                            "web",
                            "darkweb",
                            "dorks",
                        ]
                    else:
                        selected_sources = search_sources

                    # Si no hay fuentes seleccionadas, usar por defecto
                    if not selected_sources:
                        selected_sources = ["people", "email", "social", "domain", "darkweb"]

                    # Añadir dominio si hay búsqueda por dominio o archivo
                    if search_domain or search_files:
                        if "domain" not in selected_sources:
                            selected_sources.append("domain")

                    # Si se selecciona darkweb, hacer búsqueda real
                    if "darkweb" in selected_sources:
                        darkweb_result = search_dark_web_catalog(
                            criteria["query"],
                            search_type="catalog",
                            max_results=50
                        )
                        st.session_state['darkweb_results'] = darkweb_result

                    # Ejecutar búsqueda múltiple
                    search_results = search_multiple_sources(criteria["query"], selected_sources)

                    # Añadir historial si hay dominio
                    if search_domain:
                        archive_results = archive_search.search_web_archives(search_domain, ["wayback", "archive"])
                        search_results["archive_history"] = archive_results

                    # Guardar en sesión
                    st.session_state['search_results'] = search_results
                    st.session_state['search_criteria'] = criteria
                    st.session_state['search_timestamp'] = time.time()

                st.success(f"✅ Búsqueda completada con {len(selected_sources)} fuentes")

            except Exception as e:
                st.error(f"❌ Error en la búsqueda: {str(e)}")
                logger.error(f"Error en búsqueda avanzada: {e}", exc_info=True)

    with col_actions[1]:
        if st.button("🔄 Limpiar", use_container_width=True, key="btn_clear", help="Limpiar todos los campos"):
            # Eliminar campos de búsqueda de sesión
            for key in [
                "search_name", "search_email", "search_location", "search_phone",
                "search_domain", "search_files", "search_company", "search_role",
                "date_start", "date_end", "search_sources", "search_relationship", "search_confidence"
            ]:
                st.session_state[key] = ""
            st.session_state['search_results'] = None
            st.session_state['darkweb_results'] = None
            st.rerun()

    with col_actions[2]:
        if st.button("🧩 Analizar Relaciones", use_container_width=True, key="btn_analyze",
                     help="Analizar posibles relaciones"):
            if st.session_state.get('search_results') is None:
                st.warning("⚠️ Primero busca personas antes de analizar relaciones")
                return

            st.info("🔍 Analizando relaciones entre las personas encontradas...")
            st.session_state['page'] = 'relationship_analysis'
            st.session_state['force_reload'] = True
            st.rerun()

    with col_actions[3]:
        if st.button("📊 Exportar Resultados", use_container_width=True, key="btn_export",
                     help="Exportar resultados a archivo"):
            if st.session_state.get('search_results') is None:
                st.warning("⚠️ No hay resultados para exportar")
                return

            results = st.session_state['search_results']
            total_count = sum(
                len(r.get('results', [])) for r in results.values() if isinstance(r, dict) and 'results' in r)

            st.info(f"📥 Exportando {total_count} resultados a archivo... (en desarrollo)")
            # Aquí se implementaría la exportación (CSV, JSON, etc.)

    # Mostrar resultados si existen
    if 'search_results' in st.session_state and st.session_state['search_results']:
        st.markdown("---")
        st.subheader("📊 Resultados de Búsqueda")

        results = st.session_state['search_results']
        total_count = 0

        for source_type, source_results in results.items():
            if isinstance(source_results, dict) and source_results.get('error'):
                st.markdown(f"""
                    <div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <strong>⚠️ Error en {source_type}:</strong> {source_results['error']}
                    </div>
                """, unsafe_allow_html=True)
                continue

            try:
                # Personas
                if source_type == 'people' and isinstance(source_results, dict) and 'results' in source_results:
                    st.markdown(f"### 👥 Resultados de Personas")
                    person_results = source_results['results']
                    total_count += len(person_results)

                    for i, person in enumerate(person_results):
                        if isinstance(person, dict) and 'name' in person:
                            person_name = person.get('name', 'Nombre desconocido')
                            person_email = person.get('email', 'N/A')
                            person_phone = person.get('phone', 'N/A')
                            person_location = person.get('location', 'N/A')
                            person_confidence = person.get('confidence', 0.8)

                            # Extraer otros datos disponibles
                            other_fields = []
                            for key, value in person.items():
                                if key not in ['name', 'email', 'phone', 'location', 'confidence']:
                                    other_fields.append(
                                        f"<p style='color: #b0b0c0; margin: 3px 0; font-size: 13px;'><strong>{key.title()}:</strong> {value}</p>")

                            person_card = f"""
                            <div style="background: #1e1e2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                       padding: 20px; margin-bottom: 15px; box-shadow: 0 3px 10px rgba(0,0,0,0.5);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                    <div>
                                        <h3 style="margin: 0; color: #ffffff; font-size: 20px;">{person_name}</h3>
                                        <p style="color: #b0b0c0; margin: 8px 0; font-size: 14px;">
                                            <strong>Email:</strong> {person_email}<br/>
                                            <strong>Teléfono:</strong> {person_phone}<br/>
                                            <strong>Ubicación:</strong> {person_location}
                                        </p>
                                        {" ".join(other_fields)}
                                    </div>
                                    <div style="text-align: right;">
                                        <span style="display: block; background: #28a745; color: white; 
                                                   padding: 5px 15px; border-radius: 15px; font-size: 14px;">
                                            ⭐ {person_confidence:.2f}
                                        </span>
                                    </div>
                                </div>
                                <div style="display: flex; gap: 10px;">
                                    <button onclick="handleSavePerson('{json.dumps(person).replace(chr(34), '&quot;')}')" 
                                            style="background: #28a745; color: white; border: none; padding: 8px 15px; 
                                                   border-radius: 6px; cursor: pointer; font-size: 14px;" 
                                            class="save-btn-{i}">
                                        ✅ Guardar Persona
                                    </button>
                                </div>
                            </div>
                            """
                            st.markdown(person_card, unsafe_allow_html=True)

                    # Mostrar resultados de perfiles sociales (Maigret/Sherlock) si existen
                    for item in person_results:
                        if isinstance(item, dict) and 'social_profiles' in item:
                            social_profiles = item.get('social_profiles', {})
                            if social_profiles:
                                st.markdown("### 🌐 Perfiles Sociales (Maigret y Sherlock)")
                                for tool_name, result_data in social_profiles.items():
                                    display_name = tool_name.capitalize()
                                    if isinstance(result_data, dict):
                                        if 'error' in result_data:
                                            st.warning(f"{display_name}: {result_data['error']}")
                                        elif 'warning' in result_data:
                                            st.info(f"{display_name}: {result_data['warning']}")
                                        else:
                                            st.markdown(f"#### {display_name} resultados")
                                            st.json(result_data)
                                    else:
                                        st.markdown(f"#### {display_name} resultados")
                                        st.json(result_data)
                            break

                # Emails
                elif source_type == 'email' and isinstance(source_results, dict) and 'results' in source_results:
                    st.markdown(f"### 📧 Resultados de Email")
                    email_results = source_results['results']
                    total_count += len(email_results)

                    for i, email_info in enumerate(email_results):
                        if isinstance(email_info, dict):
                            email_value = email_info.get('email', 'Email')
                            breach_value = email_info.get('breached', False) or email_info.get('breach_count', 0) > 0
                            breach_count = email_info.get('breach_count', 0)
                            sources_list = str(email_info.get('sources', [])) if 'sources' in email_info else 'API'

                            # Extraer otros datos disponibles
                            other_fields = []
                            for key, value in email_info.items():
                                if key not in ['email', 'breached', 'breach_count', 'sources']:
                                    other_fields.append(
                                        f"<p style='color: #b0b0c0; margin: 3px 0; font-size: 13px;'><strong>{key.title()}:</strong> {value}</p>")

                        else:
                            email_value = "Error de búsqueda"
                            breach_value = False
                            breach_count = 0
                            sources_list = "N/A"
                            other_fields = []

                        email_card = f"""
                        <div style="background: #1e1e2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                   padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4 style="margin: 0; color: #ffffff;">{email_value}</h4>
                                <span style="background: {'#28a745' if breach_value or breach_count > 0 else '#ffc107'}; 
                                           color: white; padding: 5px 10px; border-radius: 10px; font-size: 14px;">
                                    {'Comprometido' if breach_value or breach_count > 0 else 'Seguro'}
                                </span>
                            </div>
                            <p style="color: #b0b0c0; margin: 8px 0; font-size: 14px;">
                                <strong>Breaches:</strong> {breach_count}<br/>
                                <strong>Fuente:</strong> {sources_list}
                            </p>
                            {" ".join(other_fields)}
                        </div>
                        """
                        st.markdown(email_card, unsafe_allow_html=True)

                # Redes sociales
                elif source_type == 'social' and isinstance(source_results, dict) and 'results' in source_results:
                    st.markdown(f"### 📱 Resultados de Redes Sociales")
                    social_results = source_results['results']
                    total_count += len(social_results)

                    for i, social_data in enumerate(social_results):
                        username_value = social_data.get('username', 'Usuario')
                        platform_value = social_data.get('platform', 'N/A')
                        followers_value = social_data.get('followers', 'N/A')
                        posts_value = social_data.get('posts', 'N/A')
                        verified_value = social_data.get('verified', False)

                        # Extraer otros datos disponibles
                        other_fields = []
                        for key, value in social_data.items():
                            if key not in ['username', 'platform', 'followers', 'posts', 'verified']:
                                other_fields.append(
                                    f"<p style='color: #b0b0c0; margin: 3px 0; font-size: 13px;'><strong>{key.title()}:</strong> {value}</p>")

                        social_card = f"""
                        <div style="background: #1e1e2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                   padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
                            <div style="display: flex; align-items: center;">
                                <div style="flex: 1;">
                                    <h4 style="margin: 0; color: #ffffff;">@{username_value}</h4>
                                    <p style="color: #b0b0c0; margin: 8px 0; font-size: 14px;">
                                        <strong>Plataforma:</strong> {platform_value}<br/>
                                        <strong>Seguidores:</strong> {followers_value}<br/>
                                        <strong>Posteos:</strong> {posts_value}
                                    </p>
                                    {" ".join(other_fields)}
                                </div>
                                <div style="text-align: right;">
                                    <span style="display: block; background: #007bff; color: white; 
                                               padding: 5px 10px; border-radius: 15px; font-size: 14px;">
                                        {'Verificado' if verified_value else 'No verificado'}
                                    </span>
                                </div>
                            </div>
                        </div>
                        """
                        st.markdown(social_card, unsafe_allow_html=True)

                # Historial
                elif source_type == 'archive_history':
                    st.markdown(f"### 📜 Historial Histórico")
                    if isinstance(source_results, dict):
                        for archive_source, archive_results in source_results.items():
                            if isinstance(archive_results, list) and archive_results:
                                st.markdown(f"#### {archive_source.upper()} Capturas")
                                for i, capture in enumerate(archive_results[:3]):
                                    if 'error' not in capture and 'url' in capture:
                                        details = capture.get('timestamp_human', capture.get('url', 'Unknown'))
                                        st.markdown(f"""
                                        <div style="background: #1e1e2e; border: 1px solid #3a3a4c; border-radius: 8px; 
                                                   padding: 10px; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                                            <h5 style="margin: 0; color: #ffffff;">{details}</h5>
                                            <a href="{capture.get('url', '#')}" target="_blank" style="color: #3498db;">
                                                🌐 Ver captura completa
                                            </a>
                                            {f'<p style="color: #b0b0c0; font-size: 14px;">Confianza: {capture.get("confidence", 0.9):.2f}</p>' if 'confidence' in capture else ''}
                                        </div>
                                        """, unsafe_allow_html=True)

                # Búsqueda Web
                elif source_type == 'web' and isinstance(source_results, dict) and 'results' in source_results:
                    st.markdown(f"### 🌍 Resultados Web")
                    web_results = source_results['results']
                    total_count += len(web_results)

                    for i, web_item in enumerate(web_results):
                        title = web_item.get('title', 'Sin título')
                        url_val = web_item.get('url', '#')
                        snippet = web_item.get('snippet', '')
                        confidence = web_item.get('confidence', 0.0)

                        # Extraer otros datos disponibles
                        other_fields = []
                        for key, value in web_item.items():
                            if key not in ['title', 'url', 'snippet', 'confidence']:
                                other_fields.append(
                                    f"<p style='color: #b0b0c0; margin: 3px 0; font-size: 13px;'><strong>{key.title()}:</strong> {value}</p>")

                        web_card = f"""
                        <div style="background: #1e1e2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                   padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
                            <h4 style="margin: 0; color: #ffffff;">{title}</h4>
                            <p style="color: #b0b0c0; margin: 8px 0; font-size: 14px;">{snippet}</p>
                            {" ".join(other_fields)}
                            <a href="{url_val}" target="_blank" style="color: #3498db; text-decoration: none; font-size: 14px;">🔗 Abrir enlace</a>
                            <div style="margin-top: 5px;">
                                <span style="display: inline-block; background: #17a2b8; color: white; padding: 3px 8px; 
                                           border-radius: 10px; font-size: 12px;">Confianza: {confidence:.2f}</span>
                            </div>
                        </div>
                        """
                        st.markdown(web_card, unsafe_allow_html=True)

                # Resultados de Dorks
                elif source_type == 'dorks' and isinstance(source_results, dict) and 'results' in source_results:
                    st.markdown(f"### 🔎 Resultados de Google Dorks")
                    dork_results = source_results['results']
                    total_count += len(dork_results)
                    for i, dork_item in enumerate(dork_results):
                        dork_query = dork_item.get('query', '')
                        dork_url = dork_item.get('url', '#')
                        dork_title = dork_item.get('title', 'Dork')
                        dork_confidence = dork_item.get('confidence', 0.0)

                        # Subresultados del dork (pueden venir de SerpAPI, Google CSE o DuckDuckGo)
                        subresults = dork_item.get('results', []) if isinstance(dork_item, dict) else []

                        subresults_html = ""
                        if subresults:
                            subresults_html += "<ul style='margin-top: 10px;'>"
                            for sub in subresults:
                                title = sub.get('title', 'Sin título')
                                url_link = sub.get('url', '#')
                                snippet = sub.get('snippet', '')
                                confidence_sub = sub.get('confidence', 0.0)

                                # Extraer datos adicionales de los subresultados
                                sub_fields = []
                                for key, value in sub.items():
                                    if key not in ['title', 'url', 'snippet', 'confidence']:
                                        sub_fields.append(
                                            f"<br/><span style='font-size:12px; color:#b0b0c0;'>{key.title()}: {value}</span>")

                                subresults_html += (
                                    f"<li style='margin-bottom:8px; color: #b0b0c0; font-size: 12px;'>"
                                    f"<a href='{url_link}' target='_blank' style='color:#3498db; font-weight:600;'>{title}</a>"
                                )
                                if snippet:
                                    subresults_html += f"<br/><span style='font-size:13px; color:#b0b0c0;'>{snippet}</span>"
                                subresults_html += (
                                    f"<br/><span style='font-size:11px; color:#b0b0c0;'>Confianza: {confidence_sub:.2f}</span>"
                                    f"{''.join(sub_fields)}"
                                    "</li>"
                                )
                            subresults_html += "</ul>"

                        # Extraer datos adicionales del dork principal
                        dork_fields = []
                        for key, value in dork_item.items():
                            if key not in ['query', 'url', 'title', 'confidence', 'results']:
                                dork_fields.append(
                                    f"<p style='color: #b0b0c0; margin: 3px 0; font-size: 13px;'><strong>{key.title()}:</strong> {value}</p>")

                        dork_card = f"""
                        <div style="background: #1e1e2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                   padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
                            <h4 style="margin: 0; color: #ffffff;">{dork_title}</h4>
                            <p style="color: #b0b0c0; margin: 8px 0; font-size: 14px;">
                                Consulta Dork: <code style="color: #3498db; background: #2d2d3d; padding: 2px 5px; border-radius: 3px;">{dork_query}</code>
                            </p>
                            {" ".join(dork_fields)}
                            <a href="{dork_url}" target="_blank" style="color: #3498db; text-decoration: none; font-size: 14px;">
                                🔗 Ver búsqueda en Google
                            </a>
                            <div style="margin-top: 5px;">
                                <span style="display: inline-block; background: #6f42c1; color: white; padding: 3px 8px;
                                           border-radius: 10px; font-size: 12px;">
                                    Confianza: {dork_confidence:.2f}
                                </span>
                            </div>
                            {subresults_html}
                        </div>
                        """
                        st.markdown(dork_card, unsafe_allow_html=True)

                # Búsqueda de Dominio
                elif source_type == 'domain' and isinstance(source_results, dict) and 'results' in source_results:
                    st.markdown(f"### 🌐 Historial de Dominio")
                    domain_data = source_results['results']
                    domain_name = domain_data.get('domain', 'Dominio desconocido')
                    history = domain_data.get('history', [])
                    snapshots = domain_data.get('wayback_snapshots', [])
                    total_history = len(history)
                    total_snapshots = len(snapshots)
                    st.markdown(f"**Dominio:** {domain_name}")
                    st.markdown(f"**Entradas de historial:** {total_history}")
                    st.markdown(f"**Capturas Wayback:** {total_snapshots}")
                    if history:
                        st.markdown("#### Últimas entradas de historial")
                        for entry in history[:3]:
                            if isinstance(entry, dict):
                                entry_text = entry.get('timestamp_human', '') or entry.get('url', '')
                            else:
                                entry_text = str(entry)
                            st.markdown(f"- {entry_text}")
                    if snapshots:
                        st.markdown("#### Algunas capturas de Wayback")
                        for snap in snapshots[:3]:
                            if isinstance(snap, dict):
                                snap_url = snap.get('url', '#')
                                snap_date = snap.get('timestamp_human', '')
                                st.markdown(f"- [{snap_date or snap_url}]({snap_url})")
                            else:
                                st.markdown(f"- {snap}")

                # Dark Web
                elif source_type == 'darkweb' and st.session_state.get('darkweb_results'):
                    st.markdown(f"### 🔍 Resultados Dark Web")
                    dark_results = st.session_state['darkweb_results']
                    if 'raw_results' in dark_results:
                        for engine_name, engine_results in dark_results['raw_results'].items():
                            if isinstance(engine_results, list) and engine_results:
                                with st.expander(f"🔍 {engine_name}"):
                                    for j, result in enumerate(engine_results[:3]):
                                        # Extraer datos adicionales de los resultados dark web
                                        other_fields = []
                                        for key, value in result.items():
                                            if key not in ['title', 'source', 'description', 'url']:
                                                other_fields.append(
                                                    f"<p style='color: #b0b0c0; margin: 3px 0; font-size: 13px;'><strong>{key.title()}:</strong> {value}</p>")

                                        st.markdown(f"""
                                        <div style="border-left: 4px solid #e74c3c; padding: 10px; margin: 10px 0; 
                                                   background: #1e1e2e; border-radius: 0 8px 8px 0;">
                                            <h4 style="color: #e74c3c; margin: 0;">{result.get('title', 'Título sin especificar')}</h4>
                                            <p style="color: #b0b0c0; margin: 5px 0;"><strong>Fuente:</strong> {result.get('source', 'Desconocida')}</p>
                                            <p style="margin: 0;">{result.get('description', 'Sin descripción')}</p>
                                            {" ".join(other_fields)}
                                            <a href="{result.get('url', '#')}" target="_blank" style="color: #3498db;">Ver detalles</a>
                                        </div>
                                        """, unsafe_allow_html=True)

            except Exception as e:
                st.warning(f"Error al mostrar resultados de {source_type}: {str(e)}")

        # Mostrar estadísticas
        if total_count > 0:
            st.markdown(f"### 📊 Estadísticas")
            st.info(f"🔍 Total de resultados encontrados: **{total_count}**")
            st.success("✅ Búsqueda realizada con éxito!")

    # Análisis de relaciones
    if 'search_results' in st.session_state and st.session_state['search_results']:
        st.markdown("---")

        # --- NUEVA SECCIÓN: Resultados de Pases y Leaks ---
        if 'search_results' in st.session_state and st.session_state['search_results']:
            st.markdown("---")
            st.subheader("📎 Resultados de Pases y Leaks")

            query = st.session_state.get('search_name', '') or st.session_state.get('search_email',
                                                                                    '') or st.session_state.get(
                'search_domain', '')
            if not query:
                st.info("🔍 No se encontraron resultados de paste o leaks (no se ha buscado un término clave)")
                return

            # 🔍 Llama a la función de búsqueda real
            paste_results = search_paste_sites(query)

            if paste_results:
                st.markdown("### 🔍 Resultados en Pastes y Leaks")
                for i, result in enumerate(paste_results):
                    with st.expander(f"📄 {result['title']} ({result['source']})", expanded=False):
                        st.markdown(f"""
                        <div style="background: #1a1a2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                   padding: 15px; color: #e6e6fa; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                            <h5 style="margin: 0; color: #ffffff;">{result['title']}</h5>
                            <p style="color: #b0b0c0; font-size: 14px;">
                                <strong>Fecha:</strong> {result.get('date', 'Desconocida')}<br/>
                                <strong>Tamaño:</strong> {result.get('size', 'N/A')}<br/>
                                <strong>Idioma:</strong> {result.get('language', 'N/A')}<br/>
                                <strong>Fuente:</strong> {result.get('source', 'N/A')}
                            </p>
                            <a href="{result.get('url', '#')}" target="_blank" style="color: #28a745; text-decoration: underline; font-size: 13px;">
                                🌐 Ver enlace
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("🔍 No se encontraron pastes o leaks relevantes para este término.")

        st.subheader("🔗 Análisis de Relaciones")

        with st.expander("🔍 Analizar posibles relaciones", expanded=False):
            st.write("Detecta automáticamente conexiones entre personas encontradas:")

            if st.button("🔍 Encontrar Conexiones", key="find_connections_btn"):
                try:
                    st.info("🔄 Buscando conexiones entre personas...")
                    connections = find_connections(st.session_state['search_results'])
                    if connections:
                        for conn in connections:
                            st.success(f"🔍 Conexión encontrada: {conn}")
                    else:
                        st.warning("No se encontraron conexiones significativas.")
                except Exception as e:
                    st.error(f"Error al encontrar conexiones: {e}")

            if st.button("🔗 Detectar Tipos", key="detect_types_btn"):
                try:
                    st.info("🔎 Detectando tipos de relación...")
                    suggested = suggest_relationships(st.session_state['search_results'])
                    if suggested:
                        for rel_type, persons in suggested.items():
                            st.info(f"💡 Sugerencia: {rel_type} entre {', '.join(p['name'] for p in persons)}")
                    else:
                        st.info("No se detectaron relaciones específicas.")
                except Exception as e:
                    st.error(f"Error al detectar relaciones: {e}")

    # --- Nueva sección de búsqueda en fuentes públicas ---
    # Sección para búsqueda en fuentes públicas que contengan los datos introducidos
    st.markdown("---")
    st.subheader("🌐 Búsqueda en Fuentes Públicas")

    # Crear lista de términos de búsqueda basados en los campos del formulario
    search_terms = []

    # Añadir términos de búsqueda de los campos de texto
    if search_name:
        search_terms.extend([term.strip() for term in search_name.split() if term.strip()])
    if search_email:
        # Añadir parte del email sin dominio
        email_parts = search_email.split('@')[0].split('.')
        search_terms.extend(email_parts)
    if search_location:
        search_terms.extend([term.strip() for term in search_location.split() if term.strip()])
    if search_company:
        search_terms.extend([term.strip() for term in search_company.split() if term.strip()])
    if search_role:
        search_terms.extend([term.strip() for term in search_role.split() if term.strip()])
    if search_domain:
        # Usar solo el nombre del dominio
        domain_name = search_domain.split('.')[0] if '.' in search_domain else search_domain
        search_terms.append(domain_name)
    if search_phone:
        # Extraer números del teléfono
        phone_numbers = ''.join(filter(str.isdigit, search_phone))
        if len(phone_numbers) >= 6:  # Solo números largos
            search_terms.append(phone_numbers)

    # Eliminar duplicados
    search_terms = list(set(term for term in search_terms if len(term) > 2))

    if search_terms:
        st.info(f"🔍 Buscando en fuentes públicas con términos: {', '.join(search_terms)}")

        # Botón para iniciar búsqueda en fuentes públicas
        if st.button("🔍 Buscar en Fuentes Públicas", use_container_width=True):
            try:
                # Importar módulos de búsqueda de fuentes públicas dentro del bloque
                from modules.search.pastesearch import search_paste_sites
                from modules.search.emailint import check_email_breach

                st.info("🔍 Realizando búsquedas en fuentes públicas...")

                # Búsqueda en pastes y leaks
                paste_results = []
                for term in search_terms:
                    try:
                        results = search_paste_sites(term)
                        paste_results.extend(results)
                    except Exception as e:
                        logger.warning(f"Error buscando paste para '{term}': {e}")

                # Mostrar resultados de pastes
                if paste_results:
                    st.markdown("### 📄 Resultados de Pastes y Leaks")
                    for i, result in enumerate(paste_results):
                        with st.expander(f"📄 {result['title']} ({result['source']})", expanded=False):
                            st.markdown(f"""
                            <div style="background: #1a1a2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                       padding: 15px; color: #e6e6fa; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                                <h5 style="margin: 0; color: #ffffff;">{result['title']}</h5>
                                <p style="color: #b0b0c0; font-size: 14px;">
                                    <strong>Fecha:</strong> {result.get('date', 'Desconocida')}<br/>
                                    <strong>Tamaño:</strong> {result.get('size', 'N/A')}<br/>
                                    <strong>Idioma:</strong> {result.get('language', 'N/A')}<br/>
                                    <strong>Fuente:</strong> {result.get('source', 'N/A')}
                                </p>
                                <a href="{result.get('url', '#')}" target="_blank" style="color: #28a745; text-decoration: underline; font-size: 13px;">
                                    🌐 Ver enlace
                                </a>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("🔍 No se encontraron resultados en fuentes de paste y leaks.")

                # Búsqueda de brechas de email (solo si hay emails)
                email_breaches = []
                for term in search_terms:
                    if '@' in term and '.' in term:  # Es probablemente un email
                        try:
                            breach_result = check_email_breach(term, st.session_state.get('current_user_id', 1))
                            if isinstance(breach_result, dict) and breach_result.get('breached'):
                                email_breaches.append(breach_result)
                        except Exception as e:
                            logger.debug(f"Error verificando brecha de email: {e}")

                if email_breaches:
                    st.markdown("### 📧 Brechas de Email Encontradas")
                    for breach in email_breaches:
                        st.markdown(f"""
                        <div style="background: #1a1a2e; border: 1px solid #3a3a4c; border-radius: 12px; 
                                   padding: 15px; color: #e6e6fa; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                            <h5 style="margin: 0; color: #ffffff;">Email comprometido</h5>
                            <p style="color: #b0b0c0; font-size: 14px;">
                                <strong>Email:</strong> {breach.get('email', 'N/A')}<br/>
                                <strong>Breaches:</strong> {breach.get('breach_count', 0)}<br/>
                                <strong>Fuente:</strong> {breach.get('source', 'N/A')}
                            </p>
                            {f'<p style="color: #b0b0c0; font-size: 14px;"><strong>Mensaje:</strong> {breach.get("message", "N/A")}</p>' if breach.get("message") else ""}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("🔍 No se encontraron brechas de email relevantes.")

            except Exception as e:
                st.error(f"❌ Error en búsqueda en fuentes públicas: {str(e)}")
                logger.error(f"Error al buscar en fuentes públicas: {e}")
    else:
        st.info(
            "📝 Introduce información en los campos de búsqueda para activar la opción de búsqueda en fuentes públicas.")

    # Estado de Tor y dark web
    if 'search_results' in st.session_state and st.session_state['search_results']:
        st.markdown("---")
        st.subheader("📡 Estado de Conexión")

        try:
            tor_status = check_onion_connectivity()
            if tor_status:
                st.success("✅ Conexión Tor: ACTIVA")
                from utils.tor_proxy import get_tor_ip
                ip_info = get_tor_ip()
                if ip_info.get('ip'):
                    st.info(f"IP Anónima: {ip_info['ip']}")
            else:
                st.warning("⚠️ Conexión Tor: NO DISPONIBLE")
                st.info("Asegúrate de que Tor esté corriendo en 127.0.0.1:9050.")

        except Exception as e:
            st.warning(f"⚠️ Error verificando conexión Tor: {e}")

        try:
            stats = get_darkweb_stats()
            st.markdown("### 🌐 Estadísticas de Dark Web")
            st.info(f"🟢 Conexión Onion: {'ACTIVA' if stats.get('tor_connectivity', False) else 'DESACTIVADA'}")
            st.info(f"📚 Motores disponibles: {stats.get('supported_sources', 0)}/{stats.get('total_sources', 0)}")
        except Exception as e:
            st.info("📊 No se pudieron cargar estadísticas de dark web.")

        # Recomendaciones de seguridad
        st.markdown("### 🔐 Recomendaciones de Seguridad")
        st.info("""
        - Asegúrate de tener Tor corriendo en tu máquina (127.0.0.1:9050)
        - Usa claves API con acceso mínimo
        - Analiza datos sensibles en entornos anónimos
        - Cambia tu identidad de Tor periódicamente para mantener privacidad
        """)

    # Botón para volver al dashboard
    if st.button(" ← Volver al Dashboard", use_container_width=True):
        st.session_state['page'] = 'dashboard'
        st.session_state['search_results'] = None
        st.session_state['darkweb_results'] = None
        st.rerun()