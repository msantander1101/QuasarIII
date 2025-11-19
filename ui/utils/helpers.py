import streamlit as st

def set_current_user_id(user_id: int):
    """Establece el ID del usuario actual en el estado de Streamlit."""
    # Asegúrate de tener esta clave en tu session_state
    st.session_state['current_user_id'] = user_id


def get_current_user_id() -> int:
    """Obtiene el ID del usuario actual del estado de Streamlit."""
    return st.session_state.get('current_user_id')


def clear_session():
    """Limpia la sesión actual."""
    st.session_state.clear()


def get_current_user():
    """Devuelve datos del usuario actual en sesión (ej: username)."""
    return st.session_state.get('current_user', None)


def get_user_session_state():
    """Devuelve todo el estado de sesión del usuario."""
    return st.session_state


def set_session_state(key: str, value):
    """Establece un valor en el estado de sesión."""
    st.session_state[key] = value


def get_session_state(key: str, default=None):
    """Obtiene un valor del estado de sesión."""
    return st.session_state.get(key, default)


def update_user_info(username: str, email: str = None):
    """Actualiza la información del usuario en la sesión."""
    if 'current_user' not in st.session_state:
        st.session_state['current_user'] = {}

    st.session_state['current_user']['username'] = username
    if email:
        st.session_state['current_user']['email'] = email


def is_authenticated() -> bool:
    """Verifica si el usuario está autenticado."""
    return st.session_state.get('authenticated', False)