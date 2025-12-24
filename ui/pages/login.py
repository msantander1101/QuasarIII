# ui/pages/login.py

import logging
import streamlit as st
from core.auth_manager import authenticate_user, register_user

logger = logging.getLogger(__name__)


def _inject_login_styles():
    st.markdown(
        """
<style>
/* ---------- Global background for login ---------- */
.stApp {
  background: radial-gradient(1200px 600px at 15% 10%, rgba(58,123,213,0.55), transparent 60%),
              radial-gradient(900px 500px at 85% 15%, rgba(0,78,146,0.55), transparent 55%),
              linear-gradient(135deg, #0b1220 0%, #07101d 40%, #050b14 100%) !important;
}

/* Hide sidebar spacing if any */
section[data-testid="stSidebar"] { display: none; }
div[data-testid="stSidebarNav"] { display: none; }

/* Reduce Streamlit main padding a bit (helps on tall gaps) */
section.main > div.block-container {
  padding-top: 2.2rem;
  padding-bottom: 2.2rem;
}

/* ---------- Card styles ---------- */
.q3-card {
  width: 100%;
  border-radius: 20px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 18px 55px rgba(0,0,0,0.45);
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.q3-topbar {
  padding: 18px 22px 14px 22px;
  border-bottom: 1px solid rgba(255,255,255,0.10);
  background: linear-gradient(135deg, rgba(58,123,213,0.22), rgba(0,78,146,0.10));
}

.q3-brand {
  display:flex;
  align-items:center;
  gap: 10px;
  margin-bottom: 8px;
}

.q3-logo {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(135deg, #3a7bd5 0%, #004e92 100%);
  box-shadow: 0 10px 22px rgba(0,0,0,0.35);
  display:flex;
  align-items:center;
  justify-content:center;
  color: white;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.q3-title {
  font-size: 26px;
  font-weight: 900;
  color: rgba(255,255,255,0.95);
  line-height: 1.1;
  margin: 0;
}

.q3-subtitle {
  margin: 0;
  margin-top: 3px;
  color: rgba(255,255,255,0.70);
  font-size: 13.5px;
}

.q3-badges { margin-top: 10px; display:flex; flex-wrap:wrap; gap:8px; }
.q3-badge {
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.10);
  color: rgba(255,255,255,0.82);
  font-size: 12px;
  font-weight: 700;
}

.q3-body {
  padding: 12px 22px 16px 22px;
}

.q3-foot {
  padding: 12px 22px 16px 22px;
  border-top: 1px solid rgba(255,255,255,0.10);
  color: rgba(255,255,255,0.55);
  font-size: 12px;
  display:flex;
  justify-content:space-between;
  flex-wrap:wrap;
  gap:10px;
}

/* ---------- Streamlit components tweaks ---------- */
div[data-testid="stTabs"] button {
  color: rgba(255,255,255,0.75) !important;
  font-weight: 800 !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: rgba(255,255,255,0.95) !important;
}

/* Compact tabs/panels spacing */
div[data-baseweb="tab-list"] {
  margin-top: 4px !important;
  margin-bottom: 6px !important;
}
div[data-baseweb="tab-panel"] {
  padding-top: 4px !important;
}

/* Inputs */
div[data-testid="stTextInput"] label { display:none !important; }
div[data-testid="stTextInput"] input {
  border-radius: 14px !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  background: rgba(255,255,255,0.06) !important;
  color: rgba(255,255,255,0.92) !important;
  padding: 12px 14px !important;
}
div[data-testid="stTextInput"] input::placeholder {
  color: rgba(255,255,255,0.45) !important;
}

/* Buttons */
div[data-testid="stButton"] button {
  border-radius: 14px !important;
  font-weight: 900 !important;
  padding: 12px 14px !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  background: linear-gradient(135deg, rgba(58,123,213,0.95), rgba(0,78,146,0.95)) !important;
}
div[data-testid="stButton"] button:hover {
  filter: brightness(1.05);
}

.q3-help {
  color: rgba(255,255,255,0.65);
  font-size: 12.5px;
  margin: 4px 0 10px 0;
}

/* Make the whole middle column feel like one card */
.q3-divider {
  height: 1px;
  background: rgba(255,255,255,0.10);
  margin: 10px 0 10px 0;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def show_login_with_tabs():
    _inject_login_styles()

    # ✅ Centro real con columnas (no dependemos de wrappers HTML abiertos)
    left, mid, right = st.columns([1, 2, 1], vertical_alignment="top")

    with mid:
        # Card start (header)
        st.markdown(
            """
<div class="q3-card">
  <div class="q3-topbar">
    <div class="q3-brand">
      <div class="q3-logo">Q3</div>
      <div>
        <h1 class="q3-title">Quasar III</h1>
        <p class="q3-subtitle">OSINT Suite • Investigación • Correlación</p>
      </div>
    </div>
    <div class="q3-badges">
      <span class="q3-badge">🔐 Acceso seguro</span>
      <span class="q3-badge">🧠 Intel-ready</span>
      <span class="q3-badge">⚡ Ejecución bajo demanda</span>
    </div>
  </div>
  <div class="q3-body">
    <div class="q3-divider"></div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["🔐 Iniciar sesión", "🆕 Registro"])

        with tab1:
            st.markdown(
                '<div class="q3-help">Introduce tus credenciales para acceder al panel.</div>',
                unsafe_allow_html=True
            )

            username = st.text_input(
                "Nombre de Usuario",
                key="login_username",
                placeholder="Usuario",
                label_visibility="collapsed",
            )

            password = st.text_input(
                "Contraseña",
                type="password",
                key="login_password",
                placeholder="Contraseña",
                label_visibility="collapsed",
            )

            if st.button("Entrar", use_container_width=True, key="login_submit"):
                if username and password:
                    user_id = authenticate_user(username, password)
                    if user_id:
                        st.session_state["authenticated"] = True
                        st.session_state["current_user_id"] = user_id
                        st.session_state["current_user"] = {"username": username}
                        logger.info("Login OK | user=%s id=%s", username, user_id)
                        st.success("✅ Acceso autorizado.")
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos.")
                        logger.warning("Login FAIL | user=%s", username)
                else:
                    st.warning("⚠️ Completa usuario y contraseña.")

        with tab2:
            st.markdown(
                '<div class="q3-help">Crea tu cuenta para empezar a operar.</div>',
                unsafe_allow_html=True
            )

            new_username = st.text_input(
                "Nombre de Usuario",
                key="register_username",
                placeholder="Nombre de usuario",
                label_visibility="collapsed",
            )

            new_email = st.text_input(
                "Correo Electrónico",
                key="register_email",
                placeholder="tu@email.com",
                label_visibility="collapsed",
            )

            new_password = st.text_input(
                "Contraseña",
                type="password",
                key="register_password",
                placeholder="Contraseña segura",
                label_visibility="collapsed",
            )

            confirm_password = st.text_input(
                "Confirmar Contraseña",
                type="password",
                key="confirm_password",
                placeholder="Repite la contraseña",
                label_visibility="collapsed",
            )

            if st.button("Crear cuenta", use_container_width=True, key="register_submit"):
                if new_username and new_email and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("❌ Las contraseñas no coinciden.")
                        return

                    success = register_user(new_username, new_email, new_password)
                    if success:
                        st.success("✅ Registro completado. Ya puedes iniciar sesión.")
                        logger.info("Register OK | user=%s", new_username)
                        st.rerun()
                    else:
                        st.error("❌ Usuario o email ya existentes.")
                        logger.warning("Register FAIL | user=%s", new_username)
                else:
                    st.warning("⚠️ Completa todos los campos.")

        # Card end (footer + close divs)
        st.markdown(
            """
  </div>
  <div class="q3-foot">
    <span>Quasar III • OSINT Suite</span>
    <span>v3 • Secure UI</span>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )
