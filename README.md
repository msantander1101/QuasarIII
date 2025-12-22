# Quasar III OSINT Suite

Quasar III es una suite OSINT moderna basada en Streamlit que centraliza autenticación, búsquedas avanzadas, visualización de grafos, generación de reportes y análisis asistido con IA en una sola aplicación web. El núcleo usa SQLite para persistencia, registra eventos en `logs/app.log` y permite almacenar claves API por usuario para integraciones externas.

## Características principales
- **Inicio rápido en Streamlit** con creación automática de base de datos y configuración de logger para registrar la actividad de la aplicación. `app.py` levanta la interfaz `ui/main.py` y asegura que las tablas existan antes de servir la UI.【F:app.py†L1-L18】【F:core/db_manager.py†L9-L85】
- **Autenticación y configuración por usuario** con almacenamiento seguro de hashes de contraseñas y claves de configuración (por ejemplo, tokens de API) en SQLite.【F:core/db_manager.py†L22-L77】【F:core/config_manager.py†L12-L60】
- **Routing de la interfaz** a páginas de login/registro, dashboard, búsquedas de personas, visualización de grafos, configuración y generación de reportes, todo orquestado desde Streamlit usando `session_state`.【F:ui/main.py†L1-L122】
- **Módulo de IA** para resúmenes, clasificación y detección de datos sensibles usando OpenAI y LangChain cuando se proporcionan las API keys correspondientes.【F:modules/ai/intelligence_core.py†L1-L196】
- **Persistencia de investigaciones** (personas, relaciones y datos de análisis) con funciones CRUD listas para ser reutilizadas por los módulos de búsqueda y visualización.【F:core/db_manager.py†L87-L200】
- **Logging centralizado** en consola y archivo `logs/app.log` con protección contra handlers duplicados en recargas de Streamlit.【F:utils/logger.py†L7-L40】

## Requisitos
- Python 3.10 o superior recomendado.
- Dependencias listadas en `requirements.txt`, que incluye Streamlit, NetworkX, OpenAI, LangChain y bibliotecas de scraping/OSINT como Sherlock y Maigret.【F:requirements.txt†L1-L21】

## Instalación
1. Clona este repositorio y entra en la carpeta del proyecto.
2. (Opcional) Crea y activa un entorno virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\\Scripts\\activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Ejecución
- Inicia la aplicación con:
  ```bash
  python app.py
  ```
  Este comando crea `data/users.db` con las tablas necesarias y arranca Streamlit apuntando a `ui/main.py`. También puedes ejecutar directamente `streamlit run ui/main.py` si prefieres usar la CLI de Streamlit.【F:app.py†L10-L18】
- Los registros se guardan en `logs/app.log`. Asegúrate de que el directorio tenga permisos de escritura.【F:utils/logger.py†L7-L40】

## Uso rápido
1. **Registro / Login:** Crea una cuenta desde la pestaña de registro y autentícate para acceder al panel.【F:ui/pages/login.py†L10-L75】
2. **Dashboard:** Usa los accesos rápidos para ir a búsquedas avanzadas, visualizar grafos o generar reportes.【F:ui/pages/dashboard.py†L14-L93】
3. **Búsquedas y análisis:** Añade personas investigadas, relaciones y datos OSINT; las entradas quedan persistidas en SQLite para su reutilización.【F:core/db_manager.py†L87-L200】
4. **Configuración y claves API:** En la página de ajustes guarda claves como `openai_api_key` o credenciales para redes sociales; se almacenan por usuario y pueden ser consultadas desde los módulos correspondientes.【F:core/config_manager.py†L12-L89】【F:modules/search/config.py†L10-L45】
5. **Funciones de IA:** Si defines `openai_api_key`, el módulo de IA se inicializa al iniciar sesión y habilita resúmenes, clasificación y detección de datos sensibles dentro de los flujos de análisis.【F:ui/main.py†L75-L83】【F:modules/ai/intelligence_core.py†L36-L196】

## Estructura del proyecto
- `app.py`: punto de entrada que inicializa la base de datos y arranca la UI de Streamlit.【F:app.py†L1-L18】
- `core/`: servicios base (DB, autenticación, gestión de configuraciones).【F:core/db_manager.py†L9-L200】【F:core/config_manager.py†L12-L89】
- `modules/`: funcionalidades de dominio (IA, búsqueda OSINT, reportes).【F:modules/ai/intelligence_core.py†L1-L196】
- `ui/`: interfaz Streamlit con páginas para login, dashboard, búsqueda, grafos, ajustes y reportes.【F:ui/main.py†L18-L122】
- `utils/`: utilidades compartidas como el sistema de logging.【F:utils/logger.py†L7-L40】

## Notas de desarrollo
- La base de datos SQLite se crea automáticamente en `data/users.db`; elimina el archivo para reiniciar los datos en entornos de prueba.【F:core/db_manager.py†L9-L85】
- Si añades nuevas integraciones que requieran claves API, usa `ConfigManager` para guardarlas y listarlas de forma consistente.【F:core/config_manager.py†L12-L89】
- El módulo de IA se mantiene deshabilitado hasta que se proporcione una clave válida; maneja el estado vía `initialize_ai_analyzer` en `ui/main.py`.【F:ui/main.py†L75-L83】
