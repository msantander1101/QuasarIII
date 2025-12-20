# utils/logger.py
import logging
import os
from typing import Optional


def _create_handlers(level: int) -> tuple[logging.Handler, logging.Handler]:
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    return file_handler, console_handler


def setup_logger(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Devuelve un logger configurado sin duplicar manejadores.

    Streamlit puede recargar el script varias veces, lo que provocaba que cada llamada
    añadiera un nuevo handler y generara líneas de log duplicadas. Para evitarlo,
    configuramos el logger sólo una vez y reutilizamos los handlers existentes.
    """

    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        file_handler, console_handler = _create_handlers(level)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
