# core/auth_manager.py
"""
Auth Manager — control básico de usuarios y roles (SQLite)

Fase 1:
- Sin registro público desde la UI principal
- Solo login con usuarios definidos por el administrador
- Roles básicos: admin / analyst
- Persistencia en tabla 'users' de data/users.db
"""

from __future__ import annotations

import os
import sqlite3
import logging
from dataclasses import dataclass
from typing import Optional, List

import bcrypt

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("QUASAR_DB_PATH", "data/users.db")


@dataclass
class User:
    id: int
    username: str
    email: str
    role: str = "analyst"
    is_active: bool = True

    @property
    def is_admin(self) -> bool:
        return (self.role or "").lower() == "admin"


class AuthManager:
    """
    AuthManager basado en SQLite.

    Tabla users esperada:
      - id INTEGER PRIMARY KEY AUTOINCREMENT
      - username TEXT UNIQUE NOT NULL
      - email TEXT UNIQUE NOT NULL
      - password_hash BLOB NOT NULL
      - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      - role TEXT DEFAULT 'analyst'
      - is_active INTEGER DEFAULT 1
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    # ---------------- Esquema / migración ligera ----------------

    def _ensure_schema(self) -> None:
        """
        Asegura que la tabla 'users' exista y tenga columnas role e is_active.
        También crea el directorio del DB si no existe.
        """
        try:
            # ✅ Asegura que la carpeta del fichero exista (evita "unable to open database file")
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Crear tabla base si no existe (por si create_db aún no se ha ejecutado)
            c.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )

            # ✅ Migración robusta: inspecciona columnas y altera solo si faltan
            c.execute("PRAGMA table_info(users)")
            cols = {row[1] for row in c.fetchall()}

            if "role" not in cols:
                c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'analyst'")

            if "is_active" not in cols:
                c.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Error asegurando esquema de la tabla users: %s", e)

    # ---------------- Helpers de password ----------------

    @staticmethod
    def hash_password(password: str) -> bytes:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    @staticmethod
    def verify_password(password: str, password_hash: bytes) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash)
        except Exception:
            return False

    # ---------------- Internos ----------------

    def _row_to_user(self, row) -> User:
        """
        row: (id, username, email, password_hash, created_at, role, is_active)
        """
        return User(
            id=row[0],
            username=row[1],
            email=row[2],
            role=row[5] if len(row) > 5 and row[5] is not None else "analyst",
            is_active=bool(row[6]) if len(row) > 6 else True,
        )

    # ---------------- API pública ----------------

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Devuelve User si las credenciales son válidas y el usuario está activo,
        o None en caso contrario.
        """
        uname = (username or "").strip().lower()
        if not uname or not password:
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT id, username, email, password_hash, created_at, "
                "COALESCE(role, 'analyst') as role, "
                "COALESCE(is_active, 1) as is_active "
                "FROM users WHERE LOWER(username)=?",
                (uname,),
            )
            row = c.fetchone()
            conn.close()
        except Exception as e:
            logger.error("Error autenticando usuario %s: %s", uname, e)
            return None

        if not row:
            logger.warning("Auth failed: user not found (%s)", uname)
            return None

        pw_hash = row[3]
        if not self.verify_password(password, pw_hash):
            logger.warning("Auth failed: bad password (%s)", uname)
            return None

        user = self._row_to_user(row)
        if not user.is_active:
            logger.warning("Auth failed: user inactive (%s)", uname)
            return None

        return user

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "analyst",
        is_active: bool = True,
        email: Optional[str] = None,
    ) -> User:
        """
        Crear usuario nuevo (se usa desde CLI y desde el panel admin).
        Persiste en tabla 'users'.
        """
        uname = (username or "").strip().lower()
        if not uname:
            raise ValueError("username vacío")

        email_val = (email or f"{uname}@local").strip()
        pw_hash = self.hash_password(password)

        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, email, password_hash, role, is_active) "
                "VALUES (?, ?, ?, ?, ?)",
                (uname, email_val, pw_hash, role, 1 if is_active else 0),
            )
            user_id = c.lastrowid
            conn.commit()
            conn.close()
            logger.info(
                "User created: %s (id=%s, role=%s, email=%s)",
                uname, user_id, role, email_val
            )
        except sqlite3.IntegrityError as e:
            logger.error("User/email already exists: %s", e)
            raise ValueError(f"El usuario o email ya existen: {uname}") from e
        except Exception as e:
            logger.error("Error creando usuario %s: %s", uname, e)
            raise

        return User(
            id=user_id,
            username=uname,
            email=email_val,
            role=role,
            is_active=is_active,
        )

    def list_users(self) -> List[User]:
        """
        Devuelve todos los usuarios registrados.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT id, username, email, password_hash, created_at, "
                "COALESCE(role, 'analyst') as role, "
                "COALESCE(is_active, 1) as is_active "
                "FROM users ORDER BY created_at ASC"
            )
            rows = c.fetchall()
            conn.close()
        except Exception as e:
            logger.error("Error listando usuarios: %s", e)
            return []

        return [self._row_to_user(r) for r in rows]

    # ---------------- Gestión por administrador ----------------

    def set_user_active(self, username: str, is_active: bool) -> None:
        """
        Activa / desactiva un usuario existente.
        """
        uname = (username or "").strip().lower()
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "UPDATE users SET is_active=? WHERE LOWER(username)=?",
                (1 if is_active else 0, uname),
            )
            conn.commit()
            conn.close()
            logger.info("User %s set is_active=%s", uname, is_active)
        except Exception as e:
            logger.error("Error cambiando estado de usuario %s: %s", uname, e)
            raise

    def set_user_role(self, username: str, role: str) -> None:
        """
        Cambia el rol de un usuario (p.ej. analyst → admin).
        """
        uname = (username or "").strip().lower()
        new_role = (role or "analyst").strip()
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "UPDATE users SET role=? WHERE LOWER(username)=?",
                (new_role, uname),
            )
            conn.commit()
            conn.close()
            logger.info("User %s role changed to %s", uname, new_role)
        except Exception as e:
            logger.error("Error cambiando rol de usuario %s: %s", uname, e)
            raise

    def user_exists(self, username: str) -> bool:
        uname = (username or "").strip().lower()
        if not uname:
            return False
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT 1 FROM users WHERE LOWER(username)=? LIMIT 1", (uname,))
            ok = c.fetchone() is not None
            conn.close()
            return ok
        except Exception as e:
            logger.error("Error comprobando existencia de usuario %s: %s", uname, e)
            return False

    def bootstrap_admin(self, username: str, password: str, email: str) -> None:
        """
        Crea un admin inicial si no existe. Idempotente.
        """
        uname = (username or "").strip().lower()
        if not uname or not password or not email:
            raise ValueError("bootstrap_admin requiere username/password/email")

        if self.user_exists(uname):
            return

        self.create_user(
            username=uname,
            password=password,
            email=email,
            role="admin",
            is_active=True,
        )
        logger.warning("BOOTSTRAP ADMIN creado: %s", uname)


# Instancia global
auth_manager = AuthManager()
