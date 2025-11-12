import bcrypt
import streamlit as st
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("MASTER_KEY", "clave_jwt_secreta")


class AuthManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def hash_password(self, password):
        """Hashear contraseña con bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, password, hashed):
        """Verificar contraseña"""
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def create_jwt_token(self, username, user_id):
        """Crear token JWT"""
        payload = {
            "username": username,
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    def verify_jwt_token(self, token):
        """Verificar token JWT"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def register(self, username, email, password):
        """Registrar nuevo usuario"""
        if self.db.get_user(username):
            return False, "Usuario ya existe"

        password_hash = self.hash_password(password)
        user_id = self.db.create_user(username, email, password_hash)

        if user_id:
            return True, "Usuario creado exitosamente"
        return False, "Error al crear usuario"

    def login(self, username, password):
        """Iniciar sesión"""
        user = self.db.get_user(username)
        if not user:
            return False, None, "Usuario no encontrado"

        if self.verify_password(password, user[3]):  # password_hash está en índice 3
            token = self.create_jwt_token(username, user[0])  # user[0] = id
            return True, token, "Login exitoso"

        return False, None, "Contraseña incorrecta"

    def logout(self):
        """Cerrar sesión"""
        if 'token' in st.session_state:
            del st.session_state.token
        if 'user' in st.session_state:
            del st.session_state.user

    def is_authenticated(self):
        """Verificar si el usuario está autenticado"""
        if 'token' not in st.session_state:
            return False

        payload = self.verify_jwt_token(st.session_state.token)
        if payload:
            st.session_state.user = {
                "id": payload["user_id"],
                "username": payload["username"]
            }
            return True

        self.logout()
        return False