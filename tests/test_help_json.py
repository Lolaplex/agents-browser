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
