# app.py
import os
import sys
import threading

import streamlit.web.cli as stcli
import uvicorn

from core.db_manager import create_db
from utils.logger import setup_logger
from utils.logger import bootstrap_root_logger
from api.main import app as api_app  # ⬅️ NUEVO: import de la API FastAPI

bootstrap_root_logger()

# Configurar logger
logger = setup_logger()


def start_api_server():
    """
    Arranca el servidor FastAPI en un hilo en segundo plano.

    Usa la variable de entorno QUASAR_API_RUNNING como flag
    para evitar múltiples inicios dentro del mismo proceso.
    """
    if os.environ.get("QUASAR_API_RUNNING") == "1":
        # Ya está marcado como iniciado en este proceso
        logger.info("API de QuasarIII ya estaba marcada como iniciada. No se vuelve a arrancar.")
        return

    os.environ["QUASAR_API_RUNNING"] = "1"

    host = os.getenv("QUASAR_API_HOST", "0.0.0.0")
    port = int(os.getenv("QUASAR_API_PORT", "8081"))

    def _run():
        logger.info(f"Iniciando API de QuasarIII en {host}:{port} ...")
        config = uvicorn.Config(api_app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    logger.info("API de QuasarIII lanzada en segundo plano.")


if __name__ == "__main__":
    logger.info("Arrancando Quasar III OSINT Suite...")

    # Inicializar base de datos
    create_db()

    # 🔹 Iniciar API FastAPI en segundo plano
    start_api_server()

    # Configurar y ejecutar Streamlit (como ya hacías)
    sys.argv = ["streamlit", "run", "ui/main.py"]
    sys.exit(stcli.main())
