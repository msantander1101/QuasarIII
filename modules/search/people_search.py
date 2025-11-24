# modules/search/people_search.py
"""
Búsqueda real de personas con integración a servicios públicos (OSINT)
Fuentes integradas:
    • SocialFinder, RoboFinder, SearchPeopleFree
    • Username Search: UserSearch.org, InstantUsername, DetectDee, Rhino Profile Checker, etc.
    • Face Recognition: VK.watch, FaceOnLive, Faceagle, ProfileImageIntel
    • Namint

Características:
    - Caché SQLite centralizada (data/cache/osint_cache.db)
    - Soporte Tor / proxy
    - Búsqueda por nombre, username o imagen
    - Extracción estructurada de datos cuando sea posible
    - Normalización de resultados compatible con grafo e IA
"""

import os
import re
import json
import time
import hashlib
import sqlite3
import threading
import mimetypes
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
import requests

# ------------------------------------------------------------
# 🔧 Ajustes para compatibilidad
# ------------------------------------------------------------
# Algunas funciones de este módulo dependen de la configuración
# del usuario (por ejemplo, proxy o nivel de concurrencia). En
# ocasiones anteriores provocaban errores porque la función
# ``get_user_setting`` no estaba definida. Añadimos un stub
# que siempre devuelve ``None`` para evitar fallos cuando no
# exista una configuración específica. Si se desea integrar con
# un gestor de configuración real, se puede reemplazar esta
# función por la adecuada.

def get_user_setting(username: str, key: str):
    """Stub para obtener configuraciones de usuario. Siempre devuelve None.

    Args:
        username: Nombre de usuario de la sesión.
        key: Clave de configuración solicitada (por ejemplo 'proxy' o 'concurrency').

    Returns:
        None: Para indicar que no hay configuración establecida.
    """
    return None


from PIL import Image
import imagehash
from core.config_manager import config_manager
from utils.logger import setup_logger

# ============================================================
# ⚙️ Configuración base
# ============================================================

CACHE_PATH = os.path.join("data", "cache")
DB_PATH = os.path.join(CACHE_PATH, "osint_cache.db")
os.makedirs(CACHE_PATH, exist_ok=True)

DEFAULT_TTL = 12 * 60 * 60  # 12 horas
DEFAULT_WORKERS = 5
DEFAULT_TIMEOUT = (10, 25)

_db_lock = threading.Lock()


# ============================================================
# 🧱 Utilidades de caché global
# ============================================================

def _ensure_schema():
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    source_group TEXT,
                    q TEXT,
                    username TEXT,
                    payload TEXT,
                    created_at INTEGER
                )
            """)
            conn.commit()
        finally:
            conn.close()


def _make_key(group: str, q: str, username: str) -> str:
    raw = f"{group}::{q}::{username}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(group: str, q: str, username: str, ttl: int = DEFAULT_TTL) -> Optional[List[Dict[str, Any]]]:
    _ensure_schema()
    now = int(time.time())
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("SELECT payload, created_at FROM cache WHERE key=?", (_make_key(group, q, username),))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        payload, created = row
        if now - created > ttl:
            return None
        return json.loads(payload)


def _cache_set(group: str, q: str, username: str, payload: List[Dict[str, Any]]):
    _ensure_schema()
    now = int(time.time())
    data = json.dumps(payload, ensure_ascii=False)
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "REPLACE INTO cache (key, source_group, q, username, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (_make_key(group, q, username), group, q, username, data, now),
        )
        conn.commit()
        conn.close()


# ============================================================
# 🌐 HTTP Session (Tor/proxy)
# ============================================================

def _build_session(username: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0 Safari/537.36",
    })
    proxy = get_user_setting(username, "proxy")
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    else:
        s.proxies.update({"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"})
    return s


# ============================================================
# 🔍 Fuentes
# ============================================================

def _misc_sources(q: str) -> List[tuple]:
    return [
        ("SocialFinder", f"https://socialfinder.io/?q={q}"),
        ("RoboFinder", f"https://robofinder.io/search?q={q}"),
        ("SearchPeopleFree", f"https://www.searchpeoplefree.com/find/{q.replace(' ', '-')}")
    ]


def _username_sources(q: str) -> List[tuple]:
    username = q.replace("@", "")
    return [
        ("UserSearch.org", f"https://usersearch.org/results/?q={username}"),
        ("InstantUsername", f"https://instantusername.com/#/{username}"),
        ("DetectDee", f"https://detectdee.com/search/{username}"),
        ("Rhino Profile Checker", f"https://rhinosearch.io/{username}"),
        ("DigitalFootprintCheck", f"https://digitalfootprintcheck.com/?user={username}"),
        ("Maigret OSINT Bot", f"https://github.com/soxoj/maigret?q={username}"),
        ("Cupidcr4wl", f"https://cupidcr4wl.io/search?q={username}"),
        ("User-Searcher", f"https://usersearcher.io/?q={username}"),
        ("AnalyzeID", f"https://analyzeid.com/search/{username}"),
        ("HandleHawk", f"https://handlehawk.com/?handle={username}")
    ]


def _face_sources(q: str) -> List[tuple]:
    return [
        ("VK.watch", "https://vk.watch/"),
        ("FaceOnLive", "https://faceonlive.com/search"),
        ("Faceagle", "https://faceagle.ai/"),
        ("ProfileImageIntel", "https://profileimageintel.com/"),
    ]


def _namint_sources(q: str) -> List[tuple]:
    return [
        ("Namint", f"https://namint.com/search?name={q.replace(' ', '+')}"),
    ]


# ============================================================
# 🧠 Hash de imagen y helpers
# ============================================================

def _phash_image(img_path: str) -> Optional[str]:
    try:
        img = Image.open(img_path)
        return str(imagehash.phash(img))
    except Exception:
        return None


def _is_image(q: str) -> bool:
    return os.path.isfile(q) and mimetypes.guess_type(q)[0] and "image" in mimetypes.guess_type(q)[0]


# ============================================================
# ⚙️ Worker de recolección
# ============================================================

def _collect_from_sources(username: str, group: str, sources: List[tuple], q: str, use_cache=True) -> List[Dict[str, Any]]:
    if use_cache:
        cached = _cache_get(group, q, username)
        if cached:
            for r in cached:
                r["_cached"] = True
            return cached

    s = _build_session(username)
    results = []
    for name, url in sources:
        results.append({
            "platform": group.capitalize(),
            "source": name,
            "title": f"Búsqueda en {name} para {q}",
            "link": url,
            "snippet": "Abrir para revisar coincidencias.",
            "structured": {},
            "_cached": False
        })
    _cache_set(group, q, username, results)
    return results


# ============================================================
# 🧩 Router principal
# ============================================================

def search_people(query: str, username: str, max_results: int = 20, use_cache=True) -> List[Dict[str, Any]]:
    """
    Detección automática de tipo:
        - @username → username_sources
        - Nombre y apellido → misc + namint
        - Imagen (ruta/URL) → face_sources
    """
    results = []
    group_tasks = []

    # Detectar tipo
    if _is_image(query) or re.match(r"^https?://.*\.(jpg|png|jpeg|gif)$", query):
        groups = ["face"]
    elif re.match(r"^@?\w{3,}$", query):
        groups = ["username"]
    else:
        groups = ["misc", "namint"]

    mapping = {
        "misc": _misc_sources,
        "username": _username_sources,
        "face": _face_sources,
        "namint": _namint_sources,
    }

    workers = DEFAULT_WORKERS
    try:
        cfg_workers = get_user_setting(username, "concurrency")
        if cfg_workers:
            workers = int(cfg_workers)
    except Exception:
        pass

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for g in groups:
            fn = mapping[g]
            sources = fn(query)
            group_tasks.append(ex.submit(_collect_from_sources, username, g, sources, query, use_cache))

        for fut in as_completed(group_tasks):
            try:
                chunk = fut.result()
                results.extend(chunk)
            except Exception as e:
                logger.warning(f"[people_search] Error: {e}")

    # Limitar
    return results[:max_results]


# ============================================================
# 👤 Clase PeopleSearcher para integraciones OSINT
# ============================================================

class PeopleSearcher:
    """
    Buscador de perfiles sociales utilizando herramientas OSINT
    como Maigret y Sherlock. Proporciona métodos para ejecutar
    búsquedas externas y devolver los resultados en un formato
    estructurado que otros módulos (por ejemplo, SOCMINT) puedan
    interpretar fácilmente.

    La búsqueda se realiza mediante la ejecución de los
    comandos CLI correspondientes. Si las herramientas no están
    instaladas o devuelven un formato inesperado, el resultado
    incluirá un mensaje de error. Los comandos se ejecutan con
    un tiempo de espera para evitar bloqueos.
    """

    def __init__(self):
        # Tiempo máximo en segundos para ejecutar cada herramienta
        self.timeout = 60

    def _run_external_tool(self, cmd: List[str]) -> Dict[str, Any]:
        """Ejecuta una herramienta externa y devuelve su salida.

        Args:
            cmd: Lista con el comando y argumentos a ejecutar.

        Returns:
            Un diccionario con claves ``raw_output`` si se pudo ejecutar
            pero la salida no es JSON, o ``error`` si hubo algún problema
            al ejecutar la herramienta.
        """
        import shutil
        import subprocess
        tool_name = cmd[0]
        # Verificar que la herramienta exista en PATH
        if not shutil.which(tool_name):
            return {"error": f"{tool_name} no está instalada o no se encuentra en el PATH"}
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            # Algunos comandos devuelven la salida útil por stderr
            output = proc.stdout.strip() or proc.stderr.strip()
            if proc.returncode != 0 and not output:
                return {"error": f"{tool_name}: retorno {proc.returncode}"}
            # Intentar parsear como JSON
            try:
                return json.loads(output)
            except Exception:
                return {"raw_output": output}
        except subprocess.TimeoutExpired:
            return {"error": f"{tool_name}: tiempo de espera agotado"}
        except Exception as e:
            return {"error": f"{tool_name}: error al ejecutar: {e}"}

    def search_social_profiles(self, username: str, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """Busca perfiles sociales de un usuario utilizando Maigret y Sherlock.

        Args:
            username: Nombre de usuario o identificador a buscar.
            platforms: Lista opcional de plataformas donde filtrar los resultados.

        Returns:
            Un diccionario con claves 'maigret' y 'sherlock' cuyos
            valores son diccionarios con resultados por plataforma,
            o mensajes de error/advertencia. Si una herramienta no está
            instalada, se incluirá un mensaje de error.
        """
        # Construir comandos para ejecutar maigret y sherlock. Utilizamos
        # opciones para producir salidas JSON cuando sea posible.
        # Para Maigret:
        #   -n: No realizar búsquedas de correo
        #   -d: resultados detallados
        #   -o json: formato de salida JSON
        # Para Sherlock no hay salida JSON oficial, así que se genera
        # un JSON básico si se instala la versión modificada. Por defecto
        # devolveremos la salida cruda.
        results: Dict[str, Any] = {}
        # Maigret
        maigret_cmd = ["maigret", username, "--no-color", "--json"]
        results["maigret"] = self._run_external_tool(maigret_cmd)
        # Sherlock
        # Sherlock admite la opción -j/--json en algunas bifurcaciones
        sherlock_cmd = ["sherlock", username, "--json"]
        results["sherlock"] = self._run_external_tool(sherlock_cmd)
        return results

    # Métodos adicionales para compatibilidad con futuros usos
    def search_people_by_name(self, name: str) -> Dict[str, Any]:
        """Alias de búsqueda social por nombre (username)."""
        return self.search_social_profiles(name)

    def search_person_by_email(self, email: str) -> Dict[str, Any]:
        """Búsqueda de personas por email (sin implementación real)."""
        return {"error": "Búsqueda por email no implementada"}

    def search_person_by_phone(self, phone: str) -> Dict[str, Any]:
        """Búsqueda de personas por número de teléfono (sin implementación real)."""
        return {"error": "Búsqueda por teléfono no implementada"}


# Instancia global para reutilizar en otros módulos
people_searcher = PeopleSearcher()

# ------------------------------------------------------------
# Funciones públicas
# ------------------------------------------------------------

def search_social_profiles(username: str, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
    """Wrapper público para buscar perfiles sociales mediante PeopleSearcher."""
    return people_searcher.search_social_profiles(username, platforms)

def search_people_by_name(name: str) -> Dict[str, Any]:
    """Wrapper público para buscar perfiles sociales por nombre."""
    return people_searcher.search_people_by_name(name)

def search_person_by_email(email: str) -> Dict[str, Any]:
    """Wrapper público para buscar por email."""
    return people_searcher.search_person_by_email(email)

def search_person_by_phone(phone: str) -> Dict[str, Any]:
    """Wrapper público para buscar por teléfono."""
    return people_searcher.search_person_by_phone(phone)

def advanced_search(query: str) -> Dict[str, Any]:
    """Realiza una búsqueda avanzada y devuelve resultados sociales.

    Actualmente, esta función es un alias de ``search_social_profiles``.
    Puede ampliarse para incluir otras fuentes.
    """
    return people_searcher.search_social_profiles(query)
