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
    # Evitar errores de tipo None
    if not email:
        return False
    # Normalizar el email (borrar espacios)
    email = email.strip()
    if not email:
        return False
    # Patrón más flexible pero aún válido
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_email_like_string(text: str) -> bool:
    """Verifica si un texto es similar a un email (útil para búsquedas en nombre de usuario)"""
    # Comprobar si es probablemente un email
    if not text or not isinstance(text, str):
        return False
    # Si contiene @, probablemente sea un email o algo parecido
    return '@' in text and '.' in text.split('@')[1]


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
        Verifica brechas de seguridad para un email. Si el formato no es válido,
        intenta verificar si es potencialmente un email o similar.
        """
        # Validar primeramente si es una cadena válida
        if not email or not isinstance(email, str):
            return {"error": "Formato de email inválido", "source": "format"}

        # Normalizar el email
        normalized_email = email.strip()
        if not normalized_email:
            return {"error": "Formato de email inválido", "source": "format"}

        # Intentar verificar formato de email
        if verify_email_format(normalized_email):
            # Es un email válido directamente
            pass
        elif is_valid_email_like_string(normalized_email):
            # Puede ser potencialmente un email, intentarlo como tal
            pass
        else:
            # No es un email ni parece tener forma de correo
            # Pero aún así no abortar inmediatamente, podría estar buscando información general
            # Solo mostrar aviso y continuar (ver implementación de más abajo)
            logger.warning(f"Email '{normalized_email}' no sigue formato estándar, pero se procede")

        # Obtener todas las fuentes disponibles para este usuario
        sources = self.get_user_email_sources(user_id)
        results = []

        # HIBP - Primera prioridad
        hibp_cfg = sources.get("hibp")
        if hibp_cfg and hibp_cfg.get("enabled") and hibp_cfg.get("api_key"):
            try:
                # Verificar si el input tiene formato válido antes de usarlo
                if verify_email_format(normalized_email):
                    data = self._check_hibp_breach_real(normalized_email, hibp_cfg["api_key"])
                    results.append(data)
                    if data.get("breached"):
                        # Devolver inmediatamente si se encuentra una brecha
                        return data
                else:
                    # Si no tiene formato de email válido pero es candidato,
                    # podríamos aún buscar en bases de datos de brechas
                    # pero esto depende de la lógica interna de la API
                    logger.warning("Email potencial no válido para HIBP, omitiendo este método")
            except Exception as e:
                logger.warning(f"Error con HIBP: {e}")

        # GHunt - Segunda prioridad
        if sources.get("ghunt", {}).get("enabled") and GHUNT_AVAILABLE:
            try:
                ghunt_result = self.search_ghunt(normalized_email)  # Ya no se pasa como email si no es válido
                # Añadir resultado de GHunt con validación de resultado
                if isinstance(ghunt_result, dict) and not ghunt_result.get('success', True):
                    # Si GHunt falló en validar como correo, puede haber fallado por formato
                    logger.info("GHunt reportó errores, posiblemente por formato de email.")
                results.append(ghunt_result)
            except Exception as e:
                logger.warning(f"Error con GHunt: {e}")

        # Si no se encontró brecha en ninguna fuente y no es un formato válido, informar
        if not results and not verify_email_format(normalized_email):
            # Devolver respuesta que indica que no es email válido pero se pudo buscar
            return {
                "breached": False,
                "breach_count": 0,
                "source": "no_breach_found",
                "confidence": 0.3,  # Menor confianza por no ser email estándar
                "message": "No se encontraron brechas de seguridad (correo no válido)",
                "query": normalized_email
            }

        # Si no se encontró brecha en ninguna fuente y es email válido
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
            return {
                "breached": False,
                "breach_count": 0,
                "source": "no_breach_found",
                "confidence": 0.5
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