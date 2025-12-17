import streamlit as st
import json




def render_person_card(person: dict, idx: int = 0):
    """Renderiza una tarjeta simplificada y segura para un dict persona."""
    if not isinstance(person, dict):
        st.write(person)
        return


    name = person.get("name") or person.get("fullname") or "Nombre desconocido"
    email = person.get("email", "N/A")
    phone = person.get("phone", "N/A")
    location = person.get("location", person.get("city", "N/A"))
    confidence = person.get("confidence", 0.0)


    html = f"""
    <div style='background:#1e1e2e;padding:12px;border-radius:10px;margin-bottom:12px;border-left:4px solid #4a90e2;'>
    <div style='display:flex;justify-content:space-between'>
    <div>
    <h3 style='margin:0;color:#fff'>{name}</h3>
    <p style='margin:4px 0 0 0;color:#b0b0c0;'>📧 {email} — 📍 {location} — 📱 {phone}</p>
    </div>
    <div style='text-align:right;'><span style='background:#4a90e2;color:white;padding:6px 12px;border-radius:12px;'>⭐ {confidence:.2f}</span></div>
    </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


    # Mostrar perfiles sociales si existen
    if person.get("social_profiles"):
        st.markdown("#### 🌐 Perfiles Sociales Integrados")
        st.json(person.get("social_profiles"))


    # boton guardar (placeholder)
    btn_key = f"save_person_{idx}"
    if st.button("✅ Guardar persona", key=btn_key):
        st.success("Persona guardada (simulado)")
