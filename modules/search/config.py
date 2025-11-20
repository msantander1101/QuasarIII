# modules/search/config.py
"""
Manejador de configuración específico para SOCMINT
"""

import logging
from core.config_manager import config_manager

logger = logging.getLogger(__name__)


class SocmintConfig:
    """
    Gestión de configuraciones de APIs de redes sociales
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.config_key_prefix = "socmint_"

    def set_api_key(self, platform: str, api_key: str) -> bool:
        """Configura clave API para plataforma específica"""
        try:
            config_key = f"{self.config_key_prefix}{platform}"
            success = config_manager.save_config(self.user_id, config_key, api_key)
            if success:
                logger.info(f"API key configurada para plataforma: {platform}")
            return success
        except Exception as e:
            logger.error(f"Error configurando API key: {e}")
            return False

    def get_api_key(self, platform: str) -> str:
        """Obtiene clave API para plataforma específica"""
        try:
            config_key = f"{self.config_key_prefix}{platform}"
            return config_manager.get_config(self.user_id, config_key)
        except Exception as e:
            logger.error(f"Error obteniendo API key: {e}")
            return ""

    def is_platform_enabled(self, platform: str) -> bool:
        """Verifica si plataforma está habilitada (configurada)"""
        return bool(self.get_api_key(platform))

    def get_all_configured_platforms(self) -> dict:
        """Obtiene todas las plataformas con sus claves configuradas"""
        platforms = ['instagram', 'tiktok', 'youtube', 'twitter', 'linkedin', 'facebook', 'reddit']
        configured = {}

        for platform in platforms:
            key = self.get_api_key(platform)
            if key:
                configured[platform] = key

        return configured


# Funciones públicas para facilidad
def configure_social_api(user_id: int, platform: str, api_key: str) -> bool:
    """Función directa para configurar API"""
    config = SocmintConfig(user_id)
    return config.set_api_key(platform, api_key)


def get_social_api_key(user_id: int, platform: str) -> str:
    """Función directa para obtener API key"""
    config = SocmintConfig(user_id)
    return config.get_api_key(platform)