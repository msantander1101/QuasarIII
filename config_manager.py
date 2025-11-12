from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()


class ConfigManager:
    def __init__(self):
        master_key = os.getenv("MASTER_KEY")
        if not master_key:
            raise ValueError("MASTER_KEY no encontrada en .env")
        self.cipher = Fernet(master_key.encode())

    def encrypt_api_key(self, plain_key):
        """Cifra una clave API"""
        if plain_key:
            return self.cipher.encrypt(plain_key.encode()).decode()
        return None

    def decrypt_api_key(self, encrypted_key):
        """Descifra una clave API"""
        if encrypted_key:
            try:
                return self.cipher.decrypt(encrypted_key.encode()).decode()
            except Exception:
                return None
        return None

    def get_decrypted_key(self, db_manager, user_id, service_name):
        """Obtiene y descifra una clave API"""
        encrypted = db_manager.get_api_key(user_id, service_name)
        if encrypted:
            return self.decrypt_api_key(encrypted)
        return None