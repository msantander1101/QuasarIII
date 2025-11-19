import bcrypt # Importamos bcrypt
from typing import Optional
from core.db_manager import get_user_by_username, create_db
import logging
import sqlite3
from uuid import uuid4
import time

# Logger global
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear DB si no existe al iniciar el módulo.
create_db()

# --- Helper Functions ---
def hash_password(password: str) -> bytes:
    """
    Hasha una contraseña con bcrypt (devuelve bytes).
    """
    # Generar un salt y hashear la contraseña
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed # Devuelve bytes

def verify_password(password: str, stored_hashed_pw: bytes) -> bool:
    """
    Verifica si una contraseña coincide con un hash almacenado (usando bytes).
    """
    try:
        # Verificar la contraseña contra el hash
        return bcrypt.checkpw(password.encode('utf-8'), stored_hashed_pw)
    except Exception as e:
        logger.error(f"Error verificando clave: {e}")
        return False

# --- Funciones principales de Autenticación ---
def register_user(username: str, email: str, password: str, db_path: str = 'data/users.db') -> bool:
    """
    Registra un nuevo usuario.
    Retorna True si el registro fue exitoso, False si el nombre de usuario o correo ya existe.
    """
    try:
        # Verificar que el nombre de usuario no exista en la BD
        if get_user_by_username(username, db_path): # Llamamos a una funcion utilitaria
            logger.warning(f"Usuario {username} ya existe.")
            return False # Usuario ya existe

        password_hash = hash_password(password) # Usamos bcrypt para seguridad
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  (username, email, password_hash)) # Almacenamos bytes directamente

        conn.commit()
        conn.close()
        logger.info(f"Usuario {username} registrado exitosamente.")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Error de integridad al registrar usuario '{username}': {e}")
        return False # Errores tipo UNIQUE constraint failed
    except Exception as e:
        logger.error(f"Error inesperado al registrar usuario '{username}': {e}")
        return False

def authenticate_user(username: str, password: str, db_path: str = 'data/users.db') -> Optional[int]:
    """
    Autentica a un usuario dado su nombre de usuario y contraseña.
    Retorna el id del usuario si la autenticación es exitosa, None si falla.
    """
    user_tuple = get_user_by_username(username, db_path)
    if not user_tuple:
        logger.warning(f"Ingreso fallido: Usuario '{username}' no encontrado.")
        return None

    user_id, stored_user, stored_email, stored_hash_bytes = user_tuple
    # Verificar contraseña usando bytes
    if verify_password(password, stored_hash_bytes):
        logger.info(f"Autenticación correcta para usuario {username} (id: {user_id}).")
        return user_id # Correcto
    else:
        logger.warning(f"Ingreso fallido: Contraseña incorrecta para '{username}'.")
        return None

# --- Funciones auxiliares (opcional) ---
# Si necesitarás comparar contraseñas en otro lugar:
def is_valid_password(password: str, stored_hash_bytes: bytes) -> bool:
    """Wrapper de verify_password para compatibilidad o uso externo."""
    return verify_password(password, stored_hash_bytes)