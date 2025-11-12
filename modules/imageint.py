from typing import Dict
import exifread
import streamlit as st


class ImageIntOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    def extract_metadata(self, image_bytes) -> Dict:
        """Extrae EXIF metadata"""
        tags = exifread.process_file(image_bytes)
        metadata = {}
        for tag, value in tags.items():
            if tag not in ('JPEGThumbnail', 'TIFFThumbnail'):
                metadata[tag] = str(value)
        return metadata

    def render_ui(self):
        st.header("🖼️ Image Intelligence")

        uploaded_file = st.file_uploader("Subir imagen", type=['jpg', 'png', 'jpeg'])

        if uploaded_file:
            col1, col2 = st.columns(2)

            with col1:
                st.image(uploaded_file, width=300)

            with col2:
                if st.button("Extraer Metadata", type="primary"):
                    metadata = self.extract_metadata(uploaded_file)
                    st.json(metadata)

                    if 'GPS GPSLatitude' in metadata:
                        st.success("🎯 ¡Coordenadas GPS encontradas!")