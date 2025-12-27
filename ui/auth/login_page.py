# ui/auth/login_page.py

import streamlit as st
from core.auth_manager import auth_manager, User


def show_login_page() -> User | None:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#141e30,#243b55);
                padding:22px;border-radius:14px;margin-bottom:20px">
        <h2 style="color:white;margin:0">🔐 QuasarIII — Acceso</h2>
        <p style="color:#d0d7ff;margin-top:8px;font-size:14px">
            Introduce tus credenciales corporativas. El registro está deshabilitado:
            el administrador da de alta las cuentas.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("👤 Usuario", key="login_username")
        password = st.text_input("🔑 Contraseña", type="password", key="login_password")
        submitted = st.form_submit_button("Entrar")

    if not submitted:
        return None

    if not username or not password:
        st.error("Introduce usuario y contraseña.")
        return None

    user = auth_manager.authenticate(username, password)
    if not user:
        st.error("Credenciales incorrectas o usuario inactivo.")
        return None

    # Guardamos en sesión
    st.session_state["current_user"] = {
        "username": user.username,
        "role": user.role,
        "is_admin": user.is_admin,
    }
    st.success(f"Bienvenido, {user.username}")
    return user
