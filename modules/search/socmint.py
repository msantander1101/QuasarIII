# modules/search/socmint.py

import logging
import requests
import time
from typing import Dict, List, Any
import subprocess
import tempfile
import json
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


# Función para verificar si una herramienta está instalada
def is_tool_available(tool_name: str) -> bool:
    """
    Verifica si una herramienta está disponible en el sistema
    """
    # Primero verificamos si están instaladas como paquetes Python
    try:
        if tool_name == "maigret":
            # Intentamos importar directamente el módulo
            import maigret
            return True
        elif tool_name == "sherlock":
            # Intentamos importar el módulo de sherlock (si está correctamente instalado)
            import sherlock
            return True
        return False
    except ImportError:
        # Si no están instaladas como paquetes, intentamos ver si existen en PATH con comandos básicos
        try:
            if tool_name == "maigret":
                subprocess.run(["maigret", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=True, timeout=5)
                return True
            elif tool_name == "sherlock":
                subprocess.run(["sherlock", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=True, timeout=5)
                return True
            return False
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False


# Importar modulo de instalación si está disponible
def install_missing_tools():
    """
    Intenta instalar herramientas faltantes
    """
    try:
        from modules.install_tools import install_all_socmint_tools
        logger.info("Instalando herramientas SOCMINT faltantes...")

        # Instalamos las herramientas necesarias si son posibles
        if not install_all_socmint_tools():
            logger.warning("No se pudieron instalar todas las herramientas SOCMINT")

    except ImportError:
        logger.warning("Módulo de instalación no encontrado, ignorando instalación automática")


# Función para detectar si es un ejecutable en PATH (verificación alternativa)
def check_tool_path(tool_name: str) -> bool:
    """
    Comprueba si la herramienta está en PATH mediante comando básico
    """
    try:
        if tool_name == "maigret":
            # Usamos --help para verificar si existe
            subprocess.run(["maigret", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, timeout=10)
            return True
        elif tool_name == "sherlock":
            # Ejemplo alternativo para sheriff (podría ser diferente)
            subprocess.run(["sherlock", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, timeout=10)
            return True
        return False
    except:
        return False


# Función global para verificar disponibilidad de herramientas
def get_tool_status() -> Dict[str, bool]:
    """
    Obtiene el estado actual de herramientas externas
    """
    return {
        "maigret": is_tool_available("maigret"),
        "sherlock": is_tool_available("sherlock")
    }


class SocmintSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.timeout = 30

    def run_maigret(self, username: str) -> Dict[str, Any]:
        """
        Ejecuta maigret con manejo robusto de errores
        """
        try:
            # Verificar si maigret está disponible
            if not is_tool_available("maigret"):
                logger.warning("Maigret no está instalado o no disponible")
                return {
                    "error": "Maigret no está instalado o no disponible",
                    "source": "maigret",
                    "warning": "Instala con: pip install maigret",
                    'installed': False
                }

            # Ejecutar maigret
            cmd = [
                "maigret",
                username,
                "--json",  # Salida JSON
                "--simple",  # Formato simple
                "--no-color",  # Sin colores
                "--timeout", "10"  # Timeout de 10 segundos
            ]

            env = os.environ.copy()
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)

            # Ajustar para windows con posibles problemas de codificación
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,  # Esto es importante para que no salga binario
                timeout=30,
                env=env,
                encoding='utf-8',  # Evitar problemas de codificación
                errors='ignore'  # Ignorar problemas de codificación
            )

            if result.returncode in [0, 1]:
                try:
                    if result.stdout.strip():
                        # Intenta parsear JSON, con control de errores
                        raw_output = result.stdout.strip()
                        try:
                            data = json.loads(raw_output)
                            return {"data": data, "source": "maigret", "raw_output": raw_output}
                        except json.JSONDecodeError:
                            # Si no se puede parsear, devuelve el output crudo
                            return {
                                "data": {},
                                "source": "maigret",
                                "raw_output": raw_output,
                                "warning": "Salida de Maigret no en formato JSON esperado"
                            }
                    else:
                        return {
                            "data": {},
                            "source": "maigret",
                            "warning": "No se encontraron resultados o salida vacía"
                        }
                except Exception as e:
                    return {
                        "data": {},
                        "source": "maigret",
                        "raw_output": result.stdout,
                        "error": f"Error al procesar salida: {str(e)}",
                        "exception": str(e)
                    }
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                return {
                    "error": f"Maigret Error: {error_output}",
                    "source": "maigret",
                    "raw_output": error_output,
                    "return_code": result.returncode
                }
        except subprocess.TimeoutExpired:
            return {"error": "Timeout en ejecución de Maigret", "source": "maigret"}
        except Exception as e:
            logger.error(f"Error ejecutando Maigret: {e}")
            return {"error": f"Error en Maigret: {str(e)}", "source": "maigret"}

    def run_sherlock(self, username: str) -> Dict[str, Any]:
        """
        Ejecuta sherlock con manejo robusto de errores
        """
        try:
            # Verificar si sherlock está disponible
            if not is_tool_available("sherlock"):
                logger.warning("Sherlock no está instalado o no disponible")
                return {
                    "error": "Sherlock no está instalado o no disponible",
                    "source": "sherlock",
                    "warning": "Instala con: pip install sherlock-project",
                    'installed': False
                }

            # Construir comando para Sherlock (evitando posibles argumentos erróneos)
            # Sherlock puede tener diferentes versiones con opciones diferentes
            cmd = [
                "sherlock",
                username,
                "--timeout", "10"
            ]

            # Intentar distintas formas de ejecutar
            # Primero intentamos sin --json que parece tener problemas en algunas versiones
            env = os.environ.copy()
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode in [0, 1]:  # Algunas versiones devuelven 1 pero funcionan
                # Comprobar si se obtuvo error específico
                error_output = result.stderr.strip()
                if "expected one argument" in error_output:
                    # Puede haber problema con línea de argumentos
                    return {
                        "error": f"Argumentos de Sherlock incorrectos: {error_output}",
                        "source": "sherlock",
                        "raw_output": result.output,
                        "warning": "Usa 'sherlock --help' para ver sintaxis correcta"
                    }
                else:
                    # Para ahora simplemente retornar que se ejecutó (aunque quizás sin resultados)
                    return {
                        "data": {},  # Sin datos parseables
                        "source": "sherlock",
                        "raw_output": result.stdout if result.stdout else result.stderr
                    }
            else:
                error_output = result.stderr.strip() or result.stdout.strip()
                return {
                    "error": f"Error en Sherlock: {error_output}",
                    "source": "sherlock",
                    "raw_output": error_output,
                    "return_code": result.returncode
                }

        except subprocess.TimeoutExpired:
            return {"error": "Timeout en ejecución de Sherlock", "source": "sherlock"}
        except Exception as e:
            logger.error(f"Error ejecutando Sherlock: {e}")
            return {"error": f"Error en Sherlock: {str(e)}", "source": "sherlock"}

    def search_social_profiles(self, username: str, platforms: List[str] | None = None) -> Dict[str, Any]:
        """
        Realiza búsqueda en redes sociales usando herramientas externas
        """
        try:
            logger.info(f"🔍 Buscando perfiles sociales para usuario: {username}")

            # Verificar si herramientas están disponibles, e intentar instalar si pueden ser instaladas
            # En modo debugging, mostramos si hay herramientas pendientes
            # Nota: Solo mostramos en debug para evitar spam
            tool_status = get_tool_status()
            logger.debug(f"Estado herramientas SOCMINT: {tool_status}")

            # Plataformas soportadas
            supported_platforms = ["maigret", "sherlock"]

            # Si no se especifican plataformas, usar todas
            if platforms is None:
                platforms = supported_platforms
            else:
                platforms = [p for p in platforms if p.lower() in supported_platforms]

            results = {}
            all_passed = True  # Variable para saber si todas pasaron

            # Procesar cada plataforma solicitada
            for platform in platforms:
                try:
                    if platform.lower() == "maigret":
                        logger.info(f"Ejecutando Maigret para {username}")
                        maigret_result = self.run_maigret(username)
                        if maigret_result.get("error"):  # Si hay error en maigret
                            logger.warning(f"Maigret falló: {maigret_result.get('error')}")
                            all_passed = False
                        results["maigret"] = maigret_result

                    elif platform.lower() == "sherlock":
                        logger.info(f"Ejecutando Sherlock para {username}")
                        sherlock_result = self.run_sherlock(username)
                        if sherlock_result.get("error"):  # Si hay error en sherlock
                            logger.warning(f" Sherlock falló: {sherlock_result.get('error')}")
                            all_passed = False
                        results["sherlock"] = sherlock_result

                except Exception as e:
                    logger.error(f"Error procesando {platform}: {e}")
                    results[platform] = {
                        "error": f"Error al ejecutar {platform}: {str(e)}",
                        "source": platform,
                        "warning": "Error de ejecución interno"
                    }
                    all_passed = False

            # Enviar notificación si alguna herramienta faltaba
            if "maigret" in platforms and not tool_status.get("maigret", False):
                logger.warning("⚠️ Aviso: Maigret no se encontró. Usa 'pip install maigret' para instalar.")

            if "sherlock" in platforms and not tool_status.get("sherlock", False):
                logger.warning("⚠️ Aviso: Sherlock no se encontró. Usa 'pip install sherlock-project' para instalar.")

            # Retorna resultados completos
            return {
                "query": username,
                "platforms_searched": platforms,
                "timestamp": time.time(),
                "profiles_found": [],
                "total_profiles": 0,
                "errors": [],
                "social_profiles": results,
                "processing_complete": True,
                "all_tools_worked": all_passed  # Nueva propiedad para evaluar éxito total
            }

        except Exception as e:
            logger.error(f"Error general en búsqueda SOCMINT: {e}")
            return {
                "error": f"Error en búsqueda SOCMINT: {str(e)}",
                "query": username,
                "timestamp": time.time(),
                "profiles_found": [],
                "total_profiles": 0,
                "errors": [str(e)],
                "social_profiles": {},
                "processing_complete": False
            }

    def simulate_social_search(self, username: str) -> Dict[str, Any]:
        """
        Simulación de resultados cuando las herramientas externas no están disponibles
        """
        return {
            "query": username,
            "platforms_searched": ["maigret", "sherlock"],
            "timestamp": time.time(),
            "profiles_found": [],
            "total_profiles": 0,
            "errors": [],
            "social_profiles": {
                "maigret": {
                    "warning": "Maigret no disponible - Instala con: pip install maigret",
                    "source": "maigret"
                },
                "sherlock": {
                    "warning": "Sherlock no disponible - Instala con: pip install sherlock-project",
                    "source": "sherlock"
                }
            },
            "processing_complete": True,
            "all_tools_worked": False
        }


# Instancia global
socmint_searcher = SocmintSearcher()


# Funciones públicas que expones correctamente
def search_social_profiles(username: str, platforms: List[str] = None) -> Dict[str, Any]:
    """Búsqueda de perfiles sociales"""
    try:
        # Primero intentar el proceso estándar
        result = socmint_searcher.search_social_profiles(username, platforms)
        return result
    except Exception as e:
        logger.error(f"Error en search_social_profiles: {e}")
        # Devolver resultado de simulación en caso de error
        return socmint_searcher.simulate_social_search(username)


def get_supported_platforms() -> List[str]:
    return ["maigret", "sherlock"]


def get_tool_installation_instructions():
    """
    Proporciona instrucciones claras para instalar herramientas externas
    """
    return {
        "maigret": "pip install maigret",
        "sherlock": "pip install sherlock-project"
    }


async def install_socmint_dependencies():
    """
    Versión asincrónica para uso futuro o en otros contextos
    """
    # Por ahora implementación simple igual, puede ampliarse para ejecutarse en thread
    try:
        install_missing_tools()
    except:
        pass  # No falla aplicación principal si no se pueden instalar