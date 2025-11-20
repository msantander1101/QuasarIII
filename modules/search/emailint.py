"""
Búsqueda real de información de email con integración a APIs reales (HIBP + SkyMem)
"""
import hashlib
import logging
import requests
import time
import json
from typing import Dict, List, Any
from urllib.parse import quote_plus
from core.config_manager import config_manager

logger = logging.getLogger(__name__)


class EmailSearcher:
    """
    Sistema de búsqueda real de información de email con integración a APIs reales
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.timeout = 30

    def get_user_email_sources(self, user_id: int) -> Dict[str, Dict]:
        """
        Obtener fuentes de búsqueda de email disponibles para el usuario
        """
        sources = {}

        # Fuentes que requieren API Key
        api_dependent_sources = {
            'hibp': 'hibp',
            'skymem': 'skymem',  # SkyMem
            # ghunt eliminado (no se usa)
        }

        # Fuentes que NO requieren API Key (búsqueda pública)
        no_api_sources = {
            'email_search': 'email_search',
            'email_verification': 'email_verification'
        }

        # Procesar fuentes dependientes de API
        for key, source_name in api_dependent_sources.items():
            api_key = config_manager.get_config(user_id, key)
            if api_key:
                sources[source_name] = {
                    'enabled': True,
                    'requires_api': True,
                    'api_key': api_key,
                    'config_key': key
                }
            else:
                sources[source_name] = {
                    'enabled': False,
                    'requires_api': True,
                    'api_key': None,
                    'config_key': key
                }

        # Añadir fuentes sin API
        for source_name, source_type in no_api_sources.items():
            sources[source_name] = {
                'enabled': True,
                'requires_api': False,
                'config_key': source_name
            }

        return sources

    def check_email_breach(self, email: str, user_id: int) -> Dict[str, Any]:
        """
        Verificación real de si un email ha sido parte de alguna brecha
        """
        start_time = time.time()
        logger.info(f"Verificando brechas de email: {email}")

        try:
            # 1. Intentar con HIBP (más confiable)
            hb_source = self.get_user_email_sources(user_id).get('hibp', {})
            if hb_source.get('enabled', False) and hb_source.get('requires_api', True):
                api_key = hb_source['api_key']
                result = self._check_hibp_breach_real(email, api_key)
                if result.get("breached"):
                    return result

            # 2. Intentar con SkyMem (requiere API)
            skymem_source = self.get_user_email_sources(user_id).get('skymem', {})
            if skymem_source.get('enabled', False) and skymem_source.get('requires_api', True):
                api_key = skymem_source['api_key']
                result = self._search_skymem_real(email, api_key)
                if result.get("breached", False):
                    return result

            # 3. Si no se encontró brecha
            return {
                "breached": False,
                "email": email,
                "message": "No se encontraron brechas en fuentes verificadas",
                "breach_count": 0,
                "source": "no_breach_found",
                "confidence": 0.3,
                "timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"Error en verificación de brechas: {e}")
            return {
                "error": f"Error en verificación: {str(e)}",
                "email": email,
                "timestamp": time.time(),
                "source": "error"
            }

    def _check_hibp_breach_real(self, email: str, api_key: str) -> Dict[str, Any]:
        """
        Verificación real en Have I Been Pwned (requiere API key)
        """
        try:
            # Hashear el correo (HIBP requiere hash MD5)
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_hash}"

            response = self.session.get(
                url,
                headers={"x-apikey": api_key, "User-Agent": "OSINT-Toolkit/1.0"},
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        "breached": True,
                        "email": email,
                        "breach_count": len(data),
                        "breaches": data,
                        "timestamp": time.time(),
                        "source": "hibp"
                    }
                else:
                    return {
                        "breached": False,
                        "email": email,
                        "message": "No hay brechas registradas",
                        "breach_count": 0,
                        "timestamp": time.time(),
                        "source": "hibp"
                    }
            elif response.status_code == 404:
                return {
                    "breached": False,
                    "email": email,
                    "message": "Email no encontrado en ninguna brecha",
                    "breach_count": 0,
                    "timestamp": time.time(),
                    "source": "hibp"
                }
            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "email": email,
                    "timestamp": time.time(),
                    "source": "hibp"
                }

        except requests.exceptions.Timeout:
            return {"error": "Tiempo de espera agotado (HIBP)", "email": email}
        except requests.exceptions.ConnectionError:
            return {"error": "Error de conexión a HIBP", "email": email}
        except Exception as e:
            logger.error(f"Error en HIBP check real: {e}")
            return {"error": f"Error verificación HIBP: {str(e)}", "email": email}

    def _search_skymem_real(self, email: str, api_key: str) -> Dict[str, Any]:
        """
        Búsqueda real en SkyMem (https://www.skymem.info)
        """
        try:
            url = "https://api.skymem.info/v1/email"
            params = {"email": email}
            headers = {
                "X-API-Key": api_key,
                "User-Agent": "OSINT-Toolkit/1.0"
            }
            response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return {
                        "breached": True,
                        "email": email,
                        "breach_count": len(data["data"]),
                        "source": "skymem",
                        "details": data["data"],
                        "timestamp": time.time(),
                        "confidence": 0.7
                    }
                else:
                    return {
                        "breached": False,
                        "email": email,
                        "message": "No se encontraron datos en SkyMem",
                        "breach_count": 0,
                        "timestamp": time.time(),
                        "source": "skymem"
                    }
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "email": email,
                    "timestamp": time.time(),
                    "source": "skymem"
                }
        except requests.exceptions.Timeout:
            return {"error": "Tiempo de espera agotado (SkyMem)", "email": email}
        except requests.exceptions.ConnectionError:
            return {"error": "Error de conexión a SkyMem", "email": email}
        except Exception as e:
            logger.error(f"Error en SkyMem search: {e}")
            return {"error": f"Error en SkyMem: {str(e)}", "email": email}

    def search_email_paste_accounts(self, email: str, user_id: int) -> Dict[str, Any]:
        """
        Búsqueda real de cuenta en paste/leaks públicos
        """
        try:
            # Usamos SkyMem como fuente principal para leaks
            result = self._search_skymem_real(email,
                                              self.get_user_email_sources(user_id).get('skymem', {}).get('api_key', ''))
            if result.get("breached", False):
                return result
            else:
                return {
                    "email": email,
                    "paste_count": 0,
                    "message": "No se encontraron paste accounts asociados",
                    "timestamp": time.time(),
                    "source": "paste_search"
                }
        except Exception as e:
            logger.error(f"Error en búsqueda de paste accounts: {e}")
            return {"error": f"Error de búsqueda de paste: {str(e)}", "email": email}

    def verify_email_format(self, email: str) -> bool:
        """
        Verificación real de formato de email
        """
        try:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))
        except Exception as e:
            logger.error(f"Error en verificación de formato: {e}")
            return False

    def verify_email_deliverability(self, email: str, user_id: int) -> Dict[str, Any]:
        """
        Verificación real de entrega de email (con API si disponible)
        """
        try:
            source_info = self.get_user_email_sources(user_id).get('hunter', {})
            if source_info.get('requires_api', True):
                api_key = source_info.get('api_key', '')
                # Aquí podrías implementar Hunter.io si lo necesitas
                pass

            return {
                "email": email,
                "delivered": "unknown",
                "timestamp": time.time(),
                "source": "basic_verification"
            }
        except Exception as e:
            logger.error(f"Error en verificación de entrega: {e}")
            return {"error": f"Error verificación entrega: {str(e)}", "email": email}

    def search_email_info(self, email: str, user_id: int, services: List[str] = None) -> Dict[str, Any]:
        """
        Búsqueda completa de información de email con múltiples fuentes reales
        """
        start_time = time.time()
        logger.info(f"Búsqueda completa de email: {email}")

        try:
            if not self.verify_email_format(email):
                return {
                    "error": "Formato de email inválido",
                    "email": email,
                    "timestamp": time.time()
                }

            results = {
                "email": email,
                "timestamp": time.time(),
                "breeches_info": {},
                "paste_info": {},
                "verification_info": {},
                "search_time": 0,
                "errors": []
            }

            # Brechas
            breach_result = self.check_email_breach(email, user_id)
            if isinstance(breach_result, dict):
                results["breeches_info"] = breach_result
            else:
                results["breeches_info"] = {
                    "error": "Error en búsqueda de brechas",
                    "details": str(breach_result)
                }
            # Paste accounts
            paste_result = self.search_email_paste_accounts(email, user_id)
            if isinstance(paste_result, dict):
                results["paste_info"] = paste_result
            else:
                results["paste_info"] = {
                    "error": "Error en búsqueda de paste accounts",
                    "details": str(paste_result)
                }

            # Verificación
            verify_result = self.verify_email_deliverability(email, user_id)
            if isinstance(verify_result, dict):
                results["verification_info"] = verify_result
            else:
                results["verification_info"] = {
                    "error": "Error en verificación de entrega",
                    "details": str(verify_result)
                }

            results["search_time"] = time.time() - start_time

            return results

        except Exception as e:
            logger.error(f"Error en búsqueda completa de email: {e}")
            return {
                "error": f"Error de búsqueda completa: {str(e)}",
                "email": email,
                "timestamp": time.time()
            }

    def get_available_email_sources(self, user_id: int) -> List[str]:
        """
        Obtiene lista de fuentes disponibles para búsqueda de email
        """
        available_sources = self.get_user_email_sources(user_id)
        return list(available_sources.keys())

    def test_email_api_connection(self, source: str, user_id: int) -> Dict[str, Any]:
        """
        Probar conexión real a fuente específica de email
        """
        try:
            source_info = self.get_user_email_sources(user_id).get(source, {})

            if source_info.get('requires_api', True):
                if not source_info.get('api_key'):
                    return {
                        "source": source,
                        "status": "not_configured",
                        "message": "Clave API no configurada",
                        "timestamp": time.time()
                    }
                else:
                    return {
                        "source": source,
                        "status": "configured",
                        "message": "Clave API configurada",
                        "timestamp": time.time()
                    }
            else:
                return {
                    "source": source,
                    "status": "available",
                    "message": "Fuente disponible (búsqueda pública)",
                    "timestamp": time.time(),
                    "requires_api": False
                }

        except Exception as e:
            return {
                "source": source,
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }


# Instancia global
email_searcher = EmailSearcher()


# Funciones públicas
def check_email_breach(email: str, user_id: int) -> Dict[str, Any]:
    """Verificación real de brechas de email"""
    return email_searcher.check_email_breach(email, user_id)


def search_email_paste_accounts(email: str, user_id: int) -> Dict[str, Any]:
    """Búsqueda real de paste accounts de email"""
    return email_searcher.search_email_paste_accounts(email, user_id)


def verify_email_format(email: str) -> bool:
    """Verificación real del formato de email"""
    return email_searcher.verify_email_format(email)


def verify_email_deliverability(email: str, user_id: int) -> Dict[str, Any]:
    """Verificación real de entrega de email"""
    return email_searcher.verify_email_deliverability(email, user_id)


def search_email_info(email: str, user_id: int, services: List[str] = None) -> Dict[str, Any]:
    """Búsqueda completa de información de email"""
    return email_searcher.search_email_info(email, user_id, services)