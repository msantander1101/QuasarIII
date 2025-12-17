import streamlit as st




def render_darkweb_block(dw_results: dict):
    st.markdown("### 🔍 Dark Web")
    if not dw_results:
        st.info("No hay resultados Darkweb")
        return
    raw = dw_results.get('raw_results') if isinstance(dw_results, dict) else None
    if raw and isinstance(raw, dict):
        for engine, hits in raw.items():
            if not hits:
                continue
            with st.expander(f"{engine} ({len(hits)})"):
                for h in hits[:10]:
                    st.write(h)
    else:
        st.write(dw_results)
