import streamlit as st
import PyPDF2
import pandas as pd


class DocumentIntOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    def extract_pdf_metadata(self, file_bytes):
        """Extrae metadata de PDF"""
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        return {"pages": len(reader.pages), "metadata": reader.metadata}

    def render_ui(self):
        st.header("📄 Document Intelligence")

        uploaded_file = st.file_uploader("Subir PDF/DOCX", type=['pdf', 'docx'])

        if uploaded_file and st.button("Analizar"):
            metadata = self.extract_pdf_metadata(uploaded_file.read())
            st.json(metadata)