import json
import streamlit as st

class SearchTemplate:
    """
    Guarda/recupera configuraciones de búsqueda
    """

    def __init__(self, user_id, db_manager):
        self.user_id = user_id
        self.db = db_manager

    def save_template(self, name, config):
        """Guarda plantilla de búsqueda"""
        self.db.save_api_key(self.user_id, f"TEMPLATE_{name}", encrypt_data(json.dumps(config)))

    def load_template(self, name):
        """Carga plantilla"""
        encrypted = self.db.get_api_key(self.user_id, f"TEMPLATE_{name}")
        return json.loads(decrypt_data(encrypted)) if encrypted else None


# UI en configuración:
template_name = st.text_input("Nombre plantilla")
if st.button("Guardar configuración actual"):
    template.save_template(template_name, {
        "modules": ["socmint", "breachdata"],
        "depth": 3,
        "use_proxies": True
    })