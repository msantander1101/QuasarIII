# modules/search/emailint.py

"""
Búsqueda real de información de email con integración a APIs reales
(HIBP + SkyMem + GHunt + verificación)
"""
import io
import sys
import hashlib
import logging
import requests
import time
import json
import re
import asyncio
import subprocess
import os
from typing import Dict, List, Any
from core.config_manager import config_manager

logger = logging.getLogger(__name__)

# ============================================================
#                AUTO-INSTALACIÓN GHUNT
# ============================================================

def ensure_ghunt_installed() -> bool:
    """
    Comprueba si GHunt está instalado. Si no lo está, intenta instalarlo desde GitHub.
    """
    try:
        import ghunt
        return True
    except ImportError:
        try:
            print("Instalando GHunt automáticamente...")
            subprocess.check_call([
                sys.executable,
                "-m",
                "pip",
                "install",
                "git+https://github.com/mxrch/GHunt.git"
            ])
            import ghunt
            return True
        except Exception as e:
            print("ERROR: No se pudo instalar GHunt:", e)
            return False


GHUNT_AVAILABLE = ensure_ghunt_installed()

# ============================================================
#               IMPORTAR GHUNT (SI EXISTE)
# ============================================================

try:
    from ghunt.modules.email import hunt as ghunt_hunt
    GHUNT_AVAILABLE = True
    logger.info("GHunt está disponible para búsquedas de emails.")
except ImportError:
    GHUNT_AVAILABLE = False
    logger.warning("GHunt no está disponible. Las búsquedas de GHunt serán omitidas.")


# ============================================================
#            FUNCIONES AUXILIARES PARA GHUNT
# ============================================================

def ghunt_tokens_exist() -> bool:
    """
    Verifica si existe el archivo de tokens requerido por GHunt.
    """
    config_path = os.path.expanduser("~/.config/ghunt/tokens.json")
    return os.path.isfile(config_path) and os.path.getsize(config_path) > 50



# ============================================================
#                 CLASE PRINCIPAL DE BÚSQUEDA
# ============================================================

class EmailSearcher:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json'
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
    #                 INTEGRACIÓN GHUNT
    # ============================================================

    def search_ghunt(self, email: str) -> Dict[str, Any]:
        if not GHUNT_AVAILABLE:
            return {"success": False, "error": "GHunt no disponible", "source": "ghunt"}

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(ghunt_hunt(None, email))
            loop.close()

            # Validar que result tenga datos antes de acceder a listas
            if not result or not isinstance(result, dict):
                return {"success": False, "error": "GHunt retornó datos vacíos", "source": "ghunt"}

            return {
                "success": True,
                "data": result,
                "source": "ghunt",
                "timestamp": time.time()
            }
        except IndexError as e:
            # Este es el error “list index out of range”
            logger.warning(f"GHunt: lista vacía para email {email} - {str(e)}")
            return {"success": False, "error": "GHunt: lista vacía para este email", "source": "ghunt"}
        except Exception as e:
            logger.error(f"Error inesperado en GHunt: {e}")
            return {"success": False, "error": f"Error GHunt: {str(e)}", "source": "ghunt"}

    # ============================================================
    #              HIBP — CHECK REAL
    # ============================================================

    def _check_hibp_breach_real(self, email: str, api_key: str) -> Dict[str, Any]:
        try:
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_hash}"

            r = self.session.get(
                url,
                headers={"x-apikey": api_key},
                timeout=self.timeout
            )

            if r.status_code == 200:
                data = r.json()
                return {
                    "breached": True,
                    "breaches": data,
                    "breach_count": len(data),
                    "source": "hibp"
                }

            if r.status_code == 404:
                return {"breached": False, "breach_count": 0, "source": "hibp"}

            if r.status_code == 401:
                return {"error": "API key incorrecta HIBP", "source": "hibp"}

            return {"error": f"Error HTTP {r.status_code}", "source": "hibp"}

        except Exception as e:
            return {"error": f"HIBP error: {e}", "source": "hibp"}

    # ============================================================
    #         WRAPPER PRINCIPAL DE BÚSQUEDA DE BRECHAS
    # ============================================================

    def check_email_breach(self, email: str, user_id: int) -> Dict[str, Any]:
        if not self.verify_email_format(email):
            return {"error": "Formato de email inválido", "source": "format"}

        sources = self.get_user_email_sources(user_id)
        results = []

        # HIBP
        hibp_cfg = sources.get("hibp")
        if hibp_cfg and hibp_cfg.get("enabled"):
            data = self._check_hibp_breach_real(email, hibp_cfg["api_key"])
            results.append(data)
            if data.get("breached"):
                return data  # prioridad máxima

        # GHunt
        if sources.get("ghunt", {}).get("enabled"):
            gh = self.search_ghunt(email)
            results.append(gh)

        # Combinar
        breached = any(r.get("breached") for r in results)
        total = sum(r.get("breach_count", 0) for r in results if r.get("breached"))

        return {
            "breached": breached,
            "breach_count": total,
            "details": results,
            "source": "combined"
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
            results["errors"].append(str(e))

        # Paste
        try:
            results["paste"] = self.search_email_paste_accounts(email, user_id)
        except Exception as e:
            results["errors"].append(str(e))

        # Verificación
        try:
            results["verification"] = self.verify_email_deliverability(email, user_id)
        except Exception as e:
            results["errors"].append(str(e))

        # GHunt directo
        try:
            results["ghunt"] = self.search_ghunt(email)
        except Exception as e:
            results["errors"].append(f"GHunt: {e}")

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
