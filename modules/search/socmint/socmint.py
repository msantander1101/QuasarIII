"""
SOCMINT Engine — Stable & Embedded
- Sherlock + Maigret con flags CORRECTOS
- Auto-detección PATH / embebido
- Compatible con Streamlit UI
"""

import os
import json
import time
import shutil
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "search")

os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------------------------------
# TOOL DETECTION
# -------------------------------------------------

def detect_tools() -> Dict[str, Optional[str]]:
    """
    Detecta Sherlock / Maigret:
    1) PATH
    2) tools/ embebidos
    """
    tools = {}

    # Sherlock
    tools["sherlock"] = (
        shutil.which("sherlock")
        or os.path.join(TOOLS_DIR, "sherlock", "sherlock.py")
    )

    # Maigret
    tools["maigret"] = (
        shutil.which("maigret")
        or os.path.join(TOOLS_DIR, "maigret", "maigret.py")
    )

    for k, v in tools.items():
        if v and not os.path.exists(v):
            tools[k] = None

    return tools


TOOLS = detect_tools()

# -------------------------------------------------
# UTILS
# -------------------------------------------------

def _run(cmd, timeout=30):
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            text=True
        )
        return proc
    except Exception as e:
        logger.exception("SOCMINT command failed")
        return None


def _safe_load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# -------------------------------------------------
# SHERLOCK
# -------------------------------------------------

def _run_sherlock(username: str) -> Dict[str, Any]:
    bin_path = TOOLS.get("sherlock")
    if not bin_path:
        return {"error": "sherlock not available"}

    out_file = os.path.join(DATA_DIR, f"sherlock_{username}.json")

    cmd = [
        "python", bin_path,
        username,
        "--json", out_file,
        "--print-found",
        "--timeout", "20"
    ] if bin_path.endswith(".py") else [
        bin_path,
        username,
        "--json", out_file,
        "--print-found",
        "--timeout", "20"
    ]

    proc = _run(cmd, timeout=40)

    data = _safe_load_json(out_file)
    if data:
        return {"data": data}

    return {
        "error": proc.stderr.strip() if proc else "execution failed"
    }


# -------------------------------------------------
# MAIGRET
# -------------------------------------------------

def _run_maigret(username: str) -> Dict[str, Any]:
    bin_path = TOOLS.get("maigret")
    if not bin_path:
        return {"error": "maigret not available"}

    cmd = [
        "python", bin_path,
        username,
        "--json", "simple",
        "--folderoutput", DATA_DIR,
        "--timeout", "20",
        "--print-found"
    ] if bin_path.endswith(".py") else [
        bin_path,
        username,
        "--json", "simple",
        "--folderoutput", DATA_DIR,
        "--timeout", "20",
        "--print-found"
    ]

    proc = _run(cmd, timeout=40)

    # localizar reporte generado
    report = None
    for f in os.listdir(DATA_DIR):
        if username in f and f.endswith(".json") and "report" in f.lower():
            report = os.path.join(DATA_DIR, f)
            break

    if report:
        data = _safe_load_json(report)
        if data:
            return {"data": data}

    return {
        "error": proc.stderr.strip() if proc else "execution failed"
    }


# -------------------------------------------------
# PUBLIC API
# -------------------------------------------------

def search_social_profiles(username: Optional[str]) -> Dict[str, Any]:
    """
    SOCMINT entrypoint estable para AdvancedSearcher
    """
    start = time.time()

    if not username or len(username.strip()) < 2:
        return {
            "source": "social",
            "query": username or "",
            "results": {},
            "errors": ["invalid username"],
            "has_data": False
        }

    username = username.strip()

    results = {
        "source": "social",
        "query": username,
        "results": {},
        "errors": [],
        "has_data": False
    }

    sherlock = _run_sherlock(username)
    maigret = _run_maigret(username)

    results["results"]["sherlock"] = sherlock
    results["results"]["maigret"] = maigret

    if "data" in sherlock or "data" in maigret:
        results["has_data"] = True

    results["_metadata"] = {
        "execution_time": round(time.time() - start, 2),
        "tools": TOOLS
    }

    return results
