# modules/search/documentint.py
import logging
from docx import Document  # pip install python-docx
import os

logger = logging.getLogger(__name__)


def search_documents_in_pdf(pdf_path: str, search_terms: list) -> list:
    """
    Busca términos dentro de un documento PDF.
    Requiere: `pip install PyPDF2` (y posiblemente otros).
    """
    logger.info(f"Buscando términos '{search_terms}' en documento PDF: {pdf_path}")

    results = []  # Lista de resultados encontrados
    try:
        if not os.path.exists(pdf_path):
            logger.warning(f"Documento PDF no encontrado: {pdf_path}")
            return results

        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        for page_num, page in enumerate(reader.pages):
            text_content = page.extract_text()
            for term in search_terms:
                positions = [i for i in range(len(text_content)) if text_content.startswith(term, i)]
                if positions:
                    # Devolver página + posición aproximada de texto encontrado
                    results.append({
                        "term": term,
                        "page": page_num + 1,  # páginas indexadas desde 1
                        "positions": positions[:5],  # Máximo 5 apariciones
                        "preview": text_content[max(0, positions[0] - 25):min(len(text_content), positions[0] + 25 + 1)]
                    })
    except Exception as e:
        logger.exception(f"Error procesando PDF: {e}")

    return results


def search_docx_file(docx_path: str, search_term: str) -> list:
    """
    Búsqueda de texto dentro de un archivo .docx (Word).
    Requiere: `pip install python-docx`
    """
    logger.info(f"Buscando '{search_term}' en documento Word: {docx_path}")

    results = []
    try:
        if not os.path.exists(docx_path):
            logger.warning(f"Documento DOCX no encontrado: {docx_path}")
            return results

        doc = Document(docx_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        full_text_str = '\n'.join(full_text)

        # Encontrar posiciones de la palabra clave
        positions = [i for i in range(len(full_text_str)) if full_text_str.startswith(search_term, i)]
        preview_size = 100

        for i, pos in enumerate(positions[:5]):  # Limitar resultados
            start_preview = max(0, pos - preview_size // 2)
            end_preview = min(len(full_text_str), pos + preview_size // 2 + len(search_term))
            preview = full_text_str[start_preview:end_preview].strip()

            results.append({
                "term": search_term,
                "position": pos,
                "preview": preview
            })

    except Exception as e:
        logger.exception(f"Error procesando documento .docx: {e}")

    return results


def search_slideshare_document(document_id: str) -> dict:
    """
    Busca un documento público en Slideshare (simulador).
    """
    logger.info(f"Buscando documento en SlideShare con ID: {document_id}")

    # Simulación de datos de un documento público
    return {
        "document_id": document_id,
        "title": "Presentación Ejemplo sobre OSINT Básico",
        "author": "Ana Rodríguez",
        "description": "Una presentación de ejemplo sobre conceptos básicos de OSINT.",
        "tags": ["OSINT", "Cybersecurity", "Investigación"],
        "download_link": "https://slideshare.net/ejemplo/presentacion",
        "presentation_type": "PowerPoint",
        "slides": 24,
        "view_count": 1500,
        "publish_date": "2024-01-15",
        "categories": ["Tecnología", "Seguridad Informática"]
    }


# Función auxiliar para obtener metadatos de documentos
def get_document_metadata(file_path: str) -> dict:
    """
    Obtiene metadatos de un documento (PDF, DOCX, etc.).
    Requiere instalación correspondiente en función del formato.
    """
    logger.info(f"Extraer metadatos de: {file_path}")

    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower()

    metadata = {
        "filename": filename,
        "full_path": file_path,
        "extension": file_ext,
        "size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        "created_time": "2024-08-10T14:30:00",
        "modified_time": "2024-10-25T09:00:00",
        "author": "Usuario Desconocido",
        "title": "",
        "subject": ""
    }

    try:
        if file_ext == '.pdf':
            from PyPDF2 import PdfReader
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                info = reader.metadata
                if info:
                    metadata.update({
                        key.replace('/', ''): val for key, val in info.items()
                    })
        elif file_ext == '.docx':
            # Para MS Word (.docx)
            doc = Document(file_path)
            core_props = doc.core_properties
            metadata.update({
                'author': core_props.author or metadata['author'],
                'title': core_props.title or metadata['title'],
                'subject': core_props.subject or metadata['subject'],
                'created_time': core_props.created.strftime('%Y-%m-%dT%H:%M:%S') if core_props.created else metadata[
                    'created_time'],
                'modified_time': core_props.modified.strftime('%Y-%m-%dT%H:%M:%S') if core_props.modified else metadata[
                    'modified_time'],
            })
    except Exception as e:
        logger.exception(f"Error al extraer metadatos del documento: {e}")

    return metadata
