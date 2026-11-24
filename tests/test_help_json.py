import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "src" / "agents_browser"
# Load updates-style: isolate help_json module
_spec = importlib.util.spec_from_file_location(
    "agents_browser_help_json",
    _ROOT / "help_json.py",
)
mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
# Provide a fake package path so Path(__file__) works; relative imports unused now
sys.modules["agents_browser_help_json"] = mod
_spec.loader.exec_module(mod)


def test_help_json_shape():
    data = mod.help_json()
    assert data["name"] == "agents-browser"
    from agents_browser import __version__
    assert data["version"] == __version__
    assert "open" in data["commands"]
    assert "snapshot" in data["commands"]
    assert "download" in data["commands"]
    assert "fetch" in data["commands"]
    assert "extract-pdf" in data["commands"]
    assert "--help-json" in data["flags"]
    json.dumps(data)


def test_file_writing_commands_are_mutating():
    commands = mod.help_json()["commands"]
    for name in ("screenshot", "extract-pdf", "record", "fetch"):
        assert commands[name]["side_effects"] == "mutating", name


def test_every_command_declares_side_effects():
    commands = mod.help_json()["commands"]
    for name, spec in commands.items():
        assert spec["side_effects"] in ("read-only", "mutating"), name


def test_cdp_commands_are_host_local():
    commands = mod.help_json()["commands"]
    for name in ("open", "click", "type", "screenshot", "record", "eval", "fetch"):
        assert commands[name]["host_local"] is True, name
    for name in ("serve", "skills", "read-url"):
        assert "host_local" not in commands[name], name


def test_help_json_subprocess(tmp_path=None):
    import subprocess
    proc = subprocess.run(
        [sys.executable, "-m", "agents_browser", "--help-json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed["commands"], dict)
