# core/create_admin_user.py

from getpass import getpass
from core.auth_manager import auth_manager

def main():
    print("== Crear usuario administrador para QuasarIII ==")
    username = input("Usuario (por ejemplo 'miguel' o 'admin'): ").strip() or "admin"
    password = getpass("Contraseña: ")
    password2 = getpass("Repite la contraseña: ")

    if password != password2:
        print("Las contraseñas no coinciden.")
        return

    user = auth_manager.create_user(username=username, password=password, role="admin", is_active=True)
    print(f"Usuario creado: {user.username} (role={user.role})")

if __name__ == "__main__":
    main()
