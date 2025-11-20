# ui/pages/login.py

import streamlit as st
from core.auth_manager import authenticate_user, register_user
from ui.utils.helpers import set_current_user_id, get_current_user_id
from core.db_manager import get_user_by_username
import logging

logger = logging.getLogger(__name__)


def show_login_with_tabs():
    """
    Pantalla de login con pestañas para login y registro
    """

    # Contenido principal sin sidebar
    # For the login and registration screens we override the global
    # background style.  Streamlit renders the app inside an element
    # with the class `stApp`; by injecting CSS here we make the
    # background darker and more in line with the rest of the app.
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        body {
            /* Fondo en degradado azul oscuro para que la página de inicio no se vea tan blanca */
            background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }
        .login-container {
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh;
            padding: 20px;
        }
        .login-form {
            width: 100%;
            max-width: 500px; 
            padding: 40px; 
            background: white; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.25); 
            position: relative; 
            overflow: hidden;
            margin-top: 20px;
        }
        .login-header {
            position: relative; 
            z-index: 1; 
            text-align: center; 
            margin-bottom: 30px;
        }
        .decor-bg-1 {
            position: absolute; 
            top: -30px; 
            right: -30px; 
            width: 100px; 
            height: 100px; 
            /* Elemento decorativo en tonos azules */
            background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%); 
            border-radius: 50%; 
            opacity: 0.15;
        }
        .decor-bg-2 {
            position: absolute; 
            bottom: -20px; 
            left: -20px; 
            width: 80px; 
            height: 80px; 
            background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%); 
            border-radius: 50%; 
            opacity: 0.15;
        }
        </style>
        <div class="login-container">
            <div class="login-form">
                <div class="decor-bg-1"></div>
                <div class="decor-bg-2"></div>
                <div class="login-header">
                    <h1 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 32px;">
                        <span style="color: #3498db;">Quasar</span><span style="color: #e74c3c;">III</span>
                    </h1>
                    <p style="color: #7f8c8d; margin: 0;">Plataforma Profesional OSINT</p>
                </div>
    """, unsafe_allow_html=True)

    # Pestañas para login y registro
    tab1, tab2 = st.tabs(["🔐 Iniciar Sesión", "🆕 Registrarse"])

    with tab1:  # Pestaña de login
        st.subheader("Acceso al Sistema")
        username = st.text_input("Nombre de Usuario", key="login_username",
                                 placeholder="Introduce tu nombre de usuario",
                                 label_visibility="collapsed")

        password = st.text_input("Contraseña", type='password', key="login_password",
                                 placeholder="Introduce tu contraseña",
                                 label_visibility="collapsed")

        if st.button("Iniciar Sesión", use_container_width=True, key="login_submit"):
            if username and password:
                user_id = authenticate_user(username, password)
                if user_id:
                    st.session_state['authenticated'] = True
                    st.session_state['current_user_id'] = user_id
                    st.session_state['current_user'] = {"username": username}
                    st.success(f"✅ ¡Bienvenido, {username}! Acceso autorizado.")
                    # Recargar la página para mostrar el dashboard
                    st.rerun()  # Cambiado de experimental_rerun() a rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
                    logger.warning(f"Fallo en inicio de sesion para usuario: {username}")
            else:
                st.warning("⚠️ Por favor, complete todos los campos")

    with tab2:  # Pestaña de registro
        st.subheader("Crear Cuenta")
        new_username = st.text_input("Nombre de Usuario", key="register_username",
                                     placeholder="Nombre de usuario",
                                     label_visibility="collapsed")

        new_email = st.text_input("Correo Electrónico", key="register_email",
                                  placeholder="tu@email.com",
                                  label_visibility="collapsed")

        new_password = st.text_input("Contraseña", type='password', key="register_password",
                                     placeholder="Contraseña segura",
                                     label_visibility="collapsed")

        confirm_password = st.text_input("Confirmar Contraseña", type='password', key="confirm_password",
                                         placeholder="Confirma tu contraseña",
                                         label_visibility="collapsed")

        if st.button("Registrarse", use_container_width=True, key="register_submit"):
            if new_username and new_email and new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                    return

                success = register_user(new_username, new_email, new_password)
                if success:
                    st.success("✅ ¡Registro exitoso! Ahora puedes iniciar sesión.")
                    logger.info(f"Nuevo usuario registrado: {new_username}")
                    st.session_state['active_tab'] = 'login'  # Ir al login tras registro
                    # Redirigir a pestaña de login
                    st.rerun()  # Cambiado de experimental_rerun() a rerun()
                else:
                    st.error("❌ El nombre de usuario o correo electrónico ya están en uso.")
                    logger.warning(f"Fallo en registro para usuario: {new_username}")
            else:
                st.warning("⚠️ Por favor, complete todos los campos")

    st.markdown("""
            </div>
        </div>
    """, unsafe_allow_html=True)