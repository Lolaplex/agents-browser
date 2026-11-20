"""On-demand Chrome for Testing download — opt-in, never bundled.

``agents-browser install`` fetches ``chrome-headless-shell`` (~100MB), or
the full ``chrome`` with ``--full`` (needed for visible windows), into
``<browser_home>/bin/`` where ``find_browser_executable()`` discovers it
after system browsers. Pure stdlib; no root needed.
"""

from __future__ import annotations

import json
import os
import platform
import stat
import sys
import tempfile
import urllib.request
import zipfile

from .cdp import browser_home

_CFT_VERSIONS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)


def _platform_slug() -> str:
    """Chrome for Testing platform key for this host."""
    if sys.platform == "win32":
        return "win64" if platform.machine().lower() in ("amd64", "x86_64") else "win32"
    if sys.platform == "darwin":
        return "mac-arm64" if platform.machine().lower() == "arm64" else "mac-x64"
    return "linux64"


def install_browser(full: bool = False) -> str:
    """Download + unpack a Chrome for Testing binary; returns status text."""
    plat = _platform_slug()
    product = "chrome" if full else "chrome-headless-shell"
    data = json.loads(urllib.request.urlopen(_CFT_VERSIONS_URL, timeout=20).read())
    chan = data["channels"]["Stable"]
    version = chan["version"]
    url = next(
        d["url"] for d in chan["downloads"][product] if d["platform"] == plat
    )

    bin_dir = browser_home() / "bin"
    exe_name = product + (".exe" if plat.startswith("win") else "")
    dest = bin_dir / f"{product}-{plat}"
    exe_path = dest / exe_name
    if exe_path.is_file():
        return f"{product} {version} already installed: {exe_path}"

    bin_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".zip")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agents-browser"})
        with os.fdopen(fd, "wb") as fh, urllib.request.urlopen(req, timeout=300) as resp:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
        with zipfile.ZipFile(tmp) as zf:
            zf.extractall(bin_dir)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    if not exe_path.is_file():
        return f"Error: expected binary missing after extract: {exe_path}"
    if not plat.startswith("win"):
        exe_path.chmod(exe_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return (
        f"Installed {product} {version} ({plat}) -> {exe_path}\n"
        "Discovery picks it up automatically (after system browsers); "
        "or point AGENTS_BROWSER_BIN at the path."
    )
