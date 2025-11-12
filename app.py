import time

import streamlit as st

# Importar managers
from auth import AuthManager
from config_manager import ConfigManager
from db_manager import DatabaseManager
from modules.alert_system import AlertOrchestrator, WorkflowEngine
from modules.batch_search import BatchSearchOrchestrator
from modules.proxy_manager import ProxyManager

# Configuración de página
st.set_page_config(
    page_title="OSINT Framework Pro",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
.stButton>button {
    background-color: #1f4e79;
    color: white;
    font-weight: bold;
}
.stProgress > div > div > div > div {
    background-color: #2e75b6;
}
</style>
""", unsafe_allow_html=True)

# Inicializar managers
db = DatabaseManager()
auth = AuthManager(db)
config = ConfigManager()

# Estado de sesión
if 'page' not in st.session_state:
    st.session_state.page = "login"
if 'user' not in st.session_state:
    st.session_state.user = None


# Navbar de autenticación
def render_navbar():
    if st.session_state.user:
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

        with col2:
            if st.button("⚙️ Config", use_container_width=True):
                st.session_state.page = "config"

        with col3:
            if st.button("🚨 Alerts", use_container_width=True):
                st.session_state.page = "alerts"

        with col4:
            if st.button("📊 Batch", use_container_width=True):
                st.session_state.page = "batch"

        with col5:
            if st.button("🚪 Salir", use_container_width=True):
                auth.logout()
                st.session_state.user = None
                st.session_state.page = "login"
                st.rerun()


# --- PÁGINAS PRINCIPALES ---

def login_page():
    st.title("🔐 OSINT Framework Pro")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Iniciar Sesión", type="primary")

    if submitted:
        success, token, message = auth.login(username, password)
        if success:
            st.session_state.token = token
            st.session_state.user = auth.verify_jwt_token(token)
            st.session_state.page = "dashboard"
            st.success("✅ Login exitoso")
            st.rerun()
        else:
            st.error(message)

    st.markdown("---")
    if st.button("Registrarse"):
        st.session_state.page = "register"
        st.rerun()


def register_page():
    st.title("📝 Registro de Usuario")

    with st.form("register_form"):
        username = st.text_input("Username", placeholder="min 3 chars")
        email = st.text_input("Email", placeholder="user@example.com")
        password = st.text_input("Password", type="password", placeholder="min 8 chars")
        confirm = st.text_input("Confirmar Password", type="password")
        submitted = st.form_submit_button("Registrar", type="primary")

    if submitted:
        if password != confirm:
            st.error("❌ Contraseñas no coinciden")
        elif len(password) < 8:
            st.error("❌ Contraseña debe tener 8+ caracteres")
        else:
            success, message = auth.register(username, email, password)
            if success:
                st.success("✅ Usuario creado! Inicia sesión")
                time.sleep(2)
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error(message)


def dashboard():
    st.title(f"🕵️ Dashboard - {st.session_state.user['username']}")

    # Navbar
    render_navbar()

    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Búsquedas", db.get_total_searches(st.session_state.user['id']))
    col2.metric("Targets Únicos", db.get_unique_targets_count(st.session_state.user['id']))
    col3.metric("Alertas", db.get_unread_alerts_count(st.session_state.user['id']))
    col4.metric("Success Rate", f"{db.get_success_rate(st.session_state.user['id']):.1f}%")

    # Módulos principales
    st.markdown("---")
    st.subheader("🔍 Seleccionar Módulo")

    modules = {
        "general_search": "🔍 Búsqueda General",
        "socmint": "📱 SOCMINT",
        "breachdata": "🔓 Breaches",
        "emailint": "📧 Email Intel",
        "domainint": "🌐 Domains",
        "phoneint": "📞 Phone Intel",
        "imageint": "🖼️ Images",
        "geoint": "🗺️ Geo Intel",
    }

    selected_module = st.selectbox("Módulo", list(modules.keys()), format_func=lambda x: modules[x])

    # Render UI del módulo
    try:
        module = __import__(f"modules.{selected_module}", fromlist=[selected_module])
        orchestrator_class = getattr(module, f"{selected_module.capitalize()}Orchestrator")
        orchestrator = orchestrator_class(st.session_state.user['id'], db, config)
        orchestrator.render_ui()
    except Exception as e:
        st.error(f"Error cargando módulo: {e}")


def alerts_page():
    st.title("🚨 Alertas & Workflows")

    tab1, tab2 = st.tabs(["Alertas", "Workflows"])

    with tab1:
        alert_orchestrator = AlertOrchestrator(
            st.session_state.user['id'],
            db,
            config,
            ProxyManager(st.session_state.user['id'], db)
        )
        alert_orchestrator.render_ui()

    with tab2:
        workflow_engine = WorkflowEngine(
            st.session_state.user['id'],
            db,
            config,
            alert_orchestrator
        )
        workflow_engine.render_ui()


def batch_page():
    st.title("📊 Batch Search")

    batch_orchestrator = BatchSearchOrchestrator(
        st.session_state.user['id'],
        db,
        config
    )
    batch_orchestrator.render_ui()


def config_page():
    st.title("⚙️ Configuración")

    # Claves API
    st.subheader("🔑 API Keys")

    services = [
        ("HaveIBeenPwned", "API para breaches"),
        ("VirusTotal", "Análisis de URLs y dominios"),
        ("Shodan", "Búsqueda de dispositivos"),
        ("Hunter", "Email intelligence"),
        ("SMTPConfig", "Notificaciones email"),
    ]

    for service_name, description in services:
        with st.expander(f"**{service_name}** - {description}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                key_value = st.text_input(
                    service_name,
                    type="password",
                    key=f"api_key_{service_name}"
                )
            with col2:
                if st.button("Guardar", key=f"save_{service_name}"):
                    if key_value:
                        encrypted = config.encrypt_api_key(key_value)
                        db.save_api_key(st.session_state.user['id'], service_name, encrypted)
                        st.success("✅ Guardado")
                    else:
                        st.error("❌ Valor vacío")


# Control de navegación
if not st.session_state.user:
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "register":
        register_page()
else:
    render_navbar()

    if st.session_state.page == "dashboard":
        dashboard()
    elif st.session_state.page == "alerts":
        alerts_page()
    elif st.session_state.page == "batch":
        batch_page()
    elif st.session_state.page == "config":
        config_page()