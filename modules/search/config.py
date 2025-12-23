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
    Compatibilidad doble:
      - nuevo: "<platform>_api_key"  (instagram_api_key, twitter_api_key, ...)
      - legacy: "socmint_<platform>"
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.legacy_prefix = "socmint_"

    def _normalize_platform(self, platform: str) -> str:
        return (platform or "").strip().lower()

    def _new_key(self, platform: str) -> str:
        # formato recomendado/alineado con required_configs
        return f"{platform}_api_key"

    def _legacy_key(self, platform: str) -> str:
        return f"{self.legacy_prefix}{platform}"

    def set_api_key(self, platform: str, api_key: str, also_save_legacy: bool = False) -> bool:
        """Configura clave API para plataforma específica."""
        try:
            platform = self._normalize_platform(platform)
            if not platform or not api_key:
                return False

            # Guardar en el formato estándar
            primary_key = self._new_key(platform)
            ok = config_manager.save_config(self.user_id, primary_key, api_key)

            # Opcional: mantener compat con el formato anterior
            if ok and also_save_legacy:
                legacy_key = self._legacy_key(platform)
                config_manager.save_config(self.user_id, legacy_key, api_key)

            if ok:
                logger.info(f"API key configurada para plataforma: {platform}")

            return ok

        except Exception as e:
            logger.error(f"Error configurando API key: {e}")
            return False

    def get_api_key(self, platform: str) -> str:
        """Obtiene clave API para plataforma específica (nuevo -> legacy)."""
        try:
            platform = self._normalize_platform(platform)
            if not platform:
                return ""

            # 1) formato estándar
            v = config_manager.get_config(self.user_id, self._new_key(platform))
            if v:
                return v

            # 2) formato legacy
            return config_manager.get_config(self.user_id, self._legacy_key(platform))

        except Exception as e:
            logger.error(f"Error obteniendo API key: {e}")
            return ""

    def is_platform_enabled(self, platform: str) -> bool:
        """Verifica si plataforma está habilitada (configurada)."""
        return bool(self.get_api_key(platform))

    def get_all_configured_platforms(self) -> dict:
        """Obtiene todas las plataformas con sus claves configuradas."""
        platforms = ['instagram', 'tiktok', 'youtube', 'twitter', 'linkedin', 'facebook', 'reddit']
        configured = {}

        for platform in platforms:
            key = self.get_api_key(platform)
            if key:
                configured[platform] = key

        return configured


# Funciones públicas para facilidad
def configure_social_api(user_id: int, platform: str, api_key: str, also_save_legacy: bool = False) -> bool:
    """Función directa para configurar API."""
    config = SocmintConfig(user_id)
    return config.set_api_key(platform, api_key, also_save_legacy=also_save_legacy)


def get_social_api_key(user_id: int, platform: str) -> str:
    """Función directa para obtener API key."""
    config = SocmintConfig(user_id)
    return config.get_api_key(platform)
