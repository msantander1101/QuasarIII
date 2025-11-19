# modules/ai/intelligence_core.py
"""
Módulo central para integración de inteligencia artificial.
Soporta resúmenes, análisis, detectores de información sensible, etc.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# Puedes instalar estos paquetes si los usas:
# pip install openai langchain

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logging.warning("OpenAI library not installed. AI features will not function without it.")

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate
    from langchain.chains import LLMChain

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    logging.warning("LangChain library not installed. Advanced AI features will not function.")

logger = logging.getLogger(__name__)


class AIPoweredAnalyzer:
    """
    Clase que proporciona métodos de análisis con IA integrada.
    Utiliza OpenAI para análisis automatizados.
    """

    def __init__(self, api_key: str = None):
        """
        Constructor que acepta una clave API de OpenAI.
        :param api_key: Clave API de OpenAI. Dejar None si no se desea usar.
        """
        self.api_key = api_key

        # Verificar y preparar cliente de OpenAI
        if HAS_OPENAI and self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            self.is_active = True
        else:
            self.client = None
            self.is_active = False
            if not HAS_OPENAI:
                logger.warning("OpenAI library no está disponible. Algunas características de IA no funcionarán.")
            if self.api_key is None and HAS_OPENAI:
                logger.warning("Clave API de OpenAI no configurada. IA deshabilitada.")

        # Si se tiene LangChain, se podrá usar para cadenas de prompts más complejas
        self.langchain_model = None
        if HAS_LANGCHAIN and self.is_active:
            try:
                # Crea modelo LangChain usando la API
                self.langchain_model = ChatOpenAI(model="gpt-4", temperature=0.3, openai_api_key=self.api_key)
                logger.info("Modelo LangChain cargado correctamente.")
            except Exception as e:
                logger.warning(f"Fallo al cargar modelo LangChain: {e}")
                self.langchain_model = None

    def summarize_text(self, text: str, max_length_words: int = 200) -> str:
        """
        Resume un texto largo usando IA.
        :param text: Texto a resumir.
        :param max_length_words: Longitud máxima del resumen (por palabras).
        :return: Resumen del texto.
        """
        if not self.is_active:
            return "La IA no está configurada. El resumen requiere una clave API de OpenAI.\nTexto original:\n" + text[
                :500] + "..."
        try:
            prompt = f"""Resume el siguiente contenido en máximo {max_length_words} palabras:

            {text}

            RESUMEN:"""

            stream = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_length_words * 4,  # Aproximadamente 4 tokens por palabra
                temperature=0.5,  # Menos creativo para resúmenes objetivos
                stream=False  # Cambiar si deseas streaming
            )

            summary = stream.choices[0].message.content.strip()
            return summary

        except Exception as e:
            logger.error(f"Error al generar resumen: {e}")
            return f"Error en análisis IA: {str(e)}"

    def classify_information(self, data: Union[Dict, str], categories: List[str]) -> Dict[str, Any]:
        """
        Clasifica información según categorías predefinidas o tipos.
        :param data: Datos a clasificar.
        :param categories: Lista de categorías posibles (ej: ["contacto", "ubicación", "comerciales"])
        :return: Diccionario de probabilidades/etiqueta por categoría.
        """
        if not self.is_active:
            return {"error": "IA desactivada"}

        try:
            # Asegurarnos de que los datos sean legibles
            input_text = ""
            if isinstance(data, dict):
                input_text = json.dumps(data, indent=2)
            elif isinstance(data, str):
                input_text = data
            else:
                return {"error": "Tipo de datos no soportado para clasificación"}

            categories_str = ", ".join(categories)
            prompt = f"""
            Clasifica la siguiente información según las categorías definidas: {categories_str}.
            Devuelve una respuesta JSON con cada categoría y una probabilidad entre 0 y 1 (ej: {{'contacto': 0.9, 'ubicación': 0.3}}).

            Información:
            {input_text}

            Respuesta JSON:
            """

            # Llamada a API con respuesta estructurada
            stream = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100,  # Ajustar según la complejidad esperada
                response_format={"type": "json_object"}  # Forzar formato JSON
            )
            resp_text = stream.choices[0].message.content.strip()
            try:
                classification = json.loads(resp_text)
                return classification
            except json.JSONDecodeError as e:
                logger.warning(f"Fallo al parsear JSON de clasificación: {e}")
                return {"error": f"Falló al interpretar respuesta IA: {resp_text}"}

        except Exception as e:
            logger.error(f"Error al clasificar información: {e}")
            return {"error": f"Error IA de clasificación: {str(e)}"}

    def detect_sensitive_data(self, info_text: str) -> List[Dict]:
        """
        Detecta elementos sensibles (números de seguridad, direcciones, etc.) en texto.
        :param info_text: Texto para analizar.
        :return: Lista de objetos con información detectada.
        """
        if not self.is_active:
            return [{"detection": "IA desactivada. No se pueden detectar datos sensibles.", "confidence": 0.1}]
        try:
            prompt = f"""
            Analiza el siguiente texto y detecta posibles datos sensibles (nombres de personas, números de teléfono, direcciones de correo, rutas de archivos, etc.). Enuméralos como una lista de JSON de objetos con claves 'type' y 'detail'.

            Información:
            {info_text}

            Formato de salida:
            [
                {{
                    "type": "<tipo>",
                    "detail": "<información específica>"
                }}
            ]
            """

            stream = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            response_text = stream.choices[0].message.content.strip()
            try:
                detections = json.loads(response_text)
                return detections if isinstance(detections, list) else [{"error": "Formato incorrecto"}]
            except Exception as e:
                return [{"error": f"Error al parsear resultados de detección: {str(e)}"}]

        except Exception as e:
            logger.error(f"Error al detectar datos sensibles: {e}")
            return [{"error": str(e)}]

    # Puede haber otros métodos como análisis de sentimiento, traducción, etc.


# Instancia global (si se desea usar por todo el sistema sin reinicialización)
# Puede cargarse desde el main.py o desde un archivo de configuración
ai_analyzer = None  # Dejar como None, y definirlo más tarde con clave cuando la tengamos


def initialize_ai_analyzer(api_key: Optional[str] = None):
    """
    Función auxiliar para crear instancia del analizador de IA.
    Esta se llama normalmente al arrancar la aplicación o cuando se obtiene la clave.
    Usar después de obtener una API key válida del usuario.
    Ejemplo: initialize_ai_analyzer(config_manager.get_config(user_id, "openai_api_key"))
    """
    global ai_analyzer
    if api_key:
        ai_analyzer = AIPoweredAnalyzer(api_key)
        logger.info("Analizador de IA inicializado")
    else:
        ai_analyzer = AIPoweredAnalyzer()  # Inicializa sin clave
        logger.info("Analizador de IA inicializado sin clave API (opcional).")


# Exporta función para inicialización
__all__ = ['AIPoweredAnalyzer', 'initialize_ai_analyzer', 'ai_analyzer']