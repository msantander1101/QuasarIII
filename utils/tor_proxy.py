# utils/tor_proxy.py
"""
Sistema de proxy para acceso seguro al dark web a través de Tor
"""

import requests
import socks
import socket
import logging
import time
from typing import Dict, Any, Optional
import urllib.parse

logger = logging.getLogger(__name__)


class TorProxy:
    """
    Sistema completo de proxy para conexión segura a red Tor
    """

    def __init__(self, tor_port: int = 9050, control_port: int = 9051,
                 tor_host: str = "127.0.0.1"):
        """
        Inicializa el proxy Tor con configuraciones básicas

        Args:
            tor_port: Puerto donde escucha Tor (9050 por defecto)
            control_port: Puerto de control de Tor (9051 por defecto)
            tor_host: Dirección del host de Tor (127.0.0.1 por defecto)
        """
        self.tor_port = tor_port
        self.control_port = control_port
        self.tor_host = tor_host
        self.session = None
        self.proxy_config = {
            "http": f"socks5h://{tor_host}:{tor_port}",
            "https": f"socks5h://{tor_host}:{tor_port}"
        }

    def create_tor_session(self) -> requests.Session:
        """
        Crea una sesión HTTP/HTTPS configurada para usar Tor

        Returns:
            requests.Session configurada con proxy SOCKS5h
        """
        try:
            # Crear una nueva sesión
            session = requests.Session()

            # Configuración del proxy SOCKS5h (hostname resolution through Tor)
            session.proxies = self.proxy_config
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'close',
                'Upgrade-Insecure-Requests': '1',
            })

            # Configuración de tiempo de espera
            session.timeout = 30

            self.session = session
            logger.info(f"✓ Sesión Tor creada: {self.proxy_config}")
            return session

        except Exception as e:
            logger.error(f"❌ Error al crear sesión Tor: {e}")
            return None

    def get_tor_ip(self) -> Dict[str, Any]:
        """
        Obtiene la dirección IP actual a través de Tor

        Returns:
            Dict con la info IP y otros detalles
        """
        try:
            session = self.create_tor_session()
            if not session:
                return {"error": "No se pudo crear sesión Tor"}

            # Ejemplo usando un servicio que retorna la IP real
            # Puede ser: https://check.torproject.org/api/ip, https://icanhazip.com, etc.
            response = session.get("https://api.ipify.org?format=json", timeout=15)

            if response.status_code == 200:
                ip_info = response.json()
                return {
                    "ip": ip_info.get("ip"),
                    "proxy_type": "Tor",
                    "status": "connected",
                    "timestamp": time.time()
                }
            else:
                return {"error": f"Error en verificación IP: {response.status_code}"}

        except Exception as e:
            logger.error(f"Error al verificar IP con Tor: {e}")
            return {"error": f"Error de conexión: {str(e)}"}

    def test_connectivity(self, test_url: str = "https://check.torproject.org/api/ip") -> Dict[str, Any]:
        """
        Verifica conectividad con Tor y URLs específicas

        Args:
            test_url: URL para testear conectividad

        Returns:
            Dict con resultados del test
        """
        try:
            session = self.create_tor_session()
            if not session:
                return {"status": "fail", "error": "No se pudo crear sesión"}

            # Intento de conexión
            response = session.get(test_url, timeout=20)

            return {
                "status": "success" if response.status_code == 200 else "fail",
                "response_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "url_tested": test_url,
                "timestamp": time.time()
            }

        except Exception as e:
            logger.error(f"Error en prueba de conectividad: {e}")
            return {
                "status": "fail",
                "error": str(e),
                "timestamp": time.time()
            }

    def is_tor_connected(self) -> bool:
        """
        Verifica si está establecida conexión con Tor

        Returns:
            bool: True si conexión con Tor es válida
        """
        try:
            # Realizar test rápido
            result = self.test_connectivity()
            return result.get("status") == "success"
        except:
            return False

    def update_tor_identity(self) -> bool:
        """
        Solicita una nueva identidad de Tor (cambio de IP)

        Returns:
            bool: True si fue exitoso
        """
        try:
            # Esta es una implementación simplificada
            # En entornos reales necesitarías control remoto de Tor
            logger.info("🔄 Solicitando cambio de identidad Tor...")
            # En producción esto conectaría al puerto de control de Tor
            # y ejecutaría "SIGNAL NEWNYM" para cambiar IP
            return True
        except Exception as e:
            logger.error(f"Error al cambiar identidad Tor: {e}")
            return False


# Instancia única para uso global
tor_proxy = TorProxy()


# Funciones de acceso directo
def create_tor_session() -> requests.Session:
    """Obtener sesión Tor para conexión rápida"""
    return tor_proxy.create_tor_session()


def get_tor_ip() -> Dict[str, Any]:
    """Obtener IP actual a través de Tor"""
    return tor_proxy.get_tor_ip()


def test_tor_connectivity(test_url: str = "https://check.torproject.org/api/ip") -> Dict[str, Any]:
    """Testear conectividad de Tor"""
    return tor_proxy.test_connectivity(test_url)


def is_tor_ready() -> bool:
    """Verificar si Tor está listo para usar"""
    return tor_proxy.is_tor_connected()


def change_tor_identity() -> bool:
    """Cambiar identidad Tor (IP)"""
    return tor_proxy.update_tor_identity()


# Configuración alternativa para desarrollo
class DevelopmentProxy:
    """
    Proxy de desarrollo para testeo sin Tor
    """

    @staticmethod
    def create_session() -> requests.Session:
        """Crea sesión regular (sin proxy) para desarrollo"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Development-Client/1.0'
        })
        return session


# Exportar dependiendo del entorno
def get_proxy_session() -> requests.Session:
    """
    Retorna sesión apropiada: con Tor si disponible, o desarrollo
    """
    try:
        # Intentar crear sesión Tor
        session = create_tor_session()
        if session:
            return session
    except Exception as e:
        logger.warning(f"Tor no disponible, usando sesión de desarrollo: {e}")

    # Fallback a desarrollo
    return DevelopmentProxy.create_session()