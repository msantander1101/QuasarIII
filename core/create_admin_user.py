# core/create_admin_user.py

from getpass import getpass

from core.auth_manager import auth_manager


def main():
    print("== Crear usuario administrador para QuasarIII (SQLite) ==")
    username = input("Usuario (por ejemplo 'miguel' o 'admin'): ").strip() or "admin"
    email = input("Email (por ejemplo 'tuusuario@tuempresa.com'): ").strip() or f"{username}@local"

    password = getpass("Contraseña: ")
    password2 = getpass("Repite la contraseña: ")

    if password != password2:
        print("Las contraseñas no coinciden.")
        return

    try:
        user = auth_manager.create_user(
            username=username,
            password=password,
            role="admin",
            is_active=True,
            email=email,
        )
        print(f"Usuario creado: {user.username} (id={user.id}, role={user.role}, email={user.email})")
    except Exception as e:
        print(f"Error creando usuario administrador: {e}")


if __name__ == "__main__":
    main()
