# modules/reporting/pdf_generator.py

import logging
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import os
import base64

logger = logging.getLogger(__name__)

# Definir estilo personalizado
styles = getSampleStyleSheet()
custom_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], spaceAfter=6, fontSize=10)


def generate_pdft_report(
        filename: str,
        title: str,
        author: str,
        content_data: List[Dict[str, Any]],
        cover_text: str = "",
        output_dir: str = "reports"
) -> str:
    """
    Genera un archivo PDF con una plantilla básica de reporte.
    :param filename: Nombre del archivo (sin extensión).
    :param title: Título del PDF.
    :param author: Autor del reporte.
    :param content_data: Lista de bloques de contenido con tipos y datos.
    :param cover_text: Texto extra que puede ir antes del contenido real.
    :param output_dir: Carpeta donde se guardará.
    :return: Ruta al archivo PDF generado.
    """
    logger.info(f"Generando reporte PDF: {filename}")

    # Asegurar que exista el directorio de salida
    os.makedirs(output_dir, exist_ok=True)

    full_path = os.path.join(output_dir, filename + ".pdf")

    # Crear el documento
    pdf_doc = SimpleDocTemplate(full_path, pagesize=letter)
    story = []

    # Título
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    # Fecha y autor
    today = datetime.now().strftime("%d/%m/%Y %H:%M")
    header_info = f"Autor: {author} | Generado el: {today}"
    story.append(Paragraph(header_info, custom_style))
    story.append(Spacer(1, 12))

    # Texto de portada/aviso si aplica
    if cover_text:
        story.append(Paragraph(cover_text, styles['Heading2']))
        story.append(Spacer(1, 12))

    # Procesar datos por tipo
    for block in content_data:
        block_type = block.get("type", "unknown")
        block_content = block.get("content", "Sin contenido.")

        if block_type.lower() == "heading":
            story.append(Paragraph(block_content, styles['Heading2']))
            story.append(Spacer(1, 12))
        elif block_type.lower() == "paragraph":
            story.append(Paragraph(block_content, styles['Normal']))
            story.append(Spacer(1, 6))
        elif block_type.lower() == "table":
            # Espera un objeto tipo [[headings], [rows]] o similar
            table_data = block_content
            try:
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 12))
            except Exception as e:
                logging.error(f"Error al procesar tabla en reporte: {e}")
                story.append(Paragraph(str(table_data), custom_style))
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(str(block_content), styles['Normal']))
            story.append(Spacer(1, 6))

    try:
        pdf_doc.build(story)
        logger.info(f"Reporte {filename} generado con éxito en {full_path}")
        return full_path
    except Exception as e:
        logger.error(f"Error al generar reporte PDF: {e}")
        raise


# Ejemplo de uso (función auxiliar que se puede invocar desde otras vistas):
def example_generate_report():
    """
    Ejemplo de creación de información de reporte.
    """

    def create_sample_report_structure():
        data_blocks = [
            {"type": "heading", "content": "Resumen del Análisis OSINT"},
            {"type": "paragraph",
             "content": f"Este reporte fue generado automáticamente el {datetime.now():%d-%m-%Y}."},
            {"type": "heading", "content": "Datos Encontrados"},
            {"type": "table", "content": [
                ["Nombre", "Email", "Ubicación"],
                ["Juan Pérez", "juan.perez@example.com", "Cd. de México"],
                ["María García", "maria.garcia@test.org", "Guadalajara"]
            ]},
            {"type": "paragraph", "content": """Este informe contiene una selección de datos recopilados durante un escaneo básico de personas. 
            Puede extenderse con detalles adicionales como relaciones, transacciones financieras o contextos geográficos."""}
        ]

        return data_blocks

    # Llamada a función real
    blocks = create_sample_report_structure()
    generated_report_path = generate_pdft_report(
        filename="ejemplo_reporte",
        title="Reporte de Análisis OSINT",
        author="OSINT Toolkit",
        content_data=blocks,
        cover_text="Nota: Datos provienen de fuentes públicas.",
        output_dir="reports"
    )
    return generated_report_path