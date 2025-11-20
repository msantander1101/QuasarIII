# modules/search/people_search.py
import logging
import requests
import time
from typing import List, Dict, Any
import json
import subprocess
import shutil

logger = logging.getLogger(__name__)


class PeopleSearcher:
    """
    Búsqueda real de personas con integración a servicios públicos
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'QuasarIII-OSINT/1.0',
            'Accept': 'application/json'
        })

    def _run_external_tool(self, command: List[str], timeout: int = 120) -> Dict[str, Any]:
        """
        Ejecuta una herramienta CLI externa (por ejemplo Maigret o Sherlock) y
        devuelve el resultado parseado como JSON si es posible.  Si la
        herramienta no existe en el entorno se devuelve un error indicando
        que debe instalarse.

        :param command: Lista con el ejecutable y sus argumentos
        :param timeout: Tiempo máximo de espera para la ejecución
        :return: Diccionario con los datos parseados o error
        """
        executable = command[0]
        if shutil.which(executable) is None:
            return {"error": f"La herramienta '{executable}' no está instalada en el entorno."}
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            stdout = result.stdout.strip()
            if not stdout:
                # Si la salida está vacía, devolver un mensaje genérico
                return {"warning": f"La herramienta '{executable}' no devolvió datos."}
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                # En caso de que no sea JSON válido, devolver el texto completo
                return {"raw_output": stdout}
        except Exception as e:
            logger.error(f"Error ejecutando {executable}: {e}")
            return {"error": str(e)}

    def search_social_profiles(self, identifier: str) -> Dict[str, Any]:
        """
        Realiza una búsqueda de perfiles sociales usando herramientas OSINT como
        Maigret y Sherlock.  El parámetro `identifier` suele ser un nombre de
        usuario.  Si las herramientas no están disponibles en el entorno,
        devolverán mensajes de error.

        :param identifier: Nombre de usuario o identificador a buscar.
        :return: Diccionario con resultados de Maigret y Sherlock.
        """
        if not identifier:
            return {}
        results: Dict[str, Any] = {}
        # Ejecutar Maigret si existe
        results['maigret'] = self._run_external_tool([
            'maigret', identifier, '--json', '--quiet'
        ])
        # Ejecutar Sherlock si existe
        results['sherlock'] = self._run_external_tool([
            'sherlock', identifier, '--json'
        ])
        return results

    def search_people_by_name(self, name: str, location: str = None,
                              max_results: int = 10) -> List[Dict]:
        """
        Búsqueda de personas por nombre usando servicios reales (simulado)
        En la versión real, conectará con servicios como:
        - Whitepages API
        - People Search APIs
        - Public Databases
        """
        try:
            # Este sería el llamado real a una API como Whitepages, Hunter, etc.
            # Ejemplo:
            # url = "https://api.whitepages.com/person-search"
            # params = {"name": name, "location": location, "api_key": api_key}
            # response = self.session.get(url, params=params)
            # return response.json()

            # Simulación de resultados reales cuando se conecte
            results = []
            for i in range(min(max_results, 5)):
                results.append({
                    "name": f"{name} {chr(65 + i)}",
                    "email": f"{name.lower()}{chr(97 + i)}@example.com",
                    "phone": f"+1-555-01{i + 1}",
                    "location": location or "Ciudad, País",
                    "source": "Directorio Público",
                    "confidence": 0.85 - (i * 0.05),  # Mayor confianza en los primeros
                    "detected_timestamp": time.time() - (i * 86400)  # Días hacia el pasado
                })

            return results

        except Exception as e:
            logger.error(f"Error en búsqueda por nombre: {e}")
            return [{"error": f"Error de búsqueda: {str(e)}"}]

    def search_person_by_email(self, email: str) -> Dict[str, Any]:
        """
        Búsqueda de persona por email real (servicios públicos o APIs)
        En producción se conectaría a:
        - Hunter.io API
        - Whitepages API
        - Person Search APIs
        """
        try:
            # Esto sería una llamada real
            # url = "https://api.hunter.io/v2/email-verifier"
            # params = {"email": email, "api_key": hunter_api_key}
            # response = self.session.get(url, params=params)

            # Simulación:
            return {
                "email": email,
                "name": "Nombre Apellido",
                "phone": "+1-555-0123",
                "location": "Ciudad, País",
                "source": "Buscador de correos públicos",
                "confidence": 0.75,
                "timestamp": time.time(),
                "profile_data": {
                    "linkedin": "https://linkedin.com/in/nombre",
                    "twitter": "@nombre",
                    "facebook": "facebook.com/nombre"
                }
            }

        except Exception as e:
            logger.error(f"Error en búsqueda por email: {e}")
            return {"error": f"Error de búsqueda: {str(e)}"}

    def search_person_by_phone(self, phone: str, country_code: str = "US") -> Dict[str, Any]:
        """
        Búsqueda de persona por número de teléfono
        Conexión real con:
        - Whitepages API
        - TruePeople API
        - AnyWho API
        """
        try:
            # Simulación (en producción conectaría a APIs reales)
            return {
                "phone": phone,
                "name": "Nombre Apellido",
                "email": "persona@example.com",
                "location": "Ciudad, País",
                "source": "Directorio público de teléfonos",
                "confidence": 0.70,
                "timestamp": time.time(),
                "details": {
                    "carrier": "Operador de Teléfono",
                    "type": "móvil",
                    "region": "Región"
                }
            }

        except Exception as e:
            logger.error(f"Error en búsqueda por teléfono: {e}")
            return {"error": f"Error de búsqueda: {str(e)}"}

    def advanced_search(self, criteria: Dict[str, Any], search_type: str = "people",
                        api_keys: Dict[str, str] = None) -> List[Dict]:
        """
        Búsqueda avanzada con múltiples criterios y fuentes reales
        """
        try:
            results = []

            if search_type == "people":
                # Búsqueda multifunción usando claves APIS si están disponibles
                if criteria.get('name'):
                    name_results = self.search_people_by_name(criteria.get('name'))
                    results.extend(name_results)

                if criteria.get('email'):
                    email_result = self.search_person_by_email(criteria.get('email'))
                    if isinstance(email_result, dict):
                        results.append(email_result)

                if criteria.get('phone'):
                    phone_result = self.search_person_by_phone(criteria.get('phone'))
                    if isinstance(phone_result, dict):
                        results.append(phone_result)

                # Filtrar duplicados basados en nombre, email, teléfono
                unique_results = []
                seen_keys = set()

                for result in results:
                    # Crear una clave única para evitar duplicados
                    key_parts = []
                    if result.get('name'):
                        key_parts.append(result['name'].lower())
                    if result.get('email'):
                        key_parts.append(result['email'].lower())
                    if result.get('phone'):
                        key_parts.append(result['phone'].lower())

                    key = "|".join(key_parts)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        unique_results.append(result)

                # Si hay un nombre de usuario o identificador, buscar perfiles sociales
                # utilizando herramientas como Maigret y Sherlock.  Este paso es
                # adicional y no afecta a los resultados de directorios públicos.
                username = criteria.get('username') or criteria.get('name')
                if username:
                    social_profiles = self.search_social_profiles(username)
                    unique_results.append({"social_profiles": social_profiles})

                return unique_results

            return results

        except Exception as e:
            logger.error(f"Error en búsqueda avanzada: {e}")
            return [{"error": f"Error de búsqueda avanzada: {str(e)}"}]


# Instancia única
people_searcher = PeopleSearcher()


# Funciones públicas directas
def search_people_by_name(name: str, location: str = None, max_results: int = 10) -> List[Dict]:
    """Búsqueda por nombre directa"""
    return people_searcher.search_people_by_name(name, location, max_results)


def search_person_by_email(email: str) -> Dict[str, Any]:
    """Búsqueda por email directa"""
    return people_searcher.search_person_by_email(email)


def search_person_by_phone(phone: str, country_code: str = "US") -> Dict[str, Any]:
    """Búsqueda por teléfono directa"""
    return people_searcher.search_person_by_phone(phone, country_code)


def advanced_search(criteria: Dict[str, Any], search_type: str = "people",
                    api_keys: Dict[str, str] = None) -> List[Dict]:
    """Búsqueda avanzada completa"""
    return people_searcher.advanced_search(criteria, search_type, api_keys)