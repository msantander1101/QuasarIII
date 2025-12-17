import streamlit as st




def render_email_block(email_block: dict):
    if not email_block:
        return
    st.markdown("### 📧 Emails")
    results = email_block.get("results") if isinstance(email_block, dict) else None
    if not results:
        st.info("No hay resultados de email")
        return
    for e in results:
        st.markdown(f"- {e.get('email', 'N/A')} — breaches: {e.get('breach_count', 0)}")




def render_web_block(web_block: dict):
    if not web_block:
        return
    st.markdown("### 🌍 Resultados Web")
    results = web_block.get("results") if isinstance(web_block, dict) else []
    for item in results:
        title = item.get('title') or item.get('name') or 'Sin título'
        url = item.get('url') or item.get('link') or '#'
        snippet = item.get('snippet', '')
        st.markdown(f"- [{title}]({url}) — {snippet}")
