# 🧠 QuasarIII — OSINT & Corporate Intelligence Suite

**QuasarIII** es una plataforma modular de OSINT e inteligencia diseñada para uso corporativo.  
Incluye autenticación con control de acceso, módulos de recopilación pasiva, análisis contextual, visualización profesional para analistas y arquitectura preparada para integrarse con plataformas CTI como **OpenCTI**.

Actualmente operando en **Fase 1 — Hardening interno**, con login obligatorio y administración centralizada de usuarios.

---

## 🚀 Características principales

| Módulo / Funcionalidad | Estado | Descripción |
|------------------------|--------|--------------|
| 🔐 Autenticación segura | ✔ Activo | Acceso con cuentas internas, sin registro público |
| 👑 Panel Admin | ✔ Activo | Crear, activar, desactivar usuarios y cambiar roles |
| 🔎 OSINT Pasivo Web | ✔ Activo | Radar contextual Google/Bing/DDG con resultados normalizados |
| 🕵️ Google Dorks | ✔ Activo | Motor de dorks con scoring, cards y relevancia |
| 🧬 Breach Intelligence Interno | ⚙ Parcial | Ingesta interna de dumps, análisis sensible y scoring de exposición |
| 🔄 OpenCTI Integration | 📅 Fase 3 | Preparado para API / conectores de enriquecimiento e ingestión STIX2 |
| 🧱 Permission Layer | 📅 Fase 2 | Control por rol de módulos sensibles (darkweb, breach, etc.) |

---

## 📦 Instalación

```bash
git clone https://github.com/msantander1101/QuasarIII.git
cd QuasarIII
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt

▶️ Ejecución

python app.py

o:

streamlit run app.py

🔐 Gestión de usuarios (Hardening Fase 1)
Crear el usuario administrador inicial

python -m core.create_admin_user

Funcionamiento

    ❌ No hay registro público.

    ✔ Solo el administrador puede crear cuentas nuevas.

    ✔ Roles disponibles: admin, analyst.

    ✔ Panel de administración desde la UI solo visible para admin.

🧭 Flujo del sistema

    Usuario accede → pantalla de login.

    Si es analista, accede a los módulos OSINT.

    Si es admin, además puede:

        Crear usuarios

        Cambiar roles

        Activar/desactivar cuentas

📁 Estructura del proyecto

QuasarIII/
├── app.py                          # Entrada principal
├── core/
│   ├── auth_manager.py             # Autenticación y roles
│   ├── config_manager.py           # Configuración por usuario y API keys
│   ├── db_manager.py               # Persistencia con SQLite
├── modules/
│   ├── search/                     # Web, dorks, general, correlación
│   ├── ai/                         # Inteligencia artificial / NLP
│   └── breach/                     # Breach pipeline defensivo
├── ui/
│   ├── auth/                       # Login + Panel administrador
│   ├── pages/                      # Secciones principales de la interfaz
│   └── components/                 # Bloques visuales reutilizables
├── utils/                          # Helpers, logging, formatos
├── data/                           # Base de datos interna
└── logs/                           # Logs de ejecución

🧠 Preparado para Integración con OpenCTI (Fase 3)

Ya está contemplada la arquitectura para:

    Conector de enriquecimiento (OpenCTI → QuasarIII)

    Envío de hallazgos como STIX2 (QuasarIII → OpenCTI)

    API /api/search para consumo desde plataforma CTI

    Mapeo automático → Identity / ObservedData / Indicator / Relationships

    Esta fase está planificada sin alterar tu estructura actual.

📅 Roadmap
Fase	Objetivo	Estado
Fase 1	Hardening, login, panel admin, sin registro	🟢 Lista
Fase 2	PermissionManager y control de módulos por rol	🟡 Próxima
Fase 3	API externa + Conector OpenCTI STIX2	🔵 Diseño
Fase 4	IA, correlación avanzada, Data Lake OSINT	🟣 Largo plazo
🧾 CHANGELOG
v0.3.0 — Hardening

    Se elimina registro público

    Login obligatorio

    Panel admin de usuarios

    Breach pipeline básico

    Normalización de resultados OSINT

v0.2.0 — OSINT UI

    Módulos web/dorks

    Cards con scoring y relevancia

    Unificación visual

v0.1.0 — MVP

    Primera UI

    Búsqueda web básica

🤝 Contribuir

    Crear rama: feature/nueva-fuente o fix/xxxx

    Mantener formato de resultados OSINT compatible con advanced_search

    Asegurar coherencia con UI (cards / snippets / scoring)

📞 Contacto

Autor: msantander1101
OSINT / CTI / Inteligencia aplicada
🛡 Nota Legal

Este software está orientado a investigación defensiva y corporativa.
Su uso para actividades ofensivas o ilegales queda fuera del alcance del proyecto.
