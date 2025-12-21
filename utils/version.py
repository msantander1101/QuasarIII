"""Utility helpers to surface Git version details in the UI."""

import subprocess
from typing import Tuple


def _run_git_command(args: list[str]) -> str:
    """Run a git command safely and return stripped output or an empty string."""

    try:
        result = subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)
        return result.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def get_git_version() -> Tuple[str, str]:
    """
    Fetch the current Git branch and short commit hash.

    Returns:
        Tuple[str, str]: (branch, short_hash). Empty strings if git data is unavailable.
    """

    branch = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _run_git_command(["rev-parse", "--short", "HEAD"])
    return branch, commit


def get_version_label() -> str:
    """Return a concise version label for display in the sidebar."""

    branch, commit = get_git_version()
    if branch and commit:
        return f"{branch} @ {commit}"
    if commit:
        return f"{commit}"
    return "sin datos git"
