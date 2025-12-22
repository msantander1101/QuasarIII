# modules/search/emailint.py
"""
Email Intelligence — OSINT correcto y sin ruido.
Incluye:
  - GHunt (solo Gmail / Google)
  - Hashtray (Gravatar pivot)
  - Verificación básica
  - Enlaces OSINT pasivos (para abrir manualmente desde UI)
NO incluye:
  - HIBP (se moverá al módulo de leaks)
  - Pastes / Leaks (solo bajo demanda desde UI)
"""

import re
import time
import logging
import urllib.parse
import os
import sys
import shutil
import subprocess
from typing import Dict, Any, List, Optional
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
    No ejecuta llamadas activas: solo devuelve URLs/comandos para UI.
    """
    info_sources = [
        {
            "name": "Gravatar (manual)",
            "source": "gravatar",
            "url": f"https://en.gravatar.com/site/check/{urllib.parse.quote_plus(email.strip().lower())}",
            "confidence": "media",
            "type": "pivot",
            "email": email,
        },
    ]

    verification_sources: List[Dict[str, Any]] = []

    return {
        "email_info": info_sources,
        "verification": verification_sources,
    }


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
# HASHTRAY (CLI)
# --------------------------------------------------

def _resolve_hashtray_cli() -> Optional[str]:
    """
    Devuelve ruta al binario `hashtray` si existe.
    """
    path_bin = shutil.which("hashtray")
    if path_bin:
        return path_bin

    # fallback típico venv
    venv_bin = os.path.join(sys.prefix, "bin", "hashtray")
    if os.path.isfile(venv_bin) and os.access(venv_bin, os.X_OK):
        return venv_bin

    return None


def _install_hashtray() -> Dict[str, Any]:
    """
    Intenta instalar hashtray vía pip.
    IMPORTANTE: No forzamos downgrades/changes de deps por conflictos (ej. lxml/maigret).
    """
    cmd = [sys.executable, "-m", "pip", "install", "hashtray"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "success": proc.returncode == 0,
    }


def _hashtray_found_from_output(stdout: str, stderr: str) -> Optional[bool]:
    """
    Heurística:
      - 'Gravatar profile not found' => False
      - Si hay URL/perfil o hash => True (best-effort)
      - Si no hay pistas => None
    """
    text = f"{stdout or ''}\n{stderr or ''}".lower()
    if "gravatar profile not found" in text and "404" in text:
        return False
    if "https://gravatar.com/avatar/" in text or "gravatar.com/avatar/" in text:
        return True
    if "account hash" in text or "primary email" in text:
        return True
    return None


def hashtray_email(email: str, auto_install: bool = True) -> Dict[str, Any]:
    """
    Ejecuta: hashtray email <email>
    Devuelve stdout/stderr + heurística found.
    """
    start = time.time()

    result: Dict[str, Any] = {
        "source": "hashtray",
        "email": email,
        "success": False,
        "found": None,
        "present": False,
        "cli_path": None,
        "command": None,
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "elapsed": 0.0,
        "error": None,
        "install": None,
        "attempts": [],
    }

    if not verify_email_format(email):
        result["error"] = "invalid_email"
        result["elapsed"] = round(time.time() - start, 3)
        return result

    cli = _resolve_hashtray_cli()
    if not cli and auto_install:
        install = _install_hashtray()
        result["install"] = install
        result["attempts"].append({"action": "pip_install", **install})
        cli = _resolve_hashtray_cli()

    if not cli:
        result["error"] = "hashtray_not_available"
        result["elapsed"] = round(time.time() - start, 3)
        return result

    result["present"] = True
    result["cli_path"] = cli

    cmd = [cli, "email", email]
    result["command"] = " ".join(cmd)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        result.update({
            "stdout": stdout,
            "stderr": stderr,
            "returncode": proc.returncode,
            "success": proc.returncode == 0,
            "found": _hashtray_found_from_output(stdout, stderr),
        })

        # hashtray puede devolver rc=0 incluso con "not found" (404); lo tratamos como ok informativo
        if result["success"] and result["found"] is False:
            pass

    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
    except Exception as exc:
        logger.exception("hashtray error")
        result["error"] = str(exc)

    result["elapsed"] = round(time.time() - start, 3)
    return result


# --------------------------------------------------
# VERIFICATION
# --------------------------------------------------


def verify_deliverability(email: str) -> Dict[str, Any]:
    if not verify_email_format(email):
        return {"source": "verification", "email": email, "deliverable": False, "reason": "invalid_format"}

    return {"source": "verification", "email": email, "deliverable": "unknown"}


# --------------------------------------------------
# MAIN ENTRY POINT
# --------------------------------------------------


def search_email_info(email: str, user_id: int = 1) -> Dict[str, Any]:
    """
    Email intelligence principal.
    NO ejecuta leaks.
    """
    start = time.time()

    out = {
        "email": email,
        "timestamp": time.time(),
        "ghunt": None,
        "hashtray": None,
        "verification": None,
        "sources": {},
        "errors": [],
        "search_time": 0.0,
    }

    try:
        email = (email or "").strip()

        # ---------------- GHUNT ----------------
        if email.lower().endswith(("@gmail.com", "@googlemail.com")):
            out["ghunt"] = ghunt_lookup(email)
        else:
            out["ghunt"] = {"source": "ghunt", "skipped": "non_gmail"}

        # ---------------- HASHTRAY ----------------
        out["hashtray"] = hashtray_email(email, auto_install=True)

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
    """
    Compat: antes usaba HIBP. Ahora se moverá al módulo de leaks.
    """
    return {"source": "hibp", "error": "moved_to_leaks_module"}
