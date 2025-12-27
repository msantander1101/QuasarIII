# ui/pages/admin_users.py
"""
Admin Users — Panel de gestión de usuarios

Solo accesible para usuarios con rol 'admin'.
Permite:
- Ver usuarios existentes
- Crear nuevos usuarios
- Activar / desactivar usuarios
- Cambiar rol (analyst/admin)
"""

from __future__ import annotations

import streamlit as st
from core.auth_manager import auth_manager, User


def _ensure_admin() -> bool:
    """Devuelve True si el usuario actual es admin, False en caso contrario."""
    info = st.session_state.get("current_user")
    if not info:
        st.error("No hay sesión activa.")
        return False
    if not info.get("is_admin"):
        st.error("Acceso restringido. Solo administradores.")
        return False
    return True


def _render_user_row(user: User, idx: int):
    cols = st.columns([2, 2, 2, 2, 2])
    with cols[0]:
        st.code(user.username, language="text")
    with cols[1]:
        st.write(user.role)
    with cols[2]:
        st.write("✅ Activo" if user.is_active else "⛔ Inactivo")

    new_role = None
    toggle_active = None

    with cols[3]:
        if st.button(
            "Hacer admin" if user.role != "admin" else "Hacer analyst",
            key=f"btn_role_{idx}",
        ):
            new_role = "admin" if user.role != "admin" else "analyst"

    with cols[4]:
        if st.button(
            "Desactivar" if user.is_active else "Activar",
            key=f"btn_active_{idx}",
        ):
            toggle_active = not user.is_active

    if new_role is not None:
        try:
            auth_manager.set_user_role(user.username, new_role)
            st.success(f"Rol actualizado: {user.username} → {new_role}")
            st.rerun()
        except Exception as e:
            st.error(f"Error cambiando rol: {e}")

    if toggle_active is not None:
        try:
            auth_manager.set_user_active(user.username, toggle_active)
            st.success(
                f"Usuario {'activado' if toggle_active else 'desactivado'}: {user.username}"
            )
            st.rerun()
        except Exception as e:
            st.error(f"Error cambiando estado: {e}")


def show_admin_users_page():
    if not _ensure_admin():
        return

    # Header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#141e30,#243b55);
                padding:22px;border-radius:14px;margin-bottom:20px">
        <h2 style="color:white;margin:0">👑 Administración de usuarios</h2>
        <p style="color:#d0d7ff;margin-top:8px;font-size:14px">
            Alta, gestión de roles y activación/desactivación de cuentas.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Botón volver al dashboard
    col_back, col_spacer = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ Volver al dashboard", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()

    # --------- Crear nuevo usuario ---------
    st.subheader("➕ Crear nuevo usuario")

    with st.form("create_user_form"):
        new_username = st.text_input("Usuario", key="admin_new_username")
        new_password = st.text_input("Contraseña", type="password", key="admin_new_password")
        new_password2 = st.text_input("Repite la contraseña", type="password", key="admin_new_password2")
        new_role = st.selectbox("Rol", options=["analyst", "admin"], index=0)
        submitted = st.form_submit_button("Crear usuario")

    if submitted:
        if not new_username or not new_password:
            st.error("Usuario y contraseña son obligatorios.")
        elif new_password != new_password2:
            st.error("Las contraseñas no coinciden.")
        else:
            try:
                user = auth_manager.create_user(
                    username=new_username,
                    password=new_password,
                    role=new_role,
                    is_active=True,
                )
                st.success(f"Usuario creado: {user.username} (rol={user.role})")
            except ValueError as ve:
                st.error(str(ve))
            except Exception as e:
                st.error(f"Error creando usuario: {e}")

    st.markdown("---")

    # --------- Listado de usuarios ---------
    st.subheader("👥 Usuarios existentes")

    users = auth_manager.list_users()
    if not users:
        st.info("No hay usuarios registrados.")
        return

    st.caption(f"{len(users)} usuarios encontrados")

    header_cols = st.columns([2, 2, 2, 2, 2])
    header_cols[0].markdown("**Usuario**")
    header_cols[1].markdown("**Rol**")
    header_cols[2].markdown("**Estado**")
    header_cols[3].markdown("**Cambiar rol**")
    header_cols[4].markdown("**Activar / Desactivar**")

    for idx, user in enumerate(users):
        _render_user_row(user, idx)
