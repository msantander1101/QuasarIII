# ============================================================
#   MÓDULO COMPLETAMENTE REFACTORIZADO Y ENDURECIDO (2025)
#   Email Intelligence Engine — v3.2
#   Incluye: HIBP, GHunt, PASTE, VERIFICATION
#   Autor: Miguel (ascii) + ChatGPT OSINT Engineering
# ============================================================

import hashlib
import re
import time
import logging
import subprocess
import sys
import threading
import asyncio
import json
from typing import Dict, Any, List
from requests import Session
from core.config_manager import config_manager

logger = logging.getLogger(__name__)

# ============================================================
# DETECCIÓN GHUNT (Silenciosa / No Crashea / Auto-Instala)
# ============================================================

GHUNT_AVAILABLE = False
GHUNT_IMPORT_ERROR = None


def safe_import_ghunt() -> bool:
    """Carga GHunt de forma segura sin romper la aplicación."""
    global GHUNT_AVAILABLE, GHUNT_IMPORT_ERROR

    try:
        import ghunt
        from ghunt.modules.email import hunt  # Test
        GHUNT_AVAILABLE = True
        logger.info("GHunt cargado correctamente.")
        return True

    except Exception as e:
        GHUNT_AVAILABLE = False
        GHUNT_IMPORT_ERROR = str(e)
        logger.warning(f"GHunt no disponible: {e}")
        return False


# Intento inicial
safe_import_ghunt()

# Si no está, intentar instalar una vez (no bloqueante)
if not GHUNT_AVAILABLE:
    try:
        logger.info("Instalando GHunt desde GitHub...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade",
            "git+https://github.com/mxrch/GHunt.git"
        ])
        safe_import_ghunt()

    except Exception as e:
        GHUNT_IMPORT_ERROR = str(e)
        logger.error(f"Fallo al instalar GHunt: {e}")


# ============================================================
# UTILIDADES DE EMAIL
# ============================================================

def verify_email_format(email: str) -> bool:
    if not isinstance(email, str):
        return False
    email = email.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$'
    return bool(re.match(pattern, email))


def is_email_like(text: str) -> bool:
    return isinstance(text, str) and '@' in text and '.' in text.split('@')[-1]


# ============================================================
# MOTOR PRINCIPAL
# ============================================================

class EmailSearcher:
    def __init__(self):
        self.session = Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (OSINT-Framework)',
            'Accept': 'application/json'
        })
        self.timeout = 25

        # Cache interno → evita repetir GHunt/HIBP en la misma sesión
        self.cache = {}

    # ========================================================
    #  FUENTES DISPONIBLES PARA EL USUARIO
    # ========================================================

    def get_sources(self, user_id: int) -> Dict[str, Dict]:
        return {
            "hibp": {
                "enabled": bool(config_manager.get_config(user_id, "hibp")),
                "api_key": config_manager.get_config(user_id, "hibp"),
                "requires_api": True
            },
            "ghunt": {
                "enabled": GHUNT_AVAILABLE,
                "requires_api": False
            },
            "paste": {
                "enabled": True,
                "requires_api": False
            },
            "verification": {
                "enabled": True,
                "requires_api": False
            }
        }

    # ============================================================
    #   HAVE I BEEN PWNED (Real)
    # ============================================================

    def hibp_lookup(self, email: str, api_key: str):
        try:
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_hash}"

            response = self.session.get(url, headers={
                "x-apikey": api_key,
                "User-Agent": "OSINT-Toolkit/1.1"
            }, timeout=self.timeout)

            if response.status_code == 200:
                breaches = response.json()
                return {
                    "breached": True,
                    "breach_count": len(breaches),
                    "breaches": breaches,
                    "source": "hibp",
                    "confidence": 0.9
                }

            if response.status_code == 404:
                return {"breached": False, "breach_count": 0, "source": "hibp"}

            if response.status_code == 401:
                return {"error": "API Key incorrecta", "source": "hibp"}

            return {"error": f"HTTP {response.status_code}", "source": "hibp"}

        except Exception as e:
            return {"error": f"HIBP error: {e}", "source": "hibp"}

    # ============================================================
    #   GHUNT – EJECUCIÓN SEGURA, CONTROLADA Y SIN CRASHEO
    # ============================================================

    def ghunt_lookup(self, email: str) -> Dict[str, Any]:
        if not GHUNT_AVAILABLE:
            return {
                "success": False,
                "source": "ghunt",
                "error": "GHunt no está disponible en este entorno"
            }

        # Cache GHunt por email
        if email in self.cache:
            return self.cache[email]

        def extract_structured_gmail_data(g) -> Dict[str, Any]:
            """Devuelve un diccionario limpio con datos principales."""
            structured = {}
            try:
                # Extraer información de persona
                if isinstance(g, dict):
                    if 'person' in g:
                        person = g['person']
                        struct_person = {}

                        metadata = person.get("metadata", {})
                        if 'gaiaId' in metadata:
                            struct_person['gaia_id'] = metadata['gaiaId']
                        if 'bestDisplayName' in metadata:
                            struct_person['display_name'] = metadata['bestDisplayName']
                        if 'formattedName' in metadata:
                            struct_person['name'] = metadata['formattedName']

                        # Email
                        if 'emails' in person:
                            primary_emails = [e for e in person['emails'] if e.get('type') == 'HOME']
                            if primary_emails:
                                struct_person['primary_email'] = primary_emails[0]['value']
                            elif person['emails']:
                                struct_person['primary_email'] = person['emails'][0]['value']

                        # User types
                        user_types = person.get("userTypes", [])
                        if user_types:
                            struct_person['user_type'] = ", ".join(user_types)
                        else:
                            struct_person['user_type'] = 'UNKNOWN'

                        # Services activated
                        active_services = []
                        features = person.get("features", [])
                        if isinstance(features, list):
                            active_services = [f for f in features if isinstance(f, str)]

                        # Si no hay features, buscar alternativas:
                        if not active_services:
                            extensions = g.get('extensions', {})
                            ext_data = extensions.get('GOOGLE_PLUS', {})
                            if 'has_plus' in ext_data:
                                active_services.append('Google Plus' if ext_data['has_plus'] else 'No Plus')

                        struct_person['services'] = active_services

                        # Last edit timestamp
                        if 'lastModifiedTimestamp' in person:
                            struct_person['last_modified'] = person['lastModifiedTimestamp']

                        structured["person"] = struct_person

                    # Si no es dict, hacer lo más simple que sea posible
                    else:
                        structured["raw_gdata"] = g
                else:
                    structured["raw_gdata"] = g

            except Exception as e:
                structured["error"] = f"Error parsing GHunt data: {str(e)}"

            return structured

        try:
            import asyncio
            from ghunt.modules.email import hunt

            async def run():
                try:
                    result = await hunt(None, email)
                    return extract_structured_gmail_data(result)
                except Exception as e:
                    return {"_error": str(e)}

            result = asyncio.run(run())

            if isinstance(result, dict) and "_error" in result:
                err = result["_error"]

                if "429" in err or "Too Many Requests" in err:
                    out = {
                        "success": False,
                        "source": "ghunt",
                        "error": "Google rate-limit (429)",
                        "message": "Google ha bloqueado temporalmente la consulta"
                    }
                else:
                    out = {
                        "success": False,
                        "source": "ghunt",
                        "error": err
                    }

                self.cache[email] = out
                return out

            out = {
                "success": True,
                "source": "ghunt",
                "data": result
            }
            self.cache[email] = out
            return out

        except Exception as e:
            out = {
                "success": False,
                "source": "ghunt",
                "error": str(e)
            }
            self.cache[email] = out
            return out

    # ============================================================
    #   PASTES (Dummy por ahora)
    # ============================================================

    def paste_lookup(self, email: str, user_id: int):
        return {
            "email": email,
            "source": "paste",
            "count": 0,
            "results": []
        }

    # ============================================================
    #   VERIFICACIÓN SIMPLE
    # ============================================================

    def verify_deliverability(self, email: str):
        return {
            "email": email,
            "source": "verification",
            "deliverable": "unknown"
        }

    # ============================================================
    #   FUNCIÓN PRINCIPAL: BUSCAR TODO
    # ============================================================

    def search_email_info(self, email: str, user_id: int) -> Dict[str, Any]:
        start = time.time()
        email = email.strip()

        out = {
            "email": email,
            "timestamp": time.time(),
            "breaches": {},
            "paste": {},
            "verification": {},
            "ghunt": {},
            "errors": [],
            "search_time": 0
        }

        sources = self.get_sources(user_id)
        valid = verify_email_format(email)

        # HIBP
        if sources["hibp"]["enabled"] and valid:
            try:
                out["breaches"] = self.hibp_lookup(email, sources["hibp"]["api_key"])
            except Exception as e:
                out["breaches"] = {"error": str(e)}
                out["errors"].append(str(e))

        # GHunt
        if sources["ghunt"]["enabled"]:
            try:
                raw_result = self.ghunt_lookup(email)
                out["ghuntRaw"] = raw_result  # Solo para debugging

                # Convertimos el resultado útil para mostrar posteriormente
                if raw_result["success"]:
                    structured = raw_result.get("data", {})
                    out["ghunt"] = {
                        "success": True,
                        "source": "ghunt",
                        "data": structured,
                        "timestamp": time.time()
                    }
                else:
                    out["ghunt"] = raw_result

            except Exception as e:
                out["ghunt"] = {"error": str(e)}
                out["errors"].append(str(e))

        # PASTES
        try:
            out["paste"] = self.paste_lookup(email, user_id)
        except Exception as e:
            out["paste"] = {"error": str(e)}
            out["errors"].append(str(e))

        # VERIFICATION
        try:
            out["verification"] = self.verify_deliverability(email)
        except Exception as e:
            out["verification"] = {"error": str(e)}
            out["errors"].append(str(e))

        out["search_time"] = time.time() - start
        return out


# ============================================================
# FUNCIONES GLOBALES (mantener compatibilidad existente)
# ============================================================

def check_email_breach(email: str, user_id: int) -> Dict[str, Any]:
    return EmailSearcher().hibp_lookup(email, config_manager.get_config(user_id, "hibp"))


def search_email_info(email: str, user_id: int) -> Dict[str, Any]:
    return EmailSearcher().search_email_info(email, user_id)


def search_email_paste_accounts(email: str, user_id: int) -> Dict[str, Any]:
    return EmailSearcher().paste_lookup(email, user_id)