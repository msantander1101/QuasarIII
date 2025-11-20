# ui/pages/register.py

import streamlit as st
from core.auth_manager import register_user
import logging

logger = logging.getLogger(__name__)


def show_register_page():
    """
    Pantalla de registro (ahora como parte de las pestañas en login)
    Esta función ya no se usa directamente, pero puede mantenerse por compatibilidad
    """

    st.markdown("""
        <div style="
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            /* Dejar el fondo transparente para mostrar el fondo global */
            background: transparent;
        ">
            <div style="width: 100%; max-width: 400px; padding: 30px; background: #ffffff; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h2 style="color: #495057; margin: 0; font-size: 28px;">🆕 Registrar Cuenta</h2>
                    <p style="color: #6c757d; margin-top: 10px;">Crea tu cuenta profesional</p>
                </div>

                <form>
    """, unsafe_allow_html=True)

    # Campos de registro con diseño moderno
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
            else:
                st.error("❌ El nombre de usuario o correo electrónico ya están en uso.")
                logger.warning(f"Fallo en registro para usuario: {new_username}")
        else:
            st.warning("⚠️ Por favor, complete todos los campos.")

    st.markdown("""
    </form>
    <div style="text-align: center; margin-top: 20px;">
        <p style="color: #6c757d; font-size: 14px;">
            ¿Ya tienes cuenta? <a href="#" style="color: #667eea; text-decoration: none;">Inicia sesión aquí</a>
        </p>
    </div>
    </div>
    </div>  
    """, unsafe_allow_html=True)