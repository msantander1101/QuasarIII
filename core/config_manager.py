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
        self.required_configs = [
            "hibp",  # Para verificar breach de emails
            "openai_api_key", # Para uso de IA
            "google_api_key", # Para búsqueda web avanzada
        ]
        # Puedes añadir más configuraciones requeridas aquí

    def save_config(self, user_id: int, config_key: str, config_value: str, encrypt_if_sensitive: bool = False) -> bool:
        """
        Guarda una clave de configuración.
        :param user_id: ID del usuario
        :param config_key: Clave de configuración (ej: 'hibp_api_key')
        :param config_value: Valor de la clave (ej: '12345abcde_secret_key')
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
        :return: El valor (string) o None si no existe.
        """
        return get_user_config(user_id, config_key)

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
        return self.required_configs.copy()  # Devuelve una copia para evitar modificaciones externas

# Exporta una instancia única por conveniencia (como en core/auth_manager.py)
config_manager = ConfigManager()