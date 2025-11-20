# ui/pages/settings.py

import streamlit as st
from core.config_manager import config_manager
from core.db_manager import get_user_by_id
import logging

logger = logging.getLogger(__name__)


def show_settings_page():
    """
    Página de configuración completa con gestor de API Keys
    """

    st.markdown("""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                    padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="color: white; text-align: center; margin: 0;">
                ⚙️ Configuración de API Keys
            </h1>
            <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 10px 0;">
                Administra tus claves API para integraciones avanzadas
            </p>
        </div>
    """, unsafe_allow_html=True)

    user_id = st.session_state.get('current_user_id', None)
    if not user_id:
        st.error("No puedes acceder a configuración sin inicio de sesión.")
        return

    # Verificar si el usuario ha sido autenticado y recuperado correctamente (más seguridad)
    user_info = get_user_by_id(user_id)
    if not user_info:
        st.error("No se pudieron obtener los datos del usuario.")
        return

    username = user_info[1]  # El segundo elemento es el nombre de usuario

    # --- Lista de API Keys disponibles ---
    st.markdown("### 🔑 Claves API Disponibles")

    api_keys_config = {
        "serpapi": "🔍 SerpAPI (Google Search)",
        "google_api_key": "🌐 Google Custom Search API",
        "google_cse_cx": "🧩 Google CSE CX ID",
        "hibp": "💀 Have I Been Pwned",
        "hunter": "📧 Hunter.io",
        "whoisxml": "🌍 WhoisXML API",
        "shodan": "🕷️ Shodan",
        "virustotal": "🧬 VirusTotal",
        "openai_api_key": "🧠 OpenAI / GPT API Key",
        "instagram_api_key": "📸 Instagram API",
        "tiktok_api_key": "🎵 TikTok API",
        "youtube_api_key": "📺 YouTube API",
        "twitter_api_key": "🐦 Twitter API",
        "linkedin_api_key": "💼 LinkedIn API",
        "facebook_api_key": "📘 Facebook API",
        "reddit_api_key": "📊 Reddit API"
    }

    st.markdown("#### ✅ Configuración Actual")
    current_configs = config_manager.list_configs(user_id)

    if current_configs:
        st.write("Las siguientes claves están configuradas:")
        for item in current_configs:
            # Mostrar solo el nombre de la clave, no el valor
            st.markdown(f"- **{item['config_key']}** (modificada: {item['updated_at']})")
    else:
        st.info("No tienes claves API configuradas aún.")

    # --- Agregar o modificar clave ---
    st.markdown("### ➕ Configurar Nueva API Key")

    # Seleccionar tipo de clave
    selected_api = st.selectbox(
        "Selecciona el servicio API",
        list(api_keys_config.keys()),
        format_func=lambda x: api_keys_config[x],
        key="select_api_key"
    )

    # Obtener nombre legible del servicio
    api_name = api_keys_config[selected_api]

    # Valor de la clave
    api_value = st.text_input(
        f"Valor de la clave para {api_name}",
        type='password',
        key=f"api_value_{selected_api}",
        placeholder="Introduce tu clave API..."
    )

    # Ayuda contextual por cada API
    help_texts = {
        "serpapi": "Clave para búsqueda de Google Search con SerpAPI",
        "google_api_key": "API key para Google Custom Search",
        "google_cse_cx": "Identificador de motor de búsqueda personalizado",
        "hibp": "Clave API para Have I Been Pwned (recomendado)",
        "hunter": "Clave API para Hunter.io (email verification)",
        "whoisxml": "Clave API para WhoisXML (WHOIS information)",
        "shodan": "Clave API para Shodan (network scanner)",
        "virustotal": "Clave API para VirusTotal (malware detection)",
        "openai_api_key": "Clave API para OpenAI/GPT (IA integrada)",
        "instagram_api_key": "Clave API para Instagram (integración SOCMINT)",
        "tiktok_api_key": "Clave API para TikTok (integración SOCMINT)",
        "youtube_api_key": "Clave API para YouTube (integración SOCMINT)",
        "twitter_api_key": "Clave API para Twitter (integración SOCMINT)",
        "linkedin_api_key": "Clave API para LinkedIn (integración SOCMINT)",
        "facebook_api_key": "Clave API para Facebook (integración SOCMINT)",
        "reddit_api_key": "Clave API para Reddit (integración SOCMINT)"
    }

    if st.button("💾 Guardar Clave API", key="save_api_button"):
        if selected_api and api_value:
            success = config_manager.save_config(user_id, selected_api, api_value)
            if success:
                st.success(f"✅ Clave API '{selected_api}' guardada correctamente.")
                st.rerun()  # Recarga para reflejar cambio
            else:
                st.error("❌ Error al guardar la clave.")
                logger.error(f"Fallo al guardar configuracion para usuario {user_id} clave {selected_api}")
        else:
            st.warning("⚠️ Por favor ingresa el tipo de clave y su valor.")

    # --- Eliminar claves existentes ---
    st.markdown("### ❌ Eliminar Clave API Existente")

    # Mostrar claves existentes para eliminar
    existing_keys = [item['config_key'] for item in current_configs]
    if existing_keys:
        remove_key = st.selectbox(
            "Selecciona una clave para eliminar",
            existing_keys,
            key="delete_key_selector",
            format_func=lambda x: f"{x} - {api_keys_config.get(x, 'Clave desconocida')}"
        )
        if st.button("🗑️ Eliminar Clave Seleccionada", key="delete_button"):
            deleted = config_manager.delete_config(user_id, remove_key)
            if deleted:
                st.success(f"✅ Clave '{remove_key}' eliminada.")
                st.rerun()  # Recarga para reflejar cambio
            else:
                st.error("❌ Error al eliminar la clave.")
                logger.error(f"Fallo al borrar configuracion para usuario {user_id} clave {remove_key}")
    else:
        st.info("No tienes claves que eliminar.")

    # --- Status de las claves requeridas ---
    st.markdown("### 📊 Estado de API Keys Requeridas")

    required_keys = [
        "hibp",  # Obligatoria para verificación de emails
        "openai_api_key",  # Obligatoria para AI integrada
        "instagram_api_key",
        "tiktok_api_key",
        "youtube_api_key",
        "twitter_api_key",
        "linkedin_api_key"
    ]

    required_status = {key: config_manager.get_config(user_id, key) for key in required_keys}
    all_required = all(required_status.values())

    status_text = "✅ Todas las claves requeridas están configuradas." if all_required else "❌ Faltan claves requeridas."
    st.markdown(f"**{status_text}**")

    # Mostrar un resumen con estado
    st.write("Estado de claves obligatorias:")
    for k, v in required_status.items():
        status_icon = "✅" if v else "❌"
        status_msg = "Configurada" if v else "Faltante"
        st.write(f"  {status_icon} `{k}`: {status_msg}")

    # --- Panel de ejemplo de uso ---
    st.markdown("### 📘 Ejemplo de Uso")

    st.info("""
    **Una vez configuradas las claves API, podrás:**
    - Verificar brechas de seguridad en correos con Have I Been Pwned
    - Realizar búsquedas avanzadas con Google Search API
    - Verificar información de dominios con WhoisXML
    - Hacer búsquedas de personas con Hunter.io
    - Usar inteligencia artificial con OpenAI/GPT
    - Realizar búsquedas en redes sociales con integación SOCMINT
    """)

    # Botón para volver al dashboard
    if st.button(" ← Volver al Dashboard", use_container_width=True):
        st.session_state['page'] = 'dashboard'
        st.rerun()