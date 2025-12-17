import streamlit as st


def _normalize_tool_value(v):
    # Si el valor es None, retornamos un error de tipo "empty"
    if v is None:
        return {"error": "empty"}

    # Si el valor es un diccionario, lo retornamos tal cual
    if isinstance(v, dict):
        return v

    # Si el valor es una lista, lo envolvemos en un diccionario con la clave "data"
    if isinstance(v, list):
        return {"data": v}

    # Si el valor es otro tipo de dato (como un string o int), lo convertimos en un error
    return {"error": str(v)}


def render_socmint_block(social_results: dict):

    # Verificamos si los resultados son un diccionario
    if not isinstance(social_results, dict):
        st.info("No hay datos SOCMINT válidos.")
        return

    st.markdown("### 🌐 Perfiles Sociales")

    # Iteramos sobre cada herramienta en los resultados
    for tool, raw in social_results.items():
        # Normalizamos el valor para evitar errores de tipo 'str' object has no attribute 'get'
        normalized_data = _normalize_tool_value(raw)

        # 🔐 Blindaje total: Si la normalización genera un error, mostramos el mensaje correspondiente
        if not isinstance(normalized_data, dict):
            st.warning(f"{tool.capitalize()}: salida inválida")
            st.code(str(normalized_data)[:1000])
            continue

        st.markdown(f"#### {tool.capitalize()}")

        # Si hay un error en los datos normalizados, lo mostramos
        if normalized_data.get("error"):
            st.warning(normalized_data["error"])
            continue

        # Si existen datos en el campo 'data', los mostramos como JSON
        if normalized_data.get("data"):
            st.json(normalized_data["data"])
        else:
            # Si no hay resultados, informamos que no se encontraron datos
            st.info("Sin resultados.")
