# utils/proxy_status_manager.py
"""
Gestor de estado del proxy para alertas de conexión y seguridad
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProxyStatus:
    """Clase para manejar el estado de proxy"""

    def __init__(self):
        self.last_check = None
        self.connection_status = "unknown"  # unknown, connected, disconnected
        self.last_error = None
        self.consecutive_failures = 0
        self.is_secure = False

    def update_status(self, status: str, error: str = None, secure: bool = False):
        """Actualizar estado actual"""
        self.last_check = datetime.now()
        self.connection_status = status
        self.last_error = error
        self.is_secure = secure

        if status == "disconnected":
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        logger.info(f"Proxy status updated: {status}, secure: {secure}")

    def get_status_info(self) -> Dict[str, Any]:
        """Obtener información completa del estado"""
        return {
            "connection_status": self.connection_status,
            "is_secure": self.is_secure,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "uptime": self._calculate_uptime()
        }

    def _calculate_uptime(self) -> str:
        """Calcular tiempo de actividad"""
        if self.last_check:
            diff = datetime.now() - self.last_check
            seconds = int(diff.total_seconds())
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m {seconds}s"
        return "0h 0m 0s"


# Estado global del proxy
proxy_status_manager = ProxyStatus()


def get_proxy_status_info() -> Dict[str, Any]:
    """Obtener información del estado del proxy"""
    return proxy_status_manager.get_status_info()


def set_proxy_status(status: str, error: str = None, secure: bool = False):
    """Establecer el estado del proxy"""
    proxy_status_manager.update_status(status, error, secure)


# Función para revisar estado
def check_proxy_health() -> bool:
    """Chequear salud del proxy"""
    try:
        from utils.tor_proxy import test_tor_connectivity
        result = test_tor_connectivity()
        status = "connected" if result.get("status") == "success" else "disconnected"
        set_proxy_status(status, result.get("error"), status == "connected")
        return status == "connected"
    except Exception as e:
        set_proxy_status("disconnected", str(e))
        return False