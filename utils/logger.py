# utils/logger.py
import logging
import os
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler


def _level_from_env(default: int) -> int:
    raw = (os.getenv("QUASAR_LOG_LEVEL") or "").upper().strip()
    if not raw:
        return default
    return getattr(logging, raw, default)


def _create_handlers(level: int) -> tuple[logging.Handler, logging.Handler]:
    os.makedirs("logs", exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d %(funcName)s() | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotación para no crecer infinito
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    return file_handler, console_handler


def setup_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Devuelve un logger configurado sin duplicar handlers (Streamlit recarga).
    - Nivel configurable por env: QUASAR_LOG_LEVEL=DEBUG/INFO/WARNING/ERROR
    - Log a consola + logs/app.log con rotación
    """
    level = _level_from_env(level)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Importante:
    # - Si pones propagate=False, SOLO verás logs de loggers que se configuren con este helper.
    # - Si lo pones True, podrás ver logs de librerías y de módulos que usan logging.getLogger(__name__)
    #   siempre que el root tenga handlers. Como tú no tienes root central, mantenemos propagate=False
    #   para no duplicar, PERO te damos un "bootstrap" para root abajo.
    logger.propagate = False

    if not logger.handlers:
        file_handler, console_handler = _create_handlers(level)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def bootstrap_root_logger(level: int = logging.INFO) -> None:
    """
    Opcional pero recomendado:
    Configura el ROOT logger una sola vez para capturar logs de módulos que usan logging.getLogger(__name__)
    sin pasar por setup_logger.
    """
    level = _level_from_env(level)
    root = logging.getLogger()

    # evitar duplicados en Streamlit
    if getattr(root, "_quasar_bootstrapped", False):
        root.setLevel(level)
        return

    root.setLevel(level)

    # si ya existen handlers, no duplicar
    if not root.handlers:
        file_handler, console_handler = _create_handlers(level)
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    # bajar ruido
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("streamlit").setLevel(logging.WARNING)

    root._quasar_bootstrapped = True
    root.info("Root logger bootstrapped | level=%s", logging.getLevelName(level))
