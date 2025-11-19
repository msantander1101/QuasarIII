# modules/search/emailint.py
import logging
import requests
import json
from typing import Dict, List, Any
import time

logger = logging.getLogger(__name__)


class EmailSearcher:
    """
    Búsqueda real de información por email usando HIBP API v3
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'QuasarIII-OSINT/1.0',
            'Accept': 'application/json'
        })
        self.hibp_base_url = "https://haveibeenpwned.com/api/v3"

    def check_email_breach(self, email: str, hibp_api_key: str = None) -> Dict[str, Any]:
        """
        Verifica si un email ha sido parte de alguna brecha real usando HIBP API v3
        """
        try:
            # Validar formato de email
            if not self._validate_email_format(email):
                return {"error": "Formato de email inválido", "email": email}

            # Preparar la llamada a HIBP API
            url = f"{self.hibp_base_url}/breachedaccount/{email}"
            params = {"truncateResponse": "false"}
            headers = {}

            # Añadir API key si está disponible
            if hibp_api_key:
                headers["hibp-api-key"] = hibp_api_key

            # Hacer la solicitud HTTP real
            response = self.session.get(url, params=params, headers=headers, timeout=15)

            # Manejo completo de todos los códigos HTTP
            if response.status_code == 200:
                # éxito - hay brechas
                breaches = response.json()
                return {
                    "breached": True,
                    "email": email,
                    "breach_count": len(breaches),
                    "breaches": breaches,
                    "timestamp": time.time()
                }
            elif response.status_code == 404:
                # Email no encontrado en ninguna brecha
                return {
                    "breached": False,
                    "email": email,
                    "message": "Email no encontrado en ninguna brecha pública",
                    "breach_count": 0
                }
            elif response.status_code == 400:
                return {"error": "Solicitud inválida - email inválido"}
            elif response.status_code == 401:
                return {"error": "Autorización fallida - clave API inválida"}
            elif response.status_code == 403:
                return {"error": "Acceso denegado - permisos insuficientes"}
            elif response.status_code == 429:
                return {"error": "Límite de tasa alcanzado"}
            elif response.status_code == 500:
                return {"error": "Error interno del servidor"}
            else:
                return {"error": f"Código HTTP {response.status_code}: {response.reason}"}

        except requests.exceptions.Timeout:
            return {"error": "Tiempo de espera agotado para la solicitud"}
        except requests.exceptions.ConnectionError:
            return {"error": "Error de conexión a la API"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error en solicitud HTTP: {str(e)}"}
        except ValueError as e:  # JSON decode error
            return {"error": "Error al procesar respuesta JSON: " + str(e)}
        except Exception as e:
            logger.error(f"Error no esperado en check_email_breach: {e}")
            return {"error": f"Error interno: {str(e)}"}

    def search_email_paste_accounts(self, email: str, hibp_api_key: str = None) -> Dict[str, Any]:
        """
        Busca cuentas expuestas en paste leaks/reports usando HIBP
        """
        try:
            if not self._validate_email_format(email):
                return {"error": "Formato de email inválido"}

            url = f"{self.hibp_base_url}/pasteaccount/{email}"
            headers = {}

            # Añadir API key si está disponible
            if hibp_api_key:
                headers["hibp-api-key"] = hibp_api_key

            response = self.session.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                pastes = response.json()
                return {
                    "email": email,
                    "paste_count": len(pastes),
                    "pastes": pastes,
                    "timestamp": time.time()
                }
            elif response.status_code == 404:
                return {
                    "email": email,
                    "paste_count": 0,
                    "pastes": [],
                    "message": "No se encontraron paste accounts"
                }
            elif response.status_code == 400:
                return {"error": "Solicitud inválida"}
            elif response.status_code == 403:
                return {"error": "Acceso denegado - permisos insuficientes"}
            elif response.status_code == 429:
                return {"error": "Límite de tasa alcanzado"}
            else:
                return {"error": f"Código HTTP {response.status_code}: {response.reason}"}

        except Exception as e:
            logger.error(f"Error en search_email_paste_accounts: {e}")
            return {"error": f"Error interno: {str(e)}"}

    def search_email_info(self, email: str, hibp_api_key: str = None) -> Dict[str, Any]:
        """
        Búsqueda combinada completa de información de email con HIBP
        """
        try:
            # Primero verificamos brechas
            breach_result = self.check_email_breach(email, hibp_api_key)

            # Luego buscamos paste accounts
            paste_result = self.search_email_paste_accounts(email, hibp_api_key)

            # Combinar resultados
            return {
                "email": email,
                "timestamp": time.time(),
                "breach_info": breach_result,
                "paste_info": paste_result
            }

        except Exception as e:
            logger.error(f"Error en search_email_info: {e}")
            return {"error": f"Error al buscar información del email: {str(e)}"}

    def _validate_email_format(self, email: str) -> bool:
        """Validación de formato de email real"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


# Instancia única
email_searcher = EmailSearcher()


# Funciones públicas directas
def check_email_breach(email: str, hibp_api_key: str = None) -> Dict[str, Any]:
    """Función directa para verificar brechas de email"""
    return email_searcher.check_email_breach(email, hibp_api_key)


def search_email_paste_accounts(email: str, hibp_api_key: str = None) -> Dict[str, Any]:
    """Función directa para buscar paste accounts"""
    return email_searcher.search_email_paste_accounts(email, hibp_api_key)


def search_email_info(email: str, hibp_api_key: str = None) -> Dict[str, Any]:
    """Función directa para búsqueda completa"""
    return email_searcher.search_email_info(email, hibp_api_key)