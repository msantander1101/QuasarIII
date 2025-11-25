# modules/search/emailint.py - Versión simplificada y compatible (última actualización)

"""
Búsqueda real de información de email con integración a APIs reales
(HIBP + SkyMem + verificación)
"""
import hashlib
import logging
import requests
import time
import re
import asyncio
import subprocess
import sys
import os
from typing import Dict, List, Any
from core.config_manager import config_manager

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
            # Intentamos importar solo el módulo principal
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
#                 CLASE PRINCIPAL DE BÚSQUEDA
# ============================================================

class EmailSearcher:

    def __init__(self):
        self.session = requests.Session()
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
    #                 INTEGRACIÓN GHUNT SIMPLIFICADA
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

                    return {
                        "success": True,
                        "data": result,
                        "source": "ghunt",
                        "timestamp": time.time()
                    }
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
                except Exception as e:
                    error_msg = f"Error en ejecución de GHunt: {str(e)}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "source": "ghunt",
                        "message": "Imposible ejecutar GHunt",
                        "timestamp": time.time()
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
            return {
                "success": False,
                "error": error_msg,
                "source": "ghunt",
                "timestamp": time.time()
            }

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
        if not self.verify_email_format(email):
            return {"error": "Formato de email inválido", "source": "format"}

        # Obtener todas las fuentes disponibles para este usuario
        sources = self.get_user_email_sources(user_id)
        results = []

        # HIBP - Primera prioridad
        hibp_cfg = sources.get("hibp")
        if hibp_cfg and hibp_cfg.get("enabled") and hibp_cfg.get("api_key"):
            try:
                data = self._check_hibp_breach_real(email, hibp_cfg["api_key"])
                results.append(data)
                if data.get("breached"):
                    # Devolver inmediatamente si se encuentra una brecha
                    return data
            except Exception as e:
                logger.warning(f"Error con HIBP: {e}")

        # GHunt - Segunda prioridad
        if sources.get("ghunt", {}).get("enabled") and GHUNT_AVAILABLE:
            try:
                ghunt_result = self.search_ghunt(email)
                results.append(ghunt_result)
            except Exception as e:
                logger.warning(f"Error con GHunt: {e}")

        # Si no se encontró brecha en ninguna fuente
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

    def verify_email_format(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        return bool(re.match(pattern, email))

    def verify_email_deliverability(self, email: str, user_id: int) -> Dict[str, Any]:
        return {
            "email": email,
            "deliverable": "unknown",
            "source": "basic_verification"
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

        # GHunt - solo si está disponible
        if GHUNT_AVAILABLE:
            try:
                results["ghunt"] = self.search_ghunt(email)
            except Exception as e:
                error_msg = f"Error con GHunt: {str(e)}"
                results["errors"].append(error_msg)
                results["ghunt"] = {"error": error_msg}
        else:
            # Si no está disponible, indicarlo claramente
            results["ghunt"] = {
                "message": "GHunt no disponible en esta instalación",
                "source": "ghunt",
                "available": False
            }

        results["search_time"] = time.time() - start
        return results


# ============================================================
#                INSTANCIA GLOBAL + WRAPPERS
# ============================================================

email_searcher = EmailSearcher()

check_email_breach = email_searcher.check_email_breach
search_email_paste_accounts = email_searcher.search_email_paste_accounts
verify_email_format = email_searcher.verify_email_format
verify_email_deliverability = email_searcher.verify_email_deliverability
search_email_info = email_searcher.search_email_info


# Agregar funciones auxiliares si se necesita
def get_ghunt_status() -> Dict[str, Any]:
    """Devolver información sobre el estado de GHunt"""
    return {
        "available": GHUNT_AVAILABLE,
        "install_error": GHUNT_INSTALL_ERROR,
        "message": "GHunt disponible" if GHUNT_AVAILABLE else f"GHunt no disponible (detalles: {GHUNT_INSTALL_ERROR if GHUNT_INSTALL_ERROR else 'Error desconocido'})"
    }