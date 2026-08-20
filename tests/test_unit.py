import tempfile
import json
from pathlib import Path
from agents_browser.sync import _merge_mcp_server_into_file, _merge_zed_settings


def test_merge_mcp_server_into_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "mcp.json"
        res = _merge_mcp_server_into_file(config_file)
        assert res.startswith("OK")
        assert config_file.exists()
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert "agents-browser" in data["mcpServers"]


def test_merge_zed_settings():
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "settings.json"
        res = _merge_zed_settings(settings_file)
        assert "Zed context_servers" in res
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert "agents-browser" in data["context_servers"]
