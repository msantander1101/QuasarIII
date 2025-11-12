import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components


class OSINTGraphBuilder:
    def __init__(self, user_id, db_manager):
        self.user_id = user_id
        self.db = db_manager
        self.G = nx.MultiDiGraph()

    def build_from_session(self):
        """Construye grafo desde session_state"""
        target = st.session_state.get('current_target', {})
        if not target:
            return

        # Nodo central
        target_id = f"person_{target.get('username', 'unknown')}"
        self.G.add_node(target_id, label=target.get('username'), color="#ff6b6b", size=30)

        # Emails
        if target.get('email'):
            email_id = f"email_{target['email']}"
            self.G.add_node(email_id, label=target['email'], color="#4dabf7")
            self.G.add_edge(target_id, email_id, label="usa_email")

        # Perfiles sociales
        if 'results_socmint' in st.session_state:
            for profile in st.session_state.results_socmint.get('profiles', []):
                profile_id = f"profile_{profile['platform']}"
                self.G.add_node(profile_id, label=profile['platform'], color="#51cf66")
                self.G.add_edge(target_id, profile_id, label="perfil_en")

    def render_ui(self):
        st.subheader("🔗 Grafo de Relaciones")

        if st.button("Generar Grafo"):
            self.build_from_session()

            if len(self.G.nodes) > 1:
                net = Network(height="500px", width="100%", bgcolor="#1a1a1a", font_color="white")
                net.from_nx(self.G)

                html = net.generate_html()
                components.html(html, height=500)
            else:
                st.info("No hay datos para graficar")