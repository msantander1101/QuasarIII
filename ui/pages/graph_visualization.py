# ui/pages/graph_visualization.py

import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from core.db_manager import get_graph_for_user, get_relationships_for_person
import matplotlib
matplotlib.use('Agg') # Requerido para usar matplotlib con Streamlit
import io
import base64


def show_graph_visualization():
    """
    Visualiza el grafo de conocimiento del usuario actual (personas + relaciones).
    """

    st.subheader("🧠 Panel de Visualización de Grafo")

    user_id = st.session_state.get('current_user_id', None)
    if not user_id:
        st.error("No puedes ver el grafo sin estar logueado.")
        return

    # Obtener datos del grafo local
    graph_data = get_graph_for_user(user_id)
    persons = graph_data.get("persons", [])
    rels = graph_data.get("relationships", [])

    if not persons and not rels:
        st.info("No hay datos para visualizar. Crea personas y relaciones primero.")
        return

    # Mostrar información resumida del grafo
    st.markdown("### Datos del Grafo")
    st.write(f"**Personas:** {len(persons)}")
    st.write(f"**Relaciones:** {len(rels)}")

    # Mostrar personas
    st.markdown("### Personas del Grafo")
    if persons:
        for i, person in enumerate(persons):
            # Usamos el índice como clave única para los elementos de expansión
            key_prefix = f"person_{i}"
            st.markdown(f"**{person['name']}** (ID: {person['id']})")
            st.markdown(f"Email: {person.get('email', 'N/A')}")
            st.markdown(f"Teléfono: {person.get('phone', 'N/A')}")
            st.markdown(f"Ubicación: {person.get('location', 'N/A')}")
            st.markdown(f"Descripción: {person.get('description', 'N/A')}")
            # Botón opcional para gestionar esta persona: Añadir relaciones
            if st.button(f"Añadir Relación", key=f"add_rel_to_{person['id']}"):
                st.session_state['rels_target_person'] = person
                st.session_state['rels_target_person_id'] = person['id']
                # Cambiar a la vista de búsqueda o creación de relaciones
                st.session_state['action_view_rels'] = True
                st.rerun()
            st.markdown("---")
    else:
        st.markdown("No hay personas guardadas.")

    # Mostrar relaciones completas en forma de tabla
    st.markdown("### Relaciones del Grafo")
    rel_table_data = []
    if rels:
        for j, rel in enumerate(rels):
            person1_id = rel.get("source", "Desconocido")
            person2_id = rel.get("target", "Desconocido")
            rel_type = rel.get("type", "Desconocido")
            details = rel.get("details", "Sin detalles")

            # Obteniendo nombres de las personas para mostrarlos
            person1_name = "Desconocido"
            person2_name = "Desconocido"

            for person in persons:
                if person['id'] == person1_id:
                    person1_name = person['name']
                if person['id'] == person2_id:
                    person2_name = person['name']

            rel_table_data.append({
                'Persona 1': person1_name,
                'Relación': rel_type,
                'Persona 2': person2_name,
                'Detalles': details
            })

        # Mostrar en tabla de forma más clara
        # Usar DataFrame no es imprescindible, puedes hacer una lista o mostrar uno por uno.
        # Pero es útil para mostrar múltiples relaciones.
        st.table(rel_table_data) # Aquí puedes mejorar visualización con HTML personalizado o grid
    else:
        st.markdown("No hay relaciones guardadas aún.")

    # --- GRÁFICO VISUAL ---
    st.markdown("### Visualización Gráfica del Grafo")
    st.info("A continuación se muestra el grafo. Para obtener una vista más detallada y explorar dinámicamente, usa el botón de abajo.")

    # Agregar botón para generar la imagen (después de verificación de datos)
    if st.button("Generar Gráfico Completo"):
        if persons and rels:
            # Crear el grafo usando networkx
            G = nx.Graph()

            # Agregar nodos (personas)
            person_lookup = {} # Para mapear ID a nombre
            for p in persons:
                person_id = p['id']
                person_name = p['name']
                G.add_node(person_id, label=person_name)
                person_lookup[person_id] = person_name

            # Agregar aristas (relaciones)
            # Aseguramos que las relaciones apunten a IDs válidos
            valid_rels_count = 0
            for r in rels:
                try:
                    source_id = int(r.get("source"))
                    target_id = int(r.get("target"))
                    relationship_type = r.get("type", "Desconocida")

                    # Verificar que las personas existen antes de añadir la relación
                    if source_id in person_lookup and target_id in person_lookup:
                        G.add_edge(source_id, target_id, relationship_type=relationship_type)
                        valid_rels_count += 1
                    else:
                        # Puedes registrar esto o ignorar
                        st.info(f"Relación ignorada: ID de persona ausente (s:{source_id}, t:{target_id}) de tipo {relationship_type}")
                except (ValueError, TypeError) as e:
                    st.warning(f"Error al procesar relación: {e}")

            # Mostrar conteo de relaciones válidas procesadas
            st.info(f"Relaciones válidas procesadas: {valid_rels_count}/{len(rels)}")

            if len(G.nodes()) > 0:
                # Configurar posición de nodos
                pos = nx.spring_layout(G, k=1, iterations=50)  # k=distancia entre nodos

                # Crear figura
                fig, ax = plt.subplots(figsize=(12, 10))
                ax.set_title("Grafo de Relaciones", fontsize=16)

                # Dibujar nodos
                node_labels = nx.get_node_attributes(G, 'label')
                nx.draw_networkx_nodes(G, pos, node_size=500, ax=ax, node_color="#ADD8E6")
                nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8, ax=ax)

                # Dibujar aristas con etiquetas de tipo de relación
                # Obtenemos etiquetas desde los atributos de las aristas
                edges = G.edges()
                edge_labels = nx.get_edge_attributes(G, 'relationship_type')
                if edge_labels:
                    # Solo muestra etiquetas si hay aristas con información de relación
                    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=6, ax=ax)

                # Dibuja las aristas sin etiquetas si no hay contenido para ellas
                nx.draw_networkx_edges(G, pos, width=1, alpha=0.7, edge_color='gray', ax=ax)

                # Usar buffer para guardar imagen
                buf = io.BytesIO()
                plt.savefig(buf, format="png", dpi=300, bbox_inches='tight')
                buf.seek(0)
                # Codificar en base64 para mostrar en streamlit
                img_str = base64.b64encode(buf.read()).decode()

                # Mostrar imagen en Streamlit
                st.image(f"data:image/png;base64,{img_str}", caption="Modelo de Grafo", use_column_width=True)
                plt.close(fig) # Cerrar matplotlib
                buf.close() # Cerrar buffered image
                st.success("Gráfico generado y mostrado.")
            else:
                st.warning("No se pudo generar el gráfico: sin nodos válidos.")
        else:
            st.warning("No hay datos suficientes para generar el gráfico.")

    # Botón para volver al dashboard
    if st.button("Volver al Dashboard"):
        st.session_state.pop('rels_target_person', None)
        st.session_state.pop('rels_target_person_id', None)
        st.session_state.pop('action_view_rels', None)
        st.session_state['page'] = 'dashboard'
        st.rerun()