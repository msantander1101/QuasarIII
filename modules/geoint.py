import streamlit as st
import folium
from streamlit_folium import st_folium


class GEOIntOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    def render_ui(self):
        st.header("🗺️ Geo Intelligence")

        lat = st.number_input("Latitud", value=40.4168)
        lon = st.number_input("Longitud", value=-3.7038)

        if st.button("Generar Mapa", type="primary"):
            m = folium.Map(location=[lat, lon], zoom_start=15)
            folium.Marker([lat, lon], popup="Target Location").add_to(m)
            st_folium(m, width=700, height=500)