# app.py
import streamlit.web.cli as stcli
import sys
from core.db_manager import create_db
from utils.logger import setup_logger

# Configurar logger
logger = setup_logger()

if __name__ == "__main__":
    logger.info("Arrancando Quasar III OSINT Suite...")

    # Inicializar base de datos
    create_db()

    # Configurar y ejecutar Streamlit
    sys.argv = ["streamlit", "run", "ui/main.py"]
    sys.exit(stcli.main())
