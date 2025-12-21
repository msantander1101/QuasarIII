# modules/search/emailint.py
"""
Email Intelligence — OSINT correcto y sin ruido.
Incluye:
  - HIBP (si API key configurada)
  - GHunt (solo Gmail / Google)
  - Verificación básica
  - Enlaces OSINT pasivos (para abrir manualmente desde UI)
NO incluye:
  - Pastes / Leaks (solo bajo demanda desde UI)
"""

import re
import time
import logging
import urllib.parse
import os
import shutil
import subprocess
from typing import Dict, Any, List
from requests import Session
import io
import contextlib

from core.config_manager import config_manager

logger = logging.getLogger(__name__)

# --------------------------------------------------
# CONSTANTES / SESSION
# --------------------------------------------------

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}$")
TIMEOUT = 25

session = Session()
session.headers.update({
    "User-Agent": "QuasarIII-EmailInt/1.0",
    "Accept": "application/json",
})

# --------------------------------------------------
# GHUNT (opcional)
# --------------------------------------------------

GHUNT_AVAILABLE = False
GHUNT_IMPORT_ERROR = None
GHUNT_WARNINGS: List[str] = []

try:
    from ghunt.modules.email import hunt as ghunt_hunt  # type: ignore
    import ghunt.helpers.gmaps as ghunt_gmaps  # type: ignore

    _orig_get_reviews = ghunt_gmaps.get_reviews

    @contextlib.contextmanager
    def _silent_bar(*_args, **_kwargs):
        yield lambda *_a, **_k: None

    _gmaps_warning_emitted = False

    async def _safe_get_reviews(as_client, gaia_id):  # type: ignore[override]
        """
        GHunt gmaps.get_reviews sin progress bar y con fallback defensivo.
        """
        global _gmaps_warning_emitted

        original_bar = getattr(ghunt_gmaps, "alive_bar", None)
        ghunt_gmaps.alive_bar = _silent_bar  # type: ignore[assignment]
        try:
            return await _orig_get_reviews(as_client, gaia_id)
        except IndexError as exc:  # pragma: no cover
            if not _gmaps_warning_emitted:
                msg = "GHunt: respuesta de Maps inesperada, se omiten reseñas/fotos."
                GHUNT_WARNINGS.append(msg)
                logger.warning("%s %s", msg, exc)
                _gmaps_warning_emitted = True
            return "failed", {}, [], []
        except Exception as exc:  # pragma: no cover
            msg = "GHunt: error en get_reviews, devolviendo vacío."
            GHUNT_WARNINGS.append(msg)
            logger.warning("%s %s", msg, exc)
            return "failed", {}, [], []
        finally:
            if original_bar is not None:
                ghunt_gmaps.alive_bar = original_bar  # type: ignore[assignment]

    ghunt_gmaps.get_reviews = _safe_get_reviews  # type: ignore[assignment]

    GHUNT_AVAILABLE = True
    logger.info("GHunt cargado correctamente")
except Exception as e:
    GHUNT_AVAILABLE = False
    GHUNT_IMPORT_ERROR = str(e)
    logger.debug("GHunt no disponible: %s", GHUNT_IMPORT_ERROR)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------


def verify_email_format(email: str) -> bool:
    return isinstance(email, str) and bool(EMAIL_RE.match(email.strip()))


def _build_source_link(email: str, source_name: str, base_url: str = "") -> Dict[str, Any]:
    """
    Crea un enlace seguro hacia una fuente externa.

    Si se proporciona base_url se utiliza directamente, de lo contrario
    se genera una búsqueda web con el nombre de la fuente.
    """
    encoded_email = urllib.parse.quote_plus(email)
    url = base_url or f"https://www.google.com/search?q={encoded_email}+{urllib.parse.quote_plus(source_name)}"

    return {
        "name": source_name,
        "url": url,
        "source": source_name.lower().replace(" ", "_"),
        "email": email,
    }


def build_email_source_links(email: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Enlaces listos para búsqueda manual en fuentes OSINT de correo.

    No ejecuta llamadas activas: solo devuelve URLs de búsqueda
    para que el analista pueda abrirlas desde la UI.
    """
    lead_sources = [
        {
            "name": "EmailFinder",
            "source": "emailfinder",
            "url": "https://github.com/rix4uni/EmailFinder",
            "command": "emailfinder -e <email>",
            "install": "go install github.com/rix4uni/emailfinder@latest",
            "confidence": "media",
            "type": "lead_generation",
            "email": email,
        },
    ]

    info_sources: List[Dict[str, Any]] = []
    verification_sources: List[Dict[str, Any]] = []

    return {
        "lead_generation": lead_sources,
        "email_info": info_sources,
        "verification": verification_sources,
    }


# --------------------------------------------------
# EMAILFINDER (CLI opcional)
# --------------------------------------------------


def emailfinder_lookup(email: str) -> Dict[str, Any]:
    install_hint = "go install github.com/rix4uni/emailfinder@latest"

    resolved_cli = shutil.which("emailfinder")
    resolved_script = None

    if os.path.exists("emailfinder.py"):
        resolved_script = "emailfinder.py"
    else:
        resolved_script = shutil.which("emailfinder.py")

    if resolved_cli:
        command = [resolved_cli, "-e", email]
        command_str = f"{resolved_cli} -e <email>"
    elif resolved_script:
        command = ["python3", resolved_script, "-e", email]
        command_str = "python3 emailfinder.py -e <email>"
    else:
        return {
            "source": "emailfinder",
            "success": False,
            "error": "EmailFinder no encontrado",
            "command": "emailfinder -e <email>",
            "install": install_hint,
        }

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        output = (proc.stdout or "").strip()
        error_output = (proc.stderr or "").strip()

        return {
            "source": "emailfinder",
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "output": output,
            "stderr": error_output,
            "command": command_str,
            "install": install_hint,
        }
    except FileNotFoundError:
        return {
            "source": "emailfinder",
            "success": False,
            "error": "runtime de EmailFinder no encontrado (python3/go)",
            "command": command_str,
            "install": install_hint,
        }
    except subprocess.TimeoutExpired:
        return {
            "source": "emailfinder",
            "success": False,
            "error": "emailfinder timeout",
            "command": command_str,
            "install": install_hint,
        }
    except Exception as exc:  # pragma: no cover
        logger.exception("EmailFinder error")
        return {
            "source": "emailfinder",
            "success": False,
            "error": str(exc),
            "command": "python3 emailfinder.py -e <email>",
        }


# --------------------------------------------------
# HIBP
# --------------------------------------------------


def hibp_lookup(email: str, api_key: str) -> Dict[str, Any]:
    if not api_key:
        return {"source": "hibp", "error": "no_api_key"}

    try:
        encoded = urllib.parse.quote_plus(email)
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{encoded}"
        headers = {
            "x-apikey": api_key,
            "User-Agent": "QuasarIII-EmailInt/1.0",
        }

        r = session.get(url, headers=headers, timeout=TIMEOUT)

        if r.status_code == 200:
            data = r.json()
            return {
                "source": "hibp",
                "breached": True,
                "breach_count": len(data),
                "details": data,
            }

        if r.status_code == 404:
            return {"source": "hibp", "breached": False, "breach_count": 0}

        if r.status_code == 401:
            return {"source": "hibp", "error": "invalid_api_key"}

        return {"source": "hibp", "error": f"HTTP {r.status_code}"}

    except Exception as e:
        logger.exception("HIBP lookup error")
        return {"source": "hibp", "error": str(e)}


# --------------------------------------------------
# GHUNT
# --------------------------------------------------


def ghunt_lookup(email: str) -> Dict[str, Any]:
    if not GHUNT_AVAILABLE:
        return {"source": "ghunt", "success": False, "error": GHUNT_IMPORT_ERROR}

    try:
        import asyncio

        GHUNT_WARNINGS.clear()
        buffer = io.StringIO()

        async def _run():
            with contextlib.redirect_stdout(buffer):
                return await ghunt_hunt(None, email)

        raw = asyncio.run(_run())
        output = buffer.getvalue().strip()
        buffer.close()

        return {
            "source": "ghunt",
            "success": True,
            "data": raw,
            "output": output,
            "warnings": list(GHUNT_WARNINGS),
        }

    except Exception as e:
        logger.exception("GHunt error")
        return {"source": "ghunt", "success": False, "error": str(e)}


# --------------------------------------------------
# VERIFICATION
# --------------------------------------------------


def verify_deliverability(email: str) -> Dict[str, Any]:
    if not verify_email_format(email):
        return {
            "source": "verification",
            "email": email,
            "deliverable": False,
            "reason": "invalid_format",
        }

    return {
        "source": "verification",
        "email": email,
        "deliverable": "unknown",
    }


# --------------------------------------------------
# MAIN ENTRY POINT
# --------------------------------------------------


def search_email_info(email: str, user_id: int = 1) -> Dict[str, Any]:
    """
    Email intelligence principal.
    NO ejecuta pastes.
    """
    start = time.time()

    out = {
        "email": email,
        "timestamp": time.time(),
        "hibp": None,
        "ghunt": None,
        "emailfinder": None,
        "verification": None,
        "sources": {},
        "errors": [],
        "search_time": 0.0,
    }

    try:
        email = email.strip()

        # ---------------- HIBP ----------------
        hibp_key = None
        if hasattr(config_manager, "get_config"):
            hibp_key = config_manager.get_config(user_id, "hibp")

        out["hibp"] = hibp_lookup(email, hibp_key)

        # ---------------- GHUNT ----------------
        if email.lower().endswith(("@gmail.com", "@googlemail.com")):
            out["ghunt"] = ghunt_lookup(email)
        else:
            out["ghunt"] = {"source": "ghunt", "skipped": "non_gmail"}

        # ---------------- EMAILFINDER ----------------
        out["emailfinder"] = emailfinder_lookup(email)

        # ---------------- VERIFICATION ----------------
        out["verification"] = verify_deliverability(email)

        # ---------------- ENLACES OSINT ----------------
        out["sources"] = build_email_source_links(email)

    except Exception as e:
        logger.exception("Email intelligence error")
        out["errors"].append(str(e))

    out["search_time"] = round(time.time() - start, 3)
    return out


# --------------------------------------------------
# COMPAT
# --------------------------------------------------


def check_email_breach(email: str, user_id: int = 1) -> Dict[str, Any]:
    hibp_key = None
    if hasattr(config_manager, "get_config"):
        hibp_key = config_manager.get_config(user_id, "hibp")
    return hibp_lookup(email, hibp_key)
