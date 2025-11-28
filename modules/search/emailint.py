# modules/search/emailint.py

import hashlib
import re
import time
import logging
import subprocess
import sys
import importlib.util
import asyncio
import json
from typing import Dict, Any, List
from requests import Session

from core.config_manager import config_manager

# Configurar logger
logger = logging.getLogger(__name__)

# ============================================================
#                DETECCIÓN Y AUTO-INSTALACIÓN GHUNT
# ============================================================

GHUNT_AVAILABLE = False
GHUNT_INSTALL_ERROR = None


def check_ghunt_availability():
    """Función para comprobar la disponibilidad de GHunt más robustamente"""
    global GHUNT_AVAILABLE

    try:
        # Intentamos importar las partes fundamentales de GHunt
        import ghunt

        # Comprobamos si podemos importar directamente el módulo de email
        try:
            from ghunt.modules.email import hunt as ghunt_hunt
            GHUNT_AVAILABLE = True
            logger.info("GHunt disponible completamente")
            return True
        except ImportError as e:
            logger.warning(f"No se puede importar módulo email de GHunt: {e}")
            # Intente importar solo el módulo principal
            try:
                import ghunt.modules.email
                GHUNT_AVAILABLE = True
                logger.info("GHunt disponible (solo módulo principal)")
                return True
            except Exception:
                GHUNT_AVAILABLE = False
                logger.warning("GHunt no disponible completamente")
                return False

    except ImportError:
        logger.warning("GHunt no encontrado en el sistema")
        return False


# Intentar instalar GHunt desde GitHub
try:
    # Primero intentar verificar si ya está instalado
    if check_ghunt_availability():
        GHUNT_AVAILABLE = True
    else:
        logger.info("Instalando GHunt desde GitHub...")
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "git+https://github.com/mxrch/GHunt.git"
        ])

        # Reintentar verificación
        if check_ghunt_availability():
            GHUNT_AVAILABLE = True
            logger.info("GHunt instalado y disponible")
        else:
            GHUNT_AVAILABLE = False
            GHUNT_INSTALL_ERROR = "GHunt instalado pero no disponible"
            logger.warning("GHunt instalado pero no disponible tras reinicio")

except Exception as e:
    GHUNT_AVAILABLE = False
    GHUNT_INSTALL_ERROR = str(e)
    logger.warning(f"Error en instalación de GHunt: {e}")


# ============================================================
#        FUNCIONES AUXILIARES DISPONIBLES GLOBALMENTE
# ============================================================

def verify_email_format(email: str) -> bool:
    """Verifica el formato de un correo electrónico."""
    # Evitar errores de tipo None o vacío
    if not email or not isinstance(email, str):
        return False
    # Normalizar el email (borrar espacios)
    email = email.strip()
    if not email:
        return False
    # Patrón más flexible en algunas condiciones
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_email_like_string(text: str) -> bool:
    """Verifica si un texto es similar a un email (útil para búsquedas en nombre de usuario)"""
    # Comprobar si es probablemente un email
    if not text or not isinstance(text, str):
        return False
    # Si contiene @, probablemente sea un email o algo parecido
    return '@' in text and '.' in text.split('@')[1]


def sanitize_query_for_email_search(query: str) -> str:
    """
    Intenta corregir o sanitizar una consulta para poder usarla en búsqueda de email.
    Esto puede ser útil si se introduce un nombre en lugar de correo.
    """
    if not query or not isinstance(query, str):
        return ""

    # Normalizar el texto
    query = query.strip()

    # Intentamos extraer una posible dirección de email si hay @ en el texto
    if '@' in query:
        # Dividimos por espacios y buscamos fragmentos con @
        parts = query.split()
        for part in parts:
            if '@' in part and '.' in part.split('@')[1]:
                return part

    # Si no encontramos email claro, pero tiene estructura de nombre
    # intentamos formatearlo como posible email (puede ser usado en otras búsquedas)
    return query


# ============================================================
#                 CLASE PRINCIPAL DE BÚSQUEDA
# ============================================================

class EmailSearcher:

    def __init__(self):
        self.session = Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.timeout = 30

    # --------------------------------------------
    # Obtener fuentes disponibles
    # --------------------------------------------

    def get_user_email_sources(self, user_id: int) -> Dict[str, Dict]:
        sources = {}

        api_dependent_sources = {
            'hibp': 'hibp',
            'skymem': 'skymem',
            'hunter': 'hunter',
            'gmail_searcher': 'gmail_searcher'
        }

        no_api_sources = {
            'email_search': 'email_search',
            'email_verification': 'email_verification',
        }

        for key, source_name in api_dependent_sources.items():
            api_key = config_manager.get_config(user_id, key)
            sources[source_name] = {
                'enabled': bool(api_key),
                'requires_api': True,
                'api_key': api_key
            }

        for source_name in no_api_sources:
            sources[source_name] = {
                'enabled': True,
                'requires_api': False
            }

        # GHunt como fuente opcional
        sources['ghunt'] = {
            'enabled': GHUNT_AVAILABLE,
            'requires_api': False
        }

        return sources

    # ============================================================
    #              HIBP — CHECK REAL
    # ============================================================

    def _check_hibp_breach_real(self, email: str, api_key: str) -> Dict[str, Any]:
        try:
            # Hashear el correo electrónico para HIBP
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_hash}"

            response = self.session.get(
                url,
                headers={
                    "x-apikey": api_key,
                    "User-Agent": "OSINT-Toolkit/1.0"
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "breached": True,
                    "breaches": data,
                    "breach_count": len(data),
                    "source": "hibp",
                    "confidence": 0.9
                }

            if response.status_code == 404:
                return {"breached": False, "breach_count": 0, "source": "hibp", "confidence": 0.8}

            if response.status_code == 401:
                return {"error": "API key incorrecta HIBP", "source": "hibp"}

            return {"error": f"Error HTTP {response.status_code}: {response.text}", "source": "hibp"}

        except Exception as e:
            return {"error": f"HIBP error: {str(e)}", "source": "hibp"}

    # ============================================================
    #         WRAPPER PRINCIPAL DE BÚSQUEDA DE BRECHAS
    # ============================================================

    def check_email_breach(self, email: str, user_id: int) -> Dict[str, Any]:
        """
        Verifica brechas de seguridad para un email.
        Si no tiene formato válido, intenta manejar entradas como nombres.
        """
        # Primer validación: si viene vacía o no es una cadena
        if not email or not isinstance(email, str):
            return {
                "error": "Entrada vacía o no válida para búsqueda de correo",
                "source": "format",
                "message": "Por favor ingrese un valor válido"
            }

        # Normalizar el email
        normalized_email = email.strip()
        if not normalized_email:
            return {
                "error": "Entrada vacía para búsqueda de correo",
                "source": "format",
                "message": "Por favor ingrese un valor válido"
            }

        # Llamada al validador de formato
        is_valid = verify_email_format(normalized_email)
        is_email_like = is_valid_email_like_string(normalized_email)

        logger.debug(f"Validando correo: '{normalized_email}', válido: {is_valid}, email-like: {is_email_like}")

        # Verificar y preparar datos para el chequeo
        check_email = normalized_email

        # Obtener todas las fuentes disponibles para este usuario
        sources = self.get_user_email_sources(user_id)
        results = []

        # HIBP - Primera prioridad (solo si tiene formato de correo)
        hibp_cfg = sources.get("hibp")
        if hibp_cfg and hibp_cfg.get("enabled") and hibp_cfg.get("api_key"):
            # Solo ejecutar HIBP si parece realmente un email
            if is_valid:
                try:
                    data = self._check_hibp_breach_real(check_email, hibp_cfg["api_key"])
                    results.append(data)
                    if data.get("breached"):
                        # Devolver inmediatamente si se encuentra una brecha
                        return data
                except Exception as e:
                    logger.warning(f"Error con HIBP: {e}")
            elif is_email_like:
                # Si es potencialmente un correo, puede que la busqueda se haga de forma más amplia
                logger.info(f"Email potencial '{check_email}' (pero no válido formal).")
                # Podríamos optar por no usar HIBP para este tipo de entrada o continuar
                # Como no es formato claro, se puede continuar pero con menos peso
            else:
                # No es email válido ni potencial, se deja de buscar brechas por HIBP
                logger.info(f"Valor '{check_email}' no cumple formato de email, omitiendo HIBP.")

        # GHunt - Segunda prioridad
        if sources.get("ghunt", {}).get("enabled") and GHUNT_AVAILABLE:
            try:
                # Para GHunt, podemos pasar cualquier valor, pero si no es válido, usamos un aviso
                ghunt_result = self.search_ghunt(check_email)
                # Añadir resultado de GHunt con validación de resultado
                if isinstance(ghunt_result, dict) and not ghunt_result.get('success', True):
                    # Esto podría ser porque GHunt no acepta el formato si no es estrictamente email
                    logger.info("GHunt reportó errores posiblemente relacionados con formato de email.")
                results.append(ghunt_result)
            except Exception as e:
                logger.warning(f"Error con GHunt: {e}")

        # Combinar los resultados (si hay alguno)
        if results:
            # Combinar los resultados
            overall_breached = any(r.get("breached", False) for r in results)
            total_breaches = sum(r.get("breach_count", 0) for r in results if r.get("breached"))

            # Preparar resultado combinado
            combined = {
                "breached": overall_breached,
                "breach_count": total_breaches,
                "details": results,
                "source": "combined",
                "confidence": 0.7 if overall_breached else 0.3
            }
            return combined
        else:
            # No se encontraron brechas
            # Devolver resultado con información de tipo de búsqueda hecho
            if is_valid:
                # Si fue email válido, se indica que no se encontró brecha
                return {
                    "breached": False,
                    "breach_count": 0,
                    "source": "no_breach_found",
                    "confidence": 0.5,
                    "message": "No se encontraron brechas de seguridad para este correo"
                }
            else:
                # Si no era email válido, aún puede devolver datos de otras fuentes
                # (pero esto es más difícil con HIBP y GHunt en la mayor parte de casos)
                return {
                    "breached": False,
                    "breach_count": 0,
                    "source": "no_breach_found",
                    "confidence": 0.3,
                    "message": "No se realizó búsqueda en bases de datos de brechas (dato no válido)",
                    "query_type": "potencial_usuario_nombre" if not is_valid else "email_formato_valido"
                }

    # ============================================================
    #        SERVICIOS EXTRAS: PASTE + VERIFICACIÓN
    # ============================================================

    def search_email_paste_accounts(self, email: str, user_id: int) -> Dict[str, Any]:
        return {
            "email": email,
            "paste_count": 0,
            "message": "Búsqueda de paste no implementada",
            "source": "paste"
        }

    def verify_email_deliverability(self, email: str, user_id: int) -> Dict[str, Any]:
        return {
            "email": email,
            "deliverable": "unknown",
            "source": "basic_verification"
        }

    # ============================================================
    #                 INTEGRACIÓN GHUNT CON MANEJO DE ERRORES
    # ============================================================

    def search_ghunt(self, email: str) -> Dict[str, Any]:
        # Si GHunt no está disponible, devolver resultado indicando que no está disponible
        if not GHUNT_AVAILABLE:
            return {
                "success": False,
                "error": "GHunt no disponible",
                "source": "ghunt",
                "message": "GHunt no está disponible o instalado correctamente",
                "timestamp": time.time()
            }

        try:
            # Intentar importar exactamente como se haría normalmente
            # Primero intentar lo que funciona según los imports que están bien

            # Importar usando el módulo de email (forma más directa)
            try:
                from ghunt.modules.email import hunt as ghunt_hunt
                success = True
                message = "Módulo de email importado correctamente"
            except ImportError as e:
                logger.warning(f"Fallo al importar ghunt_hunt: {e}")
                success = False
                message = f"Fallo al importar: {str(e)}"

            # Si tenemos éxito en la importación, intentamos invocar GHunt
            if success:
                try:
                    # Usar un bucle de eventos seguro
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Invocar la función con manejo específico de errores
                    result = loop.run_until_complete(ghunt_hunt(None, email))
                    loop.close()

                    # Verificar resultado
                    if not result:
                        return {
                            "success": False,
                            "error": "GHunt devolvió datos vacíos",
                            "source": "ghunt",
                            "message": "GHunt no devolvió datos para este email",
                            "timestamp": time.time()
                        }

                    # Formatear correctamente el resultado
                    formatted_result = {
                        "success": True,
                        "data": result,
                        "source": "ghunt",
                        "timestamp": time.time()
                    }

                    # Intentar hacer validación adicional si es necesario
                    if isinstance(result, dict):
                        # Verificar estructura de resultado aceptable
                        if result.get('error') or len(str(result)) < 10:
                            return {
                                "success": False,
                                "error": "Respuesta inválida de GHunt",
                                "source": "ghunt",
                                "message": "GHunt no encontró información para este email",
                                "raw_data": str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                                "timestamp": time.time()
                            }

                    return formatted_result

                except IndexError as e:
                    # Manejar específicamente el error "list index out of range"
                    error_msg = f"GHunt: lista vacía para email {email} - {str(e)}"
                    logger.warning(error_msg)
                    return {
                        "success": False,
                        "error": "List index out of range en GHunt",
                        "source": "ghunt",
                        "message": "GHunt no encontró información para este email (posiblemente lista vacía)",
                        "timestamp": time.time()
                    }
                except json.JSONDecodeError as e:
                    # Especificamente manejar el caso de la respuesta JSON vacía
                    logger.debug(f"Error de JSON en GHunt: {e}")
                    error_str = str(e)
                    if "Expecting value: line 1 column 1 (char 0)" in error_str:
                        # Solo informar en modo debug para evitar spam en logs
                        return {
                            "success": False,
                            "error": "GHunt: datos vacíos o respuesta vacía",
                            "source": "ghunt",
                            "message": "No se obtuvo información válida de GHunt para este email (posiblemente no encontrado)",
                            "timestamp": time.time()
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Formato inválido en respuesta de GHunt",
                            "source": "ghunt",
                            "message": "GHunt devolvió respuesta no válida",
                            "timestamp": time.time()
                        }
                except Exception as e:
                    error_msg = f"Error en ejecución de GHunt: {str(e)}"
                    logger.error(error_msg)
                    detailed_error = str(e)
                    # Detectar si es el error específico que mencionaste
                    if "Expecting value: line 1 column 1 (char 0)" in detailed_error:
                        return {
                            "success": False,
                            "error": "GHunt: datos vacíos o respuesta vacía",
                            "source": "ghunt",
                            "message": "GHunt no encontró información para este email",
                            "raw_error": detailed_error,
                            "timestamp": time.time()
                        }
                    else:
                        return {
                            "success": False,
                            "error": error_msg,
                            "source": "ghunt"
                        }
            else:
                # Si no se pudo importar, devolver error
                return {
                    "success": False,
                    "error": "No se pudo importar módulo GHunt",
                    "source": "ghunt",
                    "message": message,
                    "timestamp": time.time()
                }

        except Exception as e:
            error_msg = f"Error general en GHunt: {str(e)}"
            logger.error(error_msg)
            # Detectar casos específicos de error
            detailed_error = str(e)
            if "Expecting value: line 1 column 1 (char 0)" in detailed_error:
                return {
                    "success": False,
                    "error": "GHunt: datos vacíos o respuesta vacía",
                    "source": "ghunt",
                    "message": "GHunt no encontró información para este email",
                    "raw_error": detailed_error,
                    "timestamp": time.time()
                }
            return {
                "success": False,
                "error": error_msg,
                "source": "ghunt",
                "timestamp": time.time()
            }

    # ============================================================
    #            FUNCIÓN PRINCIPAL DE BÚSQUEDA COMPLETA
    # ============================================================

    def search_email_info(self, email: str, user_id: int, services: List[str] = None) -> Dict[str, Any]:
        start = time.time()

        results = {
            "email": email,
            "timestamp": time.time(),
            "breaches": {},
            "paste": {},
            "verification": {},
            "ghunt": {},
            "search_time": 0,
            "errors": []
        }

        # Brechas
        try:
            results["breaches"] = self.check_email_breach(email, user_id)
        except Exception as e:
            error_msg = f"Error buscando brechas: {str(e)}"
            results["errors"].append(error_msg)
            results["breaches"] = {"error": error_msg}

        # Paste
        try:
            results["paste"] = self.search_email_paste_accounts(email, user_id)
        except Exception as e:
            error_msg = f"Error buscando paste: {str(e)}"
            results["errors"].append(error_msg)
            results["paste"] = {"error": error_msg}

        # Verificación
        try:
            results["verification"] = self.verify_email_deliverability(email, user_id)
        except Exception as e:
            error_msg = f"Error verificando email: {str(e)}"
            results["errors"].append(error_msg)
            results["verification"] = {"error": error_msg}

        # GHunt
        try:
            results["ghunt"] = self.search_ghunt(email)
        except Exception as e:
            error_msg = f"Error buscando con GHunt: {str(e)}"
            results["errors"].append(error_msg)
            results["ghunt"] = {"error": error_msg}

        # Tiempo de búsqueda
        results["search_time"] = time.time() - start

        # Devolver resultados
        return results


# ============================================================
#           FUNCIÓN GLOBAL PARA IMPORTACIÓN DIRECTA
# ============================================================

# Función para verificar brechas de correo (función global)
def check_email_breach(email: str, user_id: int) -> Dict[str, Any]:
    """
    Función global para verificar brechas de correo electrónico.

    Esta función permite importar directamente check_email_breach sin requerir
    crear una instancia de EmailSearcher primero.

    Args:
        email (str): Dirección de correo electrónico a verificar
        user_id (int): ID del usuario solicitante para buscar configuraciones

    Returns:
        Dict[str, Any]: Resultados de la verificación de brechas
    """
    searcher = EmailSearcher()
    return searcher.check_email_breach(email, user_id)


# Función para realizar búsqueda completa de correo (función global)
def search_email_info(email: str, user_id: int, services: List[str] = None) -> Dict[str, Any]:
    """
    Función global para búsqueda completa de correo electrónico.

    Esta función permite importar directamente search_email_info sin requerir
    crear una instancia de EmailSearcher primero.

    Args:
        email (str): Dirección de correo electrónico a buscar
        user_id (int): ID del usuario solicitante para buscar configuraciones
        services (List[str], optional): Lista de servicios específicos a usar

    Returns:
        Dict[str, Any]: Resultados completos de la búsqueda
    """
    searcher = EmailSearcher()
    return searcher.search_email_info(email, user_id, services)


# Función para buscar paste de correo (función global)
def search_email_paste_accounts(email: str, user_id: int) -> Dict[str, Any]:
    """
    Función global para buscar cuentas de paste asociadas a un correo.

    Args:
        email (str): Dirección de correo electrónico a buscar
        user_id (int): ID del usuario solicitante

    Returns:
        Dict[str, Any]: Resultados de la búsqueda de paste
    """
    searcher = EmailSearcher()
    return searcher.search_email_paste_accounts(email, user_id)