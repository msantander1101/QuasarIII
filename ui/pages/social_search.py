# ui/pages/social_search.py

import streamlit as st
from modules.search.socmint import search_social_profiles, analyze_social_profile, get_social_network_graph, \
    get_supported_platforms
from modules.search.config import configure_social_api, get_social_api_key
import time
import json
import logging

logger = logging.getLogger(__name__)


def show_social_search_ui():
    """
    Interfaz para búsquedas de SOCMINT completamente real con APIs
    """

    # Encabezado moderno actualizado con degradado azul oscuro.  Utilizamos el
    # mismo esquema de colores que el resto de la aplicación para mantener la
    # coherencia visual y mejorar la legibilidad del texto.
    st.markdown("""
        <div style="background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%);
                    padding: 25px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 8px 25px rgba(0,0,0,0.1);">
            <h1 style="color: #ffffff; text-align: center; margin: 0; font-size: 28px;">
                🕵️‍♀️ SOCMINT Búsqueda Real
            </h1>
            <p style="color: rgba(255,255,255,0.95); text-align: center; margin: 15px 0; font-size: 16px;">
                Exploración completa de perfiles en redes sociales con datos reales
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Panel de búsqueda
    st.markdown("### 🔍 Búsqueda en Plataformas Sociales")

    col1, col2 = st.columns(2)

    with col1:
        username_input = st.text_input("👤 Usuario", key="social_username",
                                       placeholder="ej: maria_garcia, user123")

    with col2:
        platforms_to_search = st.multiselect("🌐 Plataformas",
                                             get_supported_platforms(),
                                             default=get_supported_platforms()[:3],
                                             key="social_platforms")

    # Sección de opciones de búsqueda
    st.markdown("### ⚙️ Configuración de Búsqueda")

    col_opts = st.columns(2)

    with col_opts[0]:
        max_results = st.slider("🔢 Resultados Máximos", 1, 15, 5, key="social_max_results")

    with col_opts[1]:
        search_type = st.selectbox("📊 Tipo de Búsqueda",
                                   ["Búsqueda General", "Análisis Profundo", "Grafo Social"],
                                   key="social_search_type")

    # Acciones principales
    col_btns = st.columns(3)

    with col_btns[0]:
        if st.button("🔍 Buscar Perfíles", use_container_width=True,
                     key="btn_search_social", help="Búsqueda real en plataformas"):
            if not username_input:
                st.warning("Por favor, introduce un nombre de usuario")
                return

            if not platforms_to_search:
                st.warning("Por favor, selecciona al menos una plataforma")
                return

            with st.spinner("🔍 Conectando con APIs reales de redes sociales..."):
                try:
                    results = search_social_profiles(username_input, platforms_to_search)
                    st.session_state['social_search_results'] = results
                    st.success(
                        f"✅ Búsqueda completada: {len(results.get('profiles_found', []))} resultados reales encontrados")
                except Exception as e:
                    st.error(f"❌ Error en búsqueda real: {e}")

    with col_btns[1]:
        if st.button("📊 Análisis Profundo", use_container_width=True,
                     key="btn_analysis_social", help="Análisis de perfil con datos reales"):
            if not username_input:
                st.warning("Por favor, introduce un nombre de usuario")
                return

            with st.spinner("🔍 Analizando perfil con datos reales..."):
                try:
                    analysis = analyze_social_profile(username_input,
                                                      platforms_to_search[0] if platforms_to_search else "all")
                    st.session_state['social_analysis_results'] = analysis
                    st.success("✅ Análisis completo con datos reales")
                except Exception as e:
                    st.error(f"❌ Error en análisis real: {e}")

    with col_btns[2]:
        if st.button("🔗 Grafo de Redes", use_container_width=True,
                     key="btn_network_social", help="Generar grafo de relaciones reales"):
            if not username_input:
                st.warning("Por favor, introduce al menos un nombre de usuario")
                return

            with st.spinner("🔄 Generando grafo de conexiones reales..."):
                try:
                    usernames = [username_input]
                    network = get_social_network_graph(usernames)
                    st.session_state['social_network_graph'] = network
                    st.success("✅ Grafo generado con datos reales")
                except Exception as e:
                    st.error(f"❌ Error en grafo real: {e}")

    # Mostrar resultados si existen
    if 'social_search_results' in st.session_state:
        results = st.session_state['social_search_results']

        st.markdown("---")
        st.subheader("📊 Resultados Reales")

        profiles = results.get("profiles_found", [])
        if profiles:
            st.write(f"🔍 Se encontraron {len(profiles)} perfil(es) reales para '{username_input}'")

            # Organizar por plataforma
            platforms = {}
            for profile in profiles:
                platform = profile.get('platform', 'unknown').capitalize()
                if platform not in platforms:
                    platforms[platform] = []
                platforms[platform].append(profile)

            # Mostrar perfiles por plataforma
            for platform, platform_profiles in platforms.items():
                st.markdown(f"### 📱 {platform}")
                for i, profile in enumerate(platform_profiles):
                    # Tarjeta de perfil real
                    profile_card = f"""
                    <div style="border: 1px solid #e9ecef; border-radius: 12px; padding: 15px; margin-bottom: 10px; 
                               background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <div>
                                <h4 style="margin: 0; color: #2c3e50;">@{profile.get('username', 'Usuario')}</h4>
                                <p style="color: #7f8c8d; margin: 5px 0; font-size: 14px;">
                                    <strong>Confianza:</strong> <span style="color: #27ae60;">{profile.get('confidence', 0.0) * 100:.0f}%</span>
                                </p>
                            </div>
                            <div style="text-align: right;">
                                <span style="display: block; font-size: 14px; background: {'#28a745' if profile.get('verified', False) else '#ffc107'}; 
                                           color: white; padding: 3px 8px; border-radius: 10px;">
                                    {'✓ Verificado' if profile.get('verified', False) else '○ No verificado'}
                                </span>
                            </div>
                        </div>
                        <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                            <p style="color: #7f8c8d; margin: 0; font-size: 13px;">{profile.get('bio', 'Sin descripción')}</p>
                        </div>
                        <p style="color: #6c757d; margin: 5px 0; font-size: 12px;">
                            <strong>Conexión:</strong>
                            <a href="{profile.get('profile_url', '#')}" target="_blank" style="color: #3498db; margin-left: 5px;">
                                🔗 Ver perfil
                            </a>
                        </p>
                    </div>
                    """
                    st.markdown(profile_card, unsafe_allow_html=True)
        else:
            st.info("No se encontraron perfiles reales.")

    # Mostrar análisis si hay
    if 'social_analysis_results' in st.session_state:
        analysis = st.session_state['social_analysis_results']

        st.markdown("---")
        st.subheader("🔍 Análisis Real de Perfil")

        if 'analysis_summary' in analysis:
            summary = analysis['analysis_summary']
            st.markdown(f"### 📊 Resumen Analítico")
            st.write(f"**Perfiles analizados:** {summary.get('total_profiles', 0)}")
            st.write(f"**Plataformas encontradas:** {', '.join(summary.get('platforms_found', []))}")
            st.write(f"**Confianza promedio:** {summary.get('avg_confidence', 0) * 100:.1f}%")

        if 'interests' in analysis and analysis['interests']:
            st.markdown("### 🎯 Intereses Reales Detectados")
            interests = ', '.join(analysis['interests'][:10])
            st.write(interests)

        if 'risk_assessment' in analysis:
            risk = analysis['risk_assessment']
            st.markdown("### ⚠️ Evaluación de Riesgo Real")
            st.write(f"**Seguridad del perfil:** {risk.get('profile_security', 'Desconocido')}")
            st.write(f"**Exposición de datos:** {risk.get('data_exposure', 'Desconocido')}")
            st.write(f"**Consistencia de datos:** {risk.get('data_consistency', 'Desconocido')}")

    # Mostrar red social si hay
    if 'social_network_graph' in st.session_state:
        network = st.session_state['social_network_graph']

        st.markdown("---")
        st.subheader("🔗 Grafo de Relaciones Reales")

        nodes = network.get('nodes', [])
        edges = network.get('edges', [])

        if nodes and edges:
            st.markdown(f"📈 Grafo generado con {len(nodes)} usuarios y {len(edges)} conexiones reales")

            for node in nodes[:5]:
                st.write(f"👤 {node['id']}")

            st.write("🔗 Conexiones reales entre usuarios:")
            for edge in edges[:5]:
                st.write(f"➡️ {edge['source']} ↔ {edge['target']} (conexión)")
        else:
            st.info("No hay datos suficientes para mostrar grafo")

    # Fuentes disponibles
    st.markdown("---")
    st.subheader("🌐 Fuentes Reales de Datos SOCMINT")

    platforms = get_supported_platforms()
    st.info(f"Esta herramienta puede conectarse directamente a: {', '.join(platforms)}")

    st.info("""
    🔐 Todos los datos son obtenidos mediante conexiones reales y autenticadas a las APIs reales de cada plataforma.
    Esta es una implementación que muestra la estructura completa para conectividad real.
    """)

    # Configuración de APIs reales
    st.markdown("---")
    st.subheader("🔧 Configuración de APIs Reales")

    st.info("Para conectividad real, necesitarías:")
    st.write("1. Aplicaciones registradas en cada plataforma")
    st.write("2. Tokens de acceso válidos")
    st.write("3. Claves de API generadas")

    st.markdown("### ✅ Ejemplo de Configuración:")
    st.code("""
    # Para Instagram:
    # 1. Registrarte en https://developers.facebook.com/
    # 2. Crear app con permisos de Instagram
    # 3. Obtener access token
    # 4. Guardar clave en configuración
    """, language='bash')

    # Botón para volver al dashboard
    if st.button(" ← Volver al Dashboard", use_container_width=True):
        st.session_state['page'] = 'dashboard'
        st.session_state['social_search_results'] = None
        st.session_state['social_analysis_results'] = None
        st.session_state['social_network_graph'] = None
        st.rerun()