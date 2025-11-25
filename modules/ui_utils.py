import streamlit as st


def render_search_results(search_results, darkweb_results=None):
    """
    Muestra los resultados de búsqueda de forma segura en Streamlit.

    Args:
        search_results (dict): Resultados principales por tipo (people, emails, etc.)
        darkweb_results (dict, optional): Resultados opcionales del dark web.
    """

    if not search_results:
        st.info("No hay resultados para mostrar.")
        return

    for source_type, source_data in search_results.items():
        if "results" not in source_data:
            continue

        results = source_data["results"]
        if not results:
            continue

        st.subheader(f"🔍 Resultados de {source_type.capitalize()}")

        for item in results:
            # Si es diccionario, mostramos campos conocidos
            if isinstance(item, dict):
                name = item.get("name") or item.get("full_name") or "N/A"
                email = item.get("email", "N/A")
                other_info = ", ".join(f"{k}: {v}" for k, v in item.items() if k not in ["name", "email"])

                st.markdown(f"**Nombre:** {name}")
                st.markdown(f"**Email:** {email}")
                if other_info:
                    st.markdown(f"**Otros datos:** {other_info}")

            # Si es string, mostramos directamente
            elif isinstance(item, str):
                st.markdown(f"**Resultado:** {item}")

            # Si es lista anidada, la mostramos recursivamente
            elif isinstance(item, list):
                st.markdown("**Resultados adicionales:**")
                for subitem in item:
                    st.markdown(f"- {subitem}")

            # Otros tipos no esperados
            else:
                st.markdown(f"**Dato inesperado:** {str(item)}")

            st.markdown("---")

    # Mostrar resultados del darkweb si los hay
    if darkweb_results:
        st.subheader("🕵️‍♂️ Resultados Dark Web")
        for entry in darkweb_results.get("results", []):
            st.markdown(f"- {entry}")
        st.markdown("---")
