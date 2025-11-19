# utils/logger.py
import logging
import os

def setup_logger(name=__name__, level=logging.INFO):
    # Asegurarse de que el directorio logs exista
    os.makedirs("logs", exist_ok=True)

    # Configurar logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Crear manejador de archivo (opcional)
    handler = logging.FileHandler("logs/app.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # También imprime en consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger