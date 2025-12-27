# core/api_tokens.py
"""
API Tokens Manager — tokens por usuario para la API /api/search

- Un token por usuario (clave: "api_access_token" en config_manager)
- Generación segura con secrets.token_hex
- Verificación basada en user_id + token
"""

from __future__ import annotations

import secrets
import logging
from typing import Optional

from core.config_manager import config_manager

logger = logging.getLogger(__name__)

API_TOKEN_KEY = "api_access_token"


def generate_api_token(user_id: int) -> str:
    """
    Genera un nuevo token para el usuario (revoca el anterior si existía).
    Lo guarda usando config_manager.save_config.
    """
    token = secrets.token_hex(32)  # 64 chars hex
    ok = config_manager.save_config(user_id, API_TOKEN_KEY, token)
    if not ok:
        logger.error("Error guardando API token para user_id=%s", user_id)
    else:
        logger.info("API token regenerado para user_id=%s", user_id)
    return token


def get_api_token(user_id: int) -> Optional[str]:
    """
    Devuelve el token actual del usuario (o None si no hay).
    """
    return config_manager.get_config(user_id, API_TOKEN_KEY)


def revoke_api_token(user_id: int) -> None:
    """
    Revoca el token actual (lo elimina de la config).
    """
    deleted = config_manager.delete_config(user_id, API_TOKEN_KEY)
    if deleted:
        logger.info("API token revocado para user_id=%s", user_id)
    else:
        logger.warning("Intento de revocar token inexistente para user_id=%s", user_id)


def verify_api_token(user_id: int, token: str) -> bool:
    """
    Verifica que el token proporcionado coincide con el almacenado.
    """
    if not token:
        return False
    stored = get_api_token(user_id)
    if not stored:
        return False
    # comparación segura para evitar timing attacks
    return secrets.compare_digest(stored, token)
