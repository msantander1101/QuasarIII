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
        """
        Realiza una búsqueda de perfiles sociales para un nombre dado usando
        herramientas OSINT (Maigret y Sherlock) y devuelve los resultados
        encapsulados en una lista.  Si las herramientas no están instaladas,
        se devolverá una estructura con mensajes de error que se mostrarán
        en la interfaz.  Esta implementación sustituye los resultados
        simulados por datos reales o mensajes informativos.
        """
        try:
            if not name:
                return []
            # Buscar perfiles sociales utilizando el nombre como identificador.
            social_profiles = self.search_social_profiles(name)
            # Devolver los perfiles sociales encapsulados para su posterior
            # visualización en la interfaz.
            return [{"social_profiles": social_profiles}]
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
        """
        Devuelve un diccionario vacío ya que no contamos con un servicio de
        verificación de correos en este entorno.  Esto evita resultados
        simulados que pudieran confundir al usuario.
        """
        try:
            # En un escenario real se integrará con servicios de verificación
            # de correos como Hunter.io, etc. Aquí simplemente devolvemos
            # un diccionario vacío.
            return {}
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
        """
        Devuelve un diccionario vacío ya que no contamos con un servicio
        real de búsqueda por teléfono en este entorno.  Se evita así
        devolver resultados simulados.
        """
        try:
            # En un entorno real, este método se conectaría con APIs de
            # búsqueda de números telefónicos.  Actualmente, devolvemos
            # un diccionario vacío.
            return {}
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
                    # Solo agregar si el resultado no está vacío
                    if isinstance(email_result, dict) and email_result:
                        results.append(email_result)

                if criteria.get('phone'):
                    phone_result = self.search_person_by_phone(criteria.get('phone'))
                    # Solo agregar si el resultado no está vacío
                    if isinstance(phone_result, dict) and phone_result:
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

                # Ya se incluye la búsqueda de perfiles sociales en
                # `search_people_by_name`, por lo que no es necesario ejecutar
                # nuevamente la búsqueda aquí.  Si se requiere una búsqueda
                # adicional, podría integrarse en el futuro.

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


# --- NUEVA FUNCIÓN ---
def search_social_profiles(identifier: str) -> Dict[str, Any]:
    """
    Búsqueda directa de perfiles sociales utilizando herramientas OSINT.

    Esta función actúa como un envoltorio de la función de instancia
    ``PeopleSearcher.search_social_profiles`` para exponerla a otros módulos
    (por ejemplo ``socmint``) que esperan una función pública. Si no se
    proporciona un identificador válido, se devuelve un diccionario vacío.

    Args:
        identifier: Nombre de usuario o identificador a buscar.

    Returns:
        Un diccionario con los resultados de Maigret y Sherlock o con
        mensajes de error si las herramientas no están instaladas o no
        devuelven datos.
    """
    try:
        if not identifier:
            return {}
        return people_searcher.search_social_profiles(identifier)
    except Exception as exc:
        logger.error(f"Error en search_social_profiles: {exc}")
        return {"error": str(exc)}
