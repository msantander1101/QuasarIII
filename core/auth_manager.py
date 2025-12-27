# core/auth_manager.py
"""
Auth Manager — control básico de usuarios y roles

Fase 1:
- Sin registro público desde la UI principal
- Solo login con usuarios definidos por el administrador
- Soporta roles básicos: admin / analyst
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Dict, Optional, List

import bcrypt
import yaml

logger = logging.getLogger(__name__)

USERS_FILE = os.getenv("QUASAR_USERS_FILE", "quasar_users.yaml")


@dataclass
class User:
    username: str
    password_hash: str
    role: str = "analyst"
    is_active: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role.lower() == "admin"


class AuthManager:
    def __init__(self, users_file: str = USERS_FILE):
        self.users_file = users_file
        self._users: Dict[str, User] = {}
        self._loaded = False

    # ---------------- Carga / guardado ----------------

    def _load(self) -> None:
        if self._loaded:
            return

        if not os.path.exists(self.users_file):
            logger.warning("Users file not found: %s", self.users_file)
            self._users = {}
            self._loaded = True
            return

        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error("Error loading users file: %s", e)
            self._users = {}
            self._loaded = True
            return

        users: Dict[str, User] = {}
        for entry in data.get("users", []):
            try:
                u = User(
                    username=str(entry.get("username")).strip(),
                    password_hash=str(entry.get("password_hash")).strip(),
                    role=(entry.get("role") or "analyst").strip(),
                    is_active=bool(entry.get("is_active", True)),
                )
                if u.username:
                    users[u.username.lower()] = u
            except Exception as e:
                logger.error("Invalid user entry in users file: %s", e)

        self._users = users
        self._loaded = True
        logger.info("AuthManager loaded %s users", len(self._users))

    def _save(self) -> None:
        data = {
            "users": [
                {
                    "username": u.username,
                    "password_hash": u.password_hash,
                    "role": u.role,
                    "is_active": u.is_active,
                }
                for u in self._users.values()
            ]
        }
        os.makedirs(os.path.dirname(self.users_file) or ".", exist_ok=True)
        with open(self.users_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)
        logger.info("AuthManager saved users file: %s", self.users_file)

    # ---------------- Password helpers ----------------

    @staticmethod
    def hash_password(password: str) -> str:
        pw = password.encode("utf-8")
        hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            pw = password.encode("utf-8")
            ph = password_hash.encode("utf-8")
            return bcrypt.checkpw(pw, ph)
        except Exception:
            return False

    # ---------------- API pública ----------------

    def get_user(self, username: str) -> Optional[User]:
        self._load()
        return self._users.get((username or "").strip().lower())

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Devuelve el User si las credenciales son válidas y el usuario está activo,
        o None en caso contrario.
        """
        self._load()
        uname = (username or "").strip().lower()
        user = self._users.get(uname)
        if not user:
            logger.warning("Auth failed: user not found (%s)", uname)
            return None
        if not user.is_active:
            logger.warning("Auth failed: user inactive (%s)", uname)
            return None
        if not self.verify_password(password, user.password_hash):
            logger.warning("Auth failed: bad password (%s)", uname)
            return None
        return user

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "analyst",
        is_active: bool = True,
    ) -> User:
        """
        Crear usuario nuevo (se usa desde CLI y desde el panel admin).
        """
        self._load()
        uname = (username or "").strip().lower()
        if not uname:
            raise ValueError("username vacío")
        if uname in self._users:
            raise ValueError(f"El usuario '{uname}' ya existe")

        pw_hash = self.hash_password(password)
        user = User(username=uname, password_hash=pw_hash, role=role, is_active=is_active)
        self._users[uname] = user
        self._save()
        logger.info("User created: %s (role=%s)", uname, role)
        return user

    def list_users(self) -> List[User]:
        self._load()
        return list(self._users.values())

    # ---------------- Gestión por administrador ----------------

    def set_user_active(self, username: str, is_active: bool) -> None:
        """Activa / desactiva un usuario existente."""
        self._load()
        uname = (username or "").strip().lower()
        user = self._users.get(uname)
        if not user:
            raise ValueError(f"Usuario '{uname}' no encontrado")

        user.is_active = bool(is_active)
        self._users[uname] = user
        self._save()
        logger.info("User %s set is_active=%s", uname, is_active)

    def set_user_role(self, username: str, role: str) -> None:
        """Cambia el rol de un usuario (p.ej. analyst → admin)."""
        self._load()
        uname = (username or "").strip().lower()
        user = self._users.get(uname)
        if not user:
            raise ValueError(f"Usuario '{uname}' no encontrado")

        user.role = (role or "analyst").strip()
        self._users[uname] = user
        self._save()
        logger.info("User %s role changed to %s", uname, role)


# Instancia global
auth_manager = AuthManager()
