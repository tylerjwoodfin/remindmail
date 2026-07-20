"""
Check PyPI for newer RemindMail releases and email the user once per version.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Any, Optional

from packaging.version import InvalidVersion, Version

PYPI_JSON_URL = "https://pypi.org/pypi/remindmail/json"
PACKAGE_NAME = "remindmail"
REQUEST_TIMEOUT_SECONDS = 10


def _display_version(version_str: str) -> str:
    """Return a human-friendly version without the PEP 440 epoch prefix."""
    if "!" in version_str:
        return version_str.split("!", 1)[1]
    return version_str


def _parse_version(version_str: str) -> Optional[Version]:
    try:
        return Version(version_str)
    except InvalidVersion:
        return None


def _truthy(value: Any) -> bool:
    """Treat missing/None as enabled; accept common falsey config strings."""
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return bool(value)


def fetch_latest_pypi_version(
    url: str = PYPI_JSON_URL, timeout: int = REQUEST_TIMEOUT_SECONDS
) -> Optional[str]:
    """
    Fetch the latest RemindMail version string from the PyPI JSON API.

    Returns:
        The version string (e.g. ``1!3.5.0``), or None on network/parse failure.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    version_str = (payload.get("info") or {}).get("version")
    if not version_str or not isinstance(version_str, str):
        return None
    return version_str


def get_installed_version() -> Optional[str]:
    """Return the installed remindmail version, or None if unavailable."""
    try:
        return package_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return None


def should_notify(
    installed: str,
    latest: str,
    last_notified: Optional[str],
) -> bool:
    """
    Return True when latest is newer than installed and has not been emailed yet.
    """
    installed_v = _parse_version(installed)
    latest_v = _parse_version(latest)
    if installed_v is None or latest_v is None:
        return False
    if latest_v <= installed_v:
        return False
    if last_notified:
        last_v = _parse_version(last_notified)
        if last_v is not None and latest_v <= last_v:
            return False
    return True


def build_update_email(latest: str, installed: str) -> tuple[str, str]:
    """Return (subject, body) for a release notification email."""
    latest_display = _display_version(latest)
    installed_display = _display_version(installed)
    subject = f"🎉 RemindMail {latest_display} Released"
    body = (
        f"A new version of RemindMail is available.<br><br>"
        f"<b>Installed:</b> {installed_display}<br>"
        f"<b>Latest:</b> {latest_display}<br><br>"
        f"Upgrade with:<br>"
        f"<code>pip install -U remindmail</code><br><br>"
        f"Release notes: "
        f'<a href="https://github.com/tylerjwoodfin/remindmail/releases">'
        f"https://github.com/tylerjwoodfin/remindmail/releases</a>"
    )
    return subject, body


class UpdateChecker:
    """
    Optionally emails the user when a newer RemindMail version is on PyPI.

    Controlled by Cabinet ``remindmail → update-checks`` (default True).
    Stores ``remindmail → last_notified_version`` so each release is emailed once.
    """

    def __init__(self, cabinet: Any, mail: Any) -> None:
        self.cabinet = cabinet
        self.mail = mail

    def check_and_notify(self, is_dry_run: bool = False) -> bool:
        """
        Check PyPI and send an update email when appropriate.

        Args:
            is_dry_run: If True, log what would be sent without emailing or
                updating Cabinet.

        Returns:
            True if an update email was sent (or would be sent on dry-run).
        """
        enabled = self.cabinet.get("remindmail", "update-checks")
        if not _truthy(enabled):
            self.cabinet.log("Update checks disabled; skipping", level="debug")
            return False

        installed = get_installed_version()
        if not installed:
            self.cabinet.log(
                "Could not determine installed RemindMail version; skipping update check",
                level="debug",
            )
            return False

        latest = fetch_latest_pypi_version()
        if not latest:
            self.cabinet.log(
                "Could not fetch latest RemindMail version from PyPI; skipping update check",
                level="debug",
            )
            return False

        last_notified = self.cabinet.get("remindmail", "last_notified_version")
        if isinstance(last_notified, str):
            last_notified_str: Optional[str] = last_notified
        else:
            last_notified_str = None

        if not should_notify(installed, latest, last_notified_str):
            self.cabinet.log(
                f"No update email needed (installed={installed}, latest={latest}, "
                f"last_notified={last_notified_str})",
                level="debug",
            )
            return False

        subject, body = build_update_email(latest, installed)
        if is_dry_run:
            self.cabinet.log(
                f"[dry-run] Would send update email: {subject}", level="info"
            )
            return True

        try:
            self.mail.send(subject, body)
            self.cabinet.put("remindmail", "last_notified_version", value=latest)
            self.cabinet.log(
                f"Sent update email for RemindMail {_display_version(latest)}",
                level="info",
            )
            return True
        except Exception as exc:  # noqa: BLE001 — never fail generate on update email
            self.cabinet.log(
                f"Failed to send update email: {exc}",
                level="error",
            )
            return False
