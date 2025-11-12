# utils/security_decorators.py
import streamlit as st
from functools import wraps

def require_auth(func):
    """Decorador que requiere autenticación"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in st.session_state:
            st.error("❌ Debes iniciar sesión primero")
            st.session_state.page = "login"
            st.rerun()
        return func(*args, **kwargs)
    return wrapper

# Uso en cualquier función:
@require_auth
def funcion_sensible():
    pass