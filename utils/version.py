"""
Utility helpers to surface Git version details in the UI.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from typing import Tuple

APP_VERSION = "1.0.0"


def _run_git_command(args: list[str]) -> str:
    """
    Run a git command safely and return stripped output or an empty string.
    """
    try:
        result = subprocess.check_output(
            ["git", *args],
            stderr=subprocess.DEVNULL
        )
        return result.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _get_commit_from_env() -> str:
    """
    Return a short commit hash from environment variables when available.
    """
    commit = os.getenv("GIT_COMMIT_SHORT") or os.getenv("GIT_COMMIT") or ""
    return commit[:7] if commit else ""


@lru_cache(maxsize=1)
def get_git_version() -> Tuple[str, str]:
    """
    Fetch the current Git branch and short commit hash.

    Returns:
        Tuple[str, str]: (branch, short_hash)
        Empty strings if git data is unavailable.
    """
    branch = (
        os.getenv("GIT_BRANCH")
        or _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    ).strip()

    commit = _get_commit_from_env() or _run_git_command(
        ["rev-parse", "--short", "HEAD"]
    )

    return branch, commit


def get_version_label() -> str:
    """
    Return a concise version label for display in the sidebar.
    """
    branch, commit = get_git_version()

    if branch and commit:
        return f"{branch} @ {commit}"
    if commit:
        return commit

    return "sin datos de git"


def get_app_version_label() -> str:
    """
    Return a human-friendly application version string.
    """
    return f"v{APP_VERSION}"
