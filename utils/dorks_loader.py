from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import json


def load_dorks_txt(path: str, *, dedupe: bool = True) -> List[str]:
    """
    Carga dorks desde un .txt.
    - Ignora líneas vacías
    - Ignora comentarios (#)
    - Deduplica preservando orden (opcional)
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return []

    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    dorks: List[str] = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        dorks.append(line)

    if dedupe:
        dorks = _deduplicate_preserve_order(dorks)

    return dorks


def load_dorks_json(path: str) -> Dict[str, List[str]]:
    """
    Carga dorks desde un .json con estructura:
    {
      "default": [...],
      "person": [...],
      "domain": [...],
      ...
    }
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}

    try:
        data: Any = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    out: Dict[str, List[str]] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, list):
            continue
        cleaned = [str(x).strip() for x in v if str(x).strip()]
        if cleaned:
            out[k] = _deduplicate_preserve_order(cleaned)

    return out


def _deduplicate_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def guess_loader(path: str) -> str:
    """Devuelve 'txt' o 'json' según extensión."""
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return "json"
    return "txt"
