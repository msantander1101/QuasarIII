# modules/search/emailint.py
"""
Email Intelligence — OSINT correcto y sin ruido.
Incluye:
  - HIBP (si API key configurada)
  - GHunt (solo Gmail / Google)
  - Verificación básica
  - Enlaces OSINT pasivos (para abrir manualmente desde UI)
  - EmailFinder (lead generation por dominio + parsing + cruce controlado)
  - Email2PhoneNumber (scrape Paypal/eBay/LastPass)  ✅
NO incluye:
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
from pathlib import Path
import importlib
from typing import Dict, Any, List, Optional, Tuple
from requests import Session
import io
import contextlib

from core.config_manager import config_manager

logger = logging.getLogger(__name__)

# --------------------------------------------------
# CONSTANTES / SESSION
# --------------------------------------------------

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}$")
EMAIL_EXTRACT_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}")
TIMEOUT = 25

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

EMAIL2PHONE_REPO = "https://github.com/martinvigo/email2phonenumber.git"
EMAIL2PHONE_DIR = Path(__file__).resolve().parents[2] / "data" / "email2phonenumber"

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


def _extract_emails_from_text(text: str) -> List[str]:
    """
    Extrae emails de cualquier salida de texto (EmailFinder suele mezclar líneas).
    Devuelve lista deduplicada y ordenada.
    """
    if not text:
        return []
    found = EMAIL_EXTRACT_RE.findall(text)
    uniq = sorted({e.strip().lower() for e in found if verify_email_format(e)})
    return uniq


def _domain_of(email: str) -> str:
    return email.split("@", 1)[1].lower() if isinstance(email, str) and "@" in email else ""


def _annotate_candidates(target_email: str, candidates: List[str]) -> List[Dict[str, Any]]:
    """
    Marca:
      - exact_match: si el candidato es exactamente el email investigado
      - same_domain: si coincide el dominio
    """
    target = (target_email or "").strip().lower()
    target_domain = _domain_of(target)

    out: List[Dict[str, Any]] = []
    for c in candidates:
        c_norm = (c or "").strip().lower()
        out.append({
            "email": c_norm,
            "exact_match": c_norm == target,
            "same_domain": bool(target_domain) and _domain_of(c_norm) == target_domain,
        })
    return out


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
    # Nota: EmailFinder trabaja por DOMINIO; el command aquí es orientativo (modo stdin)
    lead_sources = [
        {
            "name": "EmailFinder",
            "source": "emailfinder",
            "url": "https://github.com/rix4uni/EmailFinder",
            "command": 'echo "<domain>" | emailfinder',
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
# EMAIL2PHONENUMBER (SCRAPE PAYPAL/EBAY/LASTPASS)
# --------------------------------------------------


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text or "")


def _ensure_email2phone_dependencies() -> Dict[str, Any]:
    """
    Verifica e instala dependencias requeridas por email2phonenumber.
    """
    dependencies = [("bs4", "beautifulsoup4"), ("requests", "requests")]
    missing = []

    for module_name, package_name in dependencies:
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)

    result: Dict[str, Any] = {
        "source": "email2phonenumber_deps",
        "installed": True,
        "packages": missing,
    }

    if not missing:
        return result

    cmd = [sys.executable, "-m", "pip", "install", *missing]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )

    result.update({
        "installed": proc.returncode == 0,
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    })

    if proc.returncode != 0:
        result["error"] = "pip_install_failed"

    return result


def _ensure_email2phonenumber_repo(base_path: Optional[Path] = None) -> Tuple[Optional[Path], Dict[str, Any]]:
    """
    Garantiza que el repositorio email2phonenumber esté disponible localmente.
    """
    repo_path = Path(base_path or EMAIL2PHONE_DIR)
    info: Dict[str, Any] = {
        "source": "email2phonenumber_repo",
        "path": str(repo_path),
    }

    script_path = repo_path / "email2phonenumber.py"
    if script_path.is_file():
        info["status"] = "present"
        return repo_path, info

    try:
        if repo_path.exists():
            if repo_path.is_dir():
                shutil.rmtree(repo_path)
            else:
                repo_path.unlink()
        repo_path.parent.mkdir(parents=True, exist_ok=True)

        proc = subprocess.run(
            ["git", "clone", EMAIL2PHONE_REPO, str(repo_path)],
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )

        info.update({
            "status": "cloned" if proc.returncode == 0 else "clone_failed",
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        })

        if proc.returncode != 0:
            return None, info

        if not script_path.is_file():
            info.update({
                "status": "missing_script",
                "error": "email2phonenumber.py not found after clone",
            })
            return None, info

        return repo_path, info

    except subprocess.TimeoutExpired:
        info.update({"status": "timeout", "error": "git_clone_timeout"})
        return None, info

    except Exception as exc:
        logger.exception("email2phonenumber clone error")
        info.update({"status": "error", "error": str(exc)})
        return None, info


def _parse_email2phonenumber_output(text: str) -> Dict[str, Any]:
    """
    Parsea la salida de email2phonenumber (modo scrape) a estructura utilizable.
    """
    parsed: Dict[str, Any] = {
        "messages": [],
        "lastpass": {
            "reported": None,
            "last_digits": None,
            "length_with_cc": None,
            "length_without_cc": None,
            "non_us": False,
            "notes": [],
        },
        "ebay": {
            "reported": None,
            "first_digit": None,
            "last_digits": None,
            "notes": [],
        },
        "paypal": {
            "reported": None,
            "first_digit": None,
            "last_digits": None,
            "last_digits_count": None,
            "length_without_cc": None,
            "notes": [],
        },
    }

    if not text:
        return parsed

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parsed["messages"].append(line)

        lp = parsed["lastpass"]
        eb = parsed["ebay"]
        pp = parsed["paypal"]

        if "Lastpass reports that the last 2 digits are:" in line:
            match = re.search(r"last 2 digits are: (\d+)", line)
            if match:
                lp["reported"] = True
                lp["last_digits"] = match.group(1)
            continue

        if "Lastpass did not report any digits" in line:
            lp["reported"] = False
            lp["notes"].append(line)
            continue

        if "Lastpass reports a non US phone number" in line:
            lp["non_us"] = True
            continue

        if "Lastpass reports that the length of the phone number (including country code)" in line:
            match = re.search(r"is (\d+) digits", line)
            if match:
                lp["length_with_cc"] = int(match.group(1))
            continue

        if "Lastpass reports that the length of the phone number (without country code)" in line:
            match = re.search(r"is (\d+) digits", line)
            if match:
                lp["length_without_cc"] = int(match.group(1))
            continue

        if "Ebay reports that the first digit is:" in line:
            match = re.search(r"first digit is: (\d+)", line)
            if match:
                eb["reported"] = True
                eb["first_digit"] = match.group(1)
            continue

        if "Ebay reports that the last 2 digits are:" in line:
            match = re.search(r"last 2 digits are: (\d+)", line)
            if match:
                eb["reported"] = True
                eb["last_digits"] = match.group(1)
            continue

        if "Ebay did not report any digits" in line:
            eb["reported"] = False
            eb["notes"].append(line)
            continue

        if "Paypal reports that the last" in line:
            match = re.search(r"last (\d+) digits are: (\d+)", line)
            if match:
                pp["reported"] = True
                pp["last_digits_count"] = int(match.group(1))
                pp["last_digits"] = match.group(2)
            continue

        if "Paypal reports that the first digit is:" in line:
            match = re.search(r"first digit is: (\d+)", line)
            if match:
                pp["reported"] = True
                pp["first_digit"] = match.group(1)
            continue

        if "Paypal reports that the length of the phone number (without country code)" in line:
            match = re.search(r"is (\d+) digits", line)
            if match:
                pp["length_without_cc"] = int(match.group(1))
            continue

        if "Paypal did not report any digits" in line:
            pp["reported"] = False
            pp["notes"].append(line)
            continue

    return parsed


def email2phonenumber_scrape(email: str, quiet_mode: bool = False) -> Dict[str, Any]:
    """
    Ejecuta `email2phonenumber.py scrape -e <email>` y devuelve salida parseada.
    """
    start = time.time()
    result: Dict[str, Any] = {
        "source": "email2phonenumber",
        "email": email,
        "quiet_mode": quiet_mode,
        "success": False,
        "repo": None,
        "dependency_check": None,
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "parsed": {},
        "error": None,
        "elapsed": 0.0,
    }

    if not verify_email_format(email):
        result["error"] = "invalid_email"
        return result

    repo_path, repo_info = _ensure_email2phonenumber_repo()
    result["repo"] = repo_info

    if not repo_path:
        result["error"] = repo_info.get("error", "repo_unavailable")
        return result

    deps_info = _ensure_email2phone_dependencies()
    result["dependency_check"] = deps_info
    if deps_info.get("installed") is False:
        result["error"] = deps_info.get("error", "dependency_install_failed")
        return result

    cmd = [sys.executable, "email2phonenumber.py", "scrape", "-e", email]
    if quiet_mode:
        cmd.append("-q")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )

        result.update({
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "returncode": proc.returncode,
            "parsed": _parse_email2phonenumber_output(_strip_ansi(proc.stdout or "")),
            "success": proc.returncode == 0,
        })

    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
    except FileNotFoundError as exc:
        result["error"] = str(exc)
    except Exception as exc:
        logger.exception("email2phonenumber error")
        result["error"] = str(exc)

    result["elapsed"] = round(time.time() - start, 3)
    return result


# --------------------------------------------------
# EMAILFINDER (CLI opcional)
# --------------------------------------------------


def emailfinder_lookup(email: str) -> Dict[str, Any]:
    """
    EmailFinder OSINT real:
    - Extrae dominio del email
    - Instala emailfinder si no existe
    - Ejecuta usando STDIN (modo oficial)
    - Parse: lista de emails deduplicada
    - Marca coincidencias con email investigado
    """

    def _resolve_emailfinder() -> Optional[str]:
        path_bin = shutil.which("emailfinder")
        if path_bin:
            return path_bin

        candidates = [
            os.path.expanduser("~/go/bin/emailfinder"),
        ]

        gopath = os.environ.get("GOPATH")
        if gopath:
            candidates.append(os.path.join(gopath, "bin", "emailfinder"))

        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c

        return None

    def _extract_domain(email_value: str) -> Optional[str]:
        if "@" not in email_value:
            return None
        return email_value.split("@", 1)[1].lower()

    try:
        domain = _extract_domain(email)
        if not domain:
            return {
                "source": "emailfinder",
                "success": False,
                "error": "email sin dominio válido",
            }

        emailfinder_bin = _resolve_emailfinder()

        # 1️⃣ instalar si no existe
        if not emailfinder_bin:
            install_proc = subprocess.run(
                ["go", "install", "github.com/rix4uni/emailfinder@latest"],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )

            if install_proc.returncode != 0:
                return {
                    "source": "emailfinder",
                    "success": False,
                    "error": "fallo instalando emailfinder",
                    "stderr": (install_proc.stderr or "").strip(),
                    "install": "go install github.com/rix4uni/emailfinder@latest",
                }

            emailfinder_bin = _resolve_emailfinder()
            if not emailfinder_bin:
                return {
                    "source": "emailfinder",
                    "success": False,
                    "error": "emailfinder instalado pero no localizado",
                    "hint": "Asegura que ~/go/bin o $GOPATH/bin está en PATH",
                }

        # 2️⃣ ejecutar usando STDIN (modo oficial)
        cmd = [emailfinder_bin]
        proc = subprocess.run(
            cmd,
            input=f"{domain}\n",
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        raw_out = (proc.stdout or "").strip()
        raw_err = (proc.stderr or "").strip()

        emails = _extract_emails_from_text(raw_out)
        candidates = _annotate_candidates(email, emails)

        return {
            "source": "emailfinder",
            "success": proc.returncode == 0,
            "domain": domain,
            "mode": "stdin",
            "command": f'echo "{domain}" | emailfinder',
            "output": raw_out,
            "stderr": raw_err,
            "returncode": proc.returncode,
            "emails": emails,                 # lista única
            "candidates": candidates,         # lista anotada
            "stats": {
                "emails_found": len(emails),
                "exact_matches": sum(1 for x in candidates if x.get("exact_match")),
                "same_domain": sum(1 for x in candidates if x.get("same_domain")),
            },
        }

    except subprocess.TimeoutExpired:
        return {
            "source": "emailfinder",
            "success": False,
            "error": "emailfinder timeout",
        }

    except FileNotFoundError as exc:
        return {
            "source": "emailfinder",
            "success": False,
            "error": "go/emailfinder no encontrado en runtime",
            "details": str(exc),
        }

    except Exception as exc:
        logger.exception("EmailFinder error")
        return {
            "source": "emailfinder",
            "success": False,
            "error": str(exc),
        }


# --------------------------------------------------
# HIBP
# --------------------------------------------------


def hibp_lookup(email: str, api_key: Optional[str]) -> Dict[str, Any]:
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
# ENRICHMENT (HIBP/GHUNT) PARA CANDIDATOS
# --------------------------------------------------


def enrich_candidate_emails(
    emails: List[str],
    user_id: int,
    max_emails: int = 10
) -> List[Dict[str, Any]]:
    """
    Enriquecimiento controlado:
    - HIBP para cada email si hay key
    - GHunt solo para gmail/googlemail
    - limita a max_emails para evitar rate-limit / latencia
    """
    hibp_key = None
    if hasattr(config_manager, "get_config"):
        hibp_key = config_manager.get_config(user_id, "hibp")

    out: List[Dict[str, Any]] = []
    seen = set()

    for e in emails:
        e_norm = (e or "").strip().lower()
        if not e_norm or e_norm in seen:
            continue
        seen.add(e_norm)

        item: Dict[str, Any] = {"email": e_norm}

        # HIBP
        if hibp_key:
            item["hibp"] = hibp_lookup(e_norm, hibp_key)
        else:
            item["hibp"] = {"source": "hibp", "error": "no_api_key"}

        # GHunt (solo gmail)
        if e_norm.endswith(("@gmail.com", "@googlemail.com")):
            item["ghunt"] = ghunt_lookup(e_norm)
        else:
            item["ghunt"] = {"source": "ghunt", "skipped": "non_gmail"}

        out.append(item)

        if len(out) >= max_emails:
            break

    return out


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
        "email2phonenumber": None,
        "emailfinder": None,
        "emailfinder_enriched": [],
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

        # ---------------- EMAIL2PHONENUMBER ----------------
        out["email2phonenumber"] = email2phonenumber_scrape(email)

        # ---------------- EMAILFINDER ----------------
        out["emailfinder"] = emailfinder_lookup(email)

        # ---------------- CRUCE CANDIDATOS (HIBP/GHUNT) ----------------
        ef = out.get("emailfinder") or {}
        found_emails = ef.get("emails") or []
        out["emailfinder_enriched"] = enrich_candidate_emails(
            found_emails,
            user_id=user_id,
            max_emails=10,
        )

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
