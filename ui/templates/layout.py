# ui/templates/layout.py

import streamlit as st
from ui.templates.sidebar import render_sidebar


def render_layout():
    """
    Diseño completo de la aplicación con tema profesional
    """

    # Configuración de estilo base
    st.set_page_config(
        page_title="Quasar III OSINT Suite",
        page_icon="🕵️‍♂️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS personalizado
    st.markdown("""
        <style>
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        .stButton>button {
            border-radius: 8px !important;
            padding: 10px 15px !important;
            font-weight: 500 !important;
        }
        .stMetric {
            border-radius: 8px;
            padding: 15px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stAlert {
            border-radius: 8px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Renderizar sidebar
    render_sidebar()

    # Contenido principal
    return st.container()