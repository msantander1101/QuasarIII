# ui/pages/person_search.py

import streamlit as st
from modules.search.advanced_search import search_multiple_sources, search_with_filtering
from modules.search.relationship_search import suggest_relationships, find_connections
from modules.search.emailint import check_email_breach
from modules.search import archive_search
from core.db_manager import create_person, get_persons_by_user
import json
import logging
import time

logger = logging.getLogger(__name__)


def show_person_search_ui():
    """
    Interfaz moderna con búsqueda avanzada multifunción
    """

    # Header moderno con diseño SaaS y fondo oscuro
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    padding: 25px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 8px 25px rgba(0,0,0,0.15);">
            <h1 style="color: white; text-align: center; margin: 0; font-size: 28px;">
                🚀 Búsqueda Avanzada Multifunción
            </h1>
            <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 15px 0; font-size: 16px;">
                Búsqueda inteligente, conexiones automáticas, análisis completo
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Panel de búsqueda con múltiples criterios
    st.markdown("### 🔍 Criterios de Búsqueda Avanzada")

    # Columnas para entradas de búsqueda
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

        search_company_role = st.text_input("💼 Cargo", key="search_role",
                                            placeholder="Cargo profesional")

    with col_filters[1]:
        search_date_start = st.date_input("📅 Desde", key="date_start")
        search_date_end = st.date_input("📅 Hasta", key="date_end")

        # Selector de fuentes
        search_source = st.multiselect("🌐 Fuentes",
                                       ["all", "people", "email", "social", "domain", "web"],
                                       default=["people", "email", "social"],
                                       key="search_sources")

    with col_filters[2]:
        search_relationship = st.selectbox("🔍 Tipo Relación",
                                           ["Todas", "Colaborador", "Familiar", "Amigo", "Contacto"],
                                           key="search_relationship")

        search_confidence = st.slider("🎯 Confianza Mínima", 0.0, 1.0, 0.7, 0.1,
                                      key="search_confidence")

    # Grupo de botones de acción
    st.markdown("### ⚙️ Acciones de Búsqueda")

    col_actions = st.columns(4)

    with col_actions[0]:
        if st.button("🔍 Buscar Personas", use_container_width=True,
                     key="btn_search", help="Buscar personas con criterios específicos"):
            # Validar entradas
            if not any([search_name, search_email, search_location, search_phone, search_domain]):
                st.warning("Por favor, introduce al menos un criterio de búsqueda")
                return

            # Preparar criterios de búsqueda
            query_data = {
                "query": search_name or search_email or search_location or search_phone or search_domain,
                "name": search_name,
                "email": search_email,
                "location": search_location,
                "phone": search_phone,
                "domain": search_domain,
                "files": search_files,
                "company": search_company,
                "role": search_company_role,
                "date_range": {
                    "start": str(search_date_start) if search_date_start else None,
                    "end": str(search_date_end) if search_date_end else None
                }
            }

            # Ejecutar búsqueda avanzada
            try:
                with st.spinner("🔍 Realizando búsqueda avanzada con datos reales..."):
                    # Buscar en múltiples fuentes
                    selected_sources = [s for s in search_source if
                                        s != "all"] if "all" in search_source else search_source
                    if not selected_sources:
                        selected_sources = ["people", "email", "social", "domain"]

                    # Verifica si debemos incluir búsqueda de archivo histórico
                    if search_domain or search_files:
                        if "domain" not in selected_sources:
                            selected_sources.append("domain")

                    # Buscar usando los módulos integrados reales con las APIs configuradas
                    search_results = search_multiple_sources(query_data["query"], selected_sources)

                    # Añadir búsqueda histórica si hay dominios
                    if search_domain:
                        # Buscar archivo histórico del dominio
                        archive_results = archive_search.search_web_archives(search_domain, ["wayback", "archive"])
                        search_results["archive_history"] = archive_results

                    # Guardar resultados en sesión
                    st.session_state['search_results'] = search_results
                    st.session_state['search_criteria'] = query_data
                    st.session_state['search_timestamp'] = time.time()

                st.success(f"✅ Búsqueda completada con resultados de múltiples fuentes")

            except Exception as e:
                st.error(f"❌ Error en búsqueda: {str(e)}")
                logger.error(f"Error en búsqueda avanzada: {e}")

    with col_actions[1]:
        if st.button("🔄 Limpiar", use_container_width=True,
                     key="btn_clear", help="Limpiar todos los campos"):
            st.session_state['search_name'] = ""
            st.session_state['search_email'] = ""
            st.session_state['search_location'] = ""
            st.session_state['search_phone'] = ""
            st.session_state['search_company'] = ""
            st.session_state['search_role'] = ""
            st.session_state['search_results'] = None
            st.rerun()  # Cambiado de experimental_rerun a rerun

    with col_actions[2]:
        if st.button("🧩 Analizar Relaciones", use_container_width=True,
                     key="btn_analyze", help="Analizar posibles relaciones"):
            # Esta función puede requerir datos de personas previamente buscadas
            st.info("🔍 Función de análisis de relaciones en desarrollo")
            st.session_state['page'] = 'relationship_analysis'
            st.session_state['force_reload'] = True
            st.rerun()

    with col_actions[3]:
        if st.button("📊 Exportar Resultados", use_container_width=True,
                     key="btn_export", help="Exportar resultados a archivo"):
            st.info("📁 Exportación de resultados en desarrollo")

    # Mostrar resultados si existen
    if 'search_results' in st.session_state and st.session_state['search_results']:
        st.markdown("---")
        st.subheader("📊 Resultados de Búsqueda")

        results = st.session_state['search_results']
        total_count = 0

        # Mostrar resultados organizados por fuente
        for source_type, source_results in results.items():
            if isinstance(source_results, dict) and source_results.get('error'):
                st.markdown(f"""
                    <div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <strong>⚠️ Error en {source_type}:</strong> {source_results['error']}
                    </div>
                """, unsafe_allow_html=True)
                continue

            try:
                # Procesar resultados por tipo
                if source_type == 'people' and isinstance(source_results, dict):
                    st.markdown(f"### 👥 Resultados de Personas")
                    if 'results' in source_results:
                        person_results = source_results['results']
                        total_count += len(person_results)

                        for i, person in enumerate(person_results):
                            # Card moderno para cada persona
                            if isinstance(person, dict) and 'name' in person:
                                person_name = person.get('name', 'Nombre desconocido')
                                person_email = person.get('email', 'N/A')
                                person_phone = person.get('phone', 'N/A')
                                person_location = person.get('location', 'N/A')
                                person_confidence = person.get('confidence', 0.8)

                                person_card = f"""
                                <div style="border: 1px solid #e9ecef; border-radius: 12px; padding: 20px; margin-bottom: 15px; 
                                           background: white; box-shadow: 0 3px 10px rgba(0,0,0,0.08);">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                        <div>
                                            <h3 style="margin: 0; color: #2c3e50; font-size: 18px;">{person_name}</h3>
                                            <p style="color: #7f8c8d; margin: 5px 0; font-size: 14px;">
                                                <strong>Email:</strong> {person_email}<br/>
                                                <strong>Teléfono:</strong> {person_phone}<br/>
                                                <strong>Ubicación:</strong> {person_location}
                                            </p>
                                        </div>
                                        <div style="text-align: right;">
                                            <span style="display: block; background: #28a745; color: white; 
                                                       padding: 5px 10px; border-radius: 15px; font-size: 12px;">
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
                                        <button onclick="handleAnalyzeRelationship('{json.dumps(person).replace(chr(34), '&quot;')}')" 
                                                style="background: #17a2b8; color: white; border: none; padding: 8px 15px; 
                                                       border-radius: 6px; cursor: pointer; font-size: 14px;" 
                                                class="analyze-btn-{i}">
                                            🔍 Analizar Relación
                                        </button>
                                    </div>
                                </div>
                                """
                                st.markdown(person_card, unsafe_allow_html=True)

                elif source_type == 'email' and isinstance(source_results, dict):
                    st.markdown(f"### 📧 Resultados de Email")
                    # Mostrar resultados de email
                    if 'results' in source_results:
                        email_results = source_results['results']
                        total_count += len(email_results)

                        for i, email_info in enumerate(email_results):
                            # Mostrar información real del email
                            email_value = email_info.get('email', 'Email')
                            breach_value = email_info.get('breached', False) or email_info.get('breach_count', 0) > 0
                            breach_count = email_info.get('breach_count', 0)
                            sources_list = str(email_info.get('sources', [])) if 'sources' in email_info else 'API'

                            email_card = f"""
                            <div style="border: 1px solid #e9ecef; border-radius: 12px; padding: 15px; margin-bottom: 10px; 
                                       background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                                <div style="display: flex; justify-content: space-between;">
                                    <h4 style="margin: 0; color: #2c3e50;">{email_value}</h4>
                                    <span style="background: {'#28a745' if breach_value or breach_count > 0 else '#ffc107'}; 
                                               color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">
                                        {'Comprometido' if breach_value or breach_count > 0 else 'Seguro'}
                                    </span>
                                </div>
                                <p style="color: #7f8c8d; margin: 5px 0; font-size: 14px;">
                                    <strong>Breaches:</strong> {breach_count}<br/>
                                    <strong>Fuente:</strong> {sources_list}
                                </p>
                            </div>
                            """
                            st.markdown(email_card, unsafe_allow_html=True)

                elif source_type == 'social' and isinstance(source_results, dict):
                    st.markdown(f"### 📱 Resultados de Redes Sociales")
                    if 'results' in source_results:
                        social_results = source_results['results']
                        total_count += len(social_results)

                        for i, social_data in enumerate(social_results):
                            # Mostrar resultados reales de redes sociales
                            username_value = social_data.get('username', 'Usuario')
                            platform_value = social_data.get('platform', 'N/A')
                            followers_value = social_data.get('followers', 'N/A')
                            posts_value = social_data.get('posts', 'N/A')
                            verified_value = social_data.get('verified', False)

                            social_card = f"""
                            <div style="border: 1px solid #e9ecef; border-radius: 12px; padding: 15px; margin-bottom: 10px; 
                                       background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                                <div style="display: flex; align-items: center;">
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0; color: #2c3e50;">@{username_value}</h4>
                                        <p style="color: #7f8c8d; margin: 5px 0; font-size: 14px;">
                                            <strong>Plataforma:</strong> {platform_value}<br/>
                                            <strong>Seguidores:</strong> {followers_value}<br/>
                                            <strong>Posteos:</strong> {posts_value}
                                        </p>
                                    </div>
                                    <div style="text-align: right;">
                                        <span style="display: block; background: #007bff; color: white; 
                                                   padding: 5px 10px; border-radius: 15px; font-size: 12px;">
                                            {'Verificado' if verified_value else 'No verificado'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            """
                            st.markdown(social_card, unsafe_allow_html=True)

                # Mostrar resultados historiales si existen
                elif source_type == 'archive_history':
                    st.markdown(f"### 📜 Historial Histórico")
                    if isinstance(source_results, dict):
                        for archive_source, archive_results in source_results.items():
                            if isinstance(archive_results, list) and archive_results:
                                st.markdown(f"#### {archive_source.upper()} Capturas")
                                for i, capture in enumerate(archive_results[:3]):  # Solo mostrar 3 por página
                                    if 'error' not in capture and 'url' in capture:
                                        details = capture.get('timestamp_human', capture.get('url', 'Unknown'))
                                        st.markdown(f"""
                                        <div style="border: 1px solid #e9ecef; border-radius: 8px; padding: 10px; margin-bottom: 10px; 
                                                   background: #f8f9fa;">
                                            <h5 style="margin: 0; color: #2c3e50;">{details}</h5>
                                            <a href="{capture.get('url', '#')}" target="_blank" style="color: #3498db;">
                                                🌐 Ver captura completa
                                            </a>
                                            {f'<p style="color: #7f8c8d; font-size: 14px;">Confianza: {capture.get("confidence", 0.9):.2f}</p>' if 'confidence' in capture else ''}
                                        </div>
                                        """, unsafe_allow_html=True)

            except Exception as e:
                st.warning(f"Error al mostrar resultados de {source_type}: {str(e)}")

        # Mostrar estadísticas de búsqueda
        if total_count > 0:
            st.markdown(f"### 📊 Estadísticas")
            st.info(f"🔍 Total de resultados encontrados: **{total_count}**")
            st.success("✅ Búsqueda realizada con éxito!")

    # Sección de análisis de relaciones
    if 'search_results' in st.session_state and st.session_state['search_results']:
        st.markdown("---")
        st.subheader("🔗 Análisis de Relaciones")

        with st.expander("🔍 Analizar posibles relaciones", expanded=False):
            st.write("Analiza automáticamente posibles conexiones entre personas encontradas:")

            if st.button("🔍 Encontrar Conexiones", key="find_connections_btn"):
                # Ejemplo de usar el sistema de conexiones
                st.info("🔄 Procesando conexiones posibles...")
                # Aquí iría conexión real con el sistema de relaciones

            if st.button("🔗 Detectar Tipos", key="detect_types_btn"):
                st.info("🔎 Detectando tipos de relación...")
                # Aquí iría detección real

    # Botón para volver al dashboard
    if st.button(" ← Volver al Dashboard", use_container_width=True):
        st.session_state['page'] = 'dashboard'
        st.session_state['search_results'] = None
        st.rerun()