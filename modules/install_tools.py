# modules/install_tools.py

import subprocess
import sys
import logging
from typing import List

logger = logging.getLogger(__name__)


def install_package(package_name: str, package_spec: str = None) -> bool:
    """
    Intenta instalar un paquete Python de forma segura
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install"]
        if package_spec:
            cmd.append(package_spec)
        else:
            cmd.append(package_name)

        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minutos de timeout
        )

        if process.returncode == 0:
            logger.info(f"✓ {package_name} instalado correctamente")
            return True
        else:
            logger.warning(f"✗ Fallo al instalar {package_name}: {process.stderr}")
            return False

    except Exception as e:
        logger.warning(f"✗ Error al instalar {package_name}: {e}")
        return False


def ensure_maigret_installed():
    """
    Asegura que Maigret esté disponible (instalación automática si no lo está)
    """
    try:
        import maigret
        logger.info("Maigret ya está instalado y disponible")
        return True
    except ImportError:
        logger.info("Maigret no encontrado. Intentando instalar...")
        if install_package("maigret"):
            try:
                import maigret
                logger.info("Maigret instalado y disponible")
                return True
            except ImportError:
                logger.warning("Maigret instalado pero no disponible tras importación")
                return False
        else:
            logger.warning("Imposible instalar Maigret")
            return False


def ensure_sherlock_installed():
    """
    Asegura que Sherlock esté disponible (instalación automática si no lo está)
    """
    try:
        import sherlock
        logger.info("Sherlock ya está instalado y disponible")
        return True
    except ImportError:
        logger.info("Sherlock no encontrado. Intentando instalar...")
        # Para Sherlock, se necesita instalación específica desde GitHub
        if install_package("sherlock-project"):
            try:
                import sherlock
                logger.info("Sherlock instalado y disponible")
                return True
            except ImportError:
                logger.warning("Sherlock instalado pero no disponible tras importación")
                return False
        else:
            logger.warning("Imposible instalar Sherlock")
            return False


def install_socmint_dependencies():
    """
    Instala todas las dependencias necesarias para SOCMINT (Maigret y Sherlock)
    """
    required_packages = [
        "maigret",
        "sherlock-project",  # Nota: nombre específico
    ]

    success_count = 0
    for pkg in required_packages:
        logger.info(f"Verificando instalación de: {pkg}")
        if pkg == "maigret":
            if ensure_maigret_installed():
                success_count += 1
        elif pkg == "sherlock-project":
            if ensure_sherlock_installed():
                success_count += 1

    # Reporte final
    if success_count == len(required_packages):
        logger.info("✓ Todas las herramientas de SOCMINT han sido instaladas correctamente")
        return True
    else:
        logger.warning(f"✗ Solo {success_count} de {len(required_packages)} herramientas instaladas")
        return False


# Funciones de uso público
def install_all_socmint_tools():
    """Función principal para instalar todas las herramientas de SOCMINT"""
    return install_socmint_dependencies()


if __name__ == "__main__":
    install_all_socmint_tools()