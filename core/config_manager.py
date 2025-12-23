# core/config_manager.py
import logging
from core.db_manager import save_user_config, get_user_config, delete_user_config, list_user_configs

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Gestiona la configuración personalizada del usuario como claves API.
    Puede expandirse para cifrar información sensible, validar formatos, etc.
    """

    def __init__(self):
        # ✅ Lista de claves que tu app considera "requeridas".
        # Nota: puedes marcar como requeridas solo las que realmente sean obligatorias.
        self.required_configs = [
            "hibp",  # Para verificar breach de emails
            "openai_api_key",  # Para uso de IA

            # Web / Dorks
            "google_api_key",               # Google Custom Search API Key
            "google_custom_search_cx",      # ✅ NUEVO: CX para Google CSE
            "serpapi_api_key",              # ✅ NUEVO: SerpAPI Key (opcional pero recomendable)

            # Social
            "instagram_api_key",
            "tiktok_api_key",
            "youtube_api_key",
            "twitter_api_key",
            "linkedin_api_key",
            "facebook_api_key",
            "reddit_api_key",
        ]

    def save_config(
        self,
        user_id: int,
        config_key: str,
        config_value: str,
        encrypt_if_sensitive: bool = False
    ) -> bool:
        """
        Guarda una clave de configuración.
        :param user_id: ID del usuario
        :param config_key: Clave (ej: 'google_api_key')
        :param config_value: Valor
        :param encrypt_if_sensitive: Si es verdadero, codifica antes de guardar (simulación)
        :return: Booleano indicando si tuvo éxito.
        """
        try:
            if not config_key or not config_value:
                logger.warning("Guardando configuración sin valores.")
                return False
            saved = save_user_config(user_id, config_key, config_value, encrypt_if_sensitive)
            return saved
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            return False

    def get_config(self, user_id: int, config_key: str) -> str:
        """
        Obtiene valor de configuración almacenada.
        :param user_id: ID del usuario
        :param config_key: Clave a buscar
        :return: El valor (string) o "" si no existe.
        """
        value = get_user_config(user_id, config_key)
        return value or ""

    def delete_config(self, user_id: int, config_key: str) -> bool:
        """
        Elimina configuración del usuario.
        :param user_id: ID del usuario
        :param config_key: Clave a eliminar
        :return: Booleano indicando éxito.
        """
        return delete_user_config(user_id, config_key)

    def list_configs(self, user_id: int) -> list:
        """
        Lista todas las configuraciones configuradas actualmente por el usuario.
        :param user_id: ID del usuario
        :return: Lista de diccionarios con información de configuración.
        """
        return list_user_configs(user_id)

    def are_keys_provided(self, user_id: int) -> dict:
        """
        Verifica si todas las claves requeridas están configuradas para el usuario.
        Returna un diccionario con la información por clave.
        """
        provided = {}
        for required_key in self.required_configs:
            value = self.get_config(user_id, required_key)
            provided[required_key] = bool(value)
        return provided

    def get_required_keys_list(self) -> list:
        """
        Devuelve la lista de claves necesarias (requeridas por la app).
        """
        return self.required_configs.copy()

    # ---------------------------------------------------------------------
    # ✅ Helpers específicos (calidad de vida / evita strings mágicos)
    # ---------------------------------------------------------------------

    def get_google_cse_key(self, user_id: int) -> str:
        """Devuelve la API Key de Google CSE (google_api_key)."""
        return self.get_config(user_id, "google_api_key")

    def get_google_cse_cx(self, user_id: int) -> str:
        """Devuelve el CX de Google Custom Search."""
        return self.get_config(user_id, "google_custom_search_cx")

    def get_serpapi_key(self, user_id: int) -> str:
        """Devuelve la key de SerpAPI."""
        return self.get_config(user_id, "serpapi_api_key")

    def get_social_api_key(self, user_id: int, platform: str) -> str:
        """
        Obtiene clave API para SOCMINT de plataforma específica.

        Compatibilidad:
        - primero intenta "<platform>_api_key" (ej: instagram_api_key)
        - luego intenta "socmint_<platform>" (formato anterior/alternativo)
        """
        platform = (platform or "").strip().lower()
        if not platform:
            return ""

        # Preferencia: formato actual en required_configs
        v = self.get_config(user_id, f"{platform}_api_key")
        if v:
            return v

        # Compatibilidad: formato alternativo
        return self.get_config(user_id, f"socmint_{platform}")


# Exporta una instancia única por conveniencia
config_manager = ConfigManager()
