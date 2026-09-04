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


def test_find_browser_executable():
    from agents_browser.cdp import find_browser_executable
    exe = find_browser_executable()
    assert exe is not None
    assert Path(exe).exists()


def test_cdp_client_default_headless():
    from agents_browser.cdp import CDPClient
    c = CDPClient()
    # Should default to True (headless background mode)
    assert c.headless is True


def test_mcp_tools_registered():
    from agents_browser.mcp_server import mcp
    tools = [t.name for t in mcp._tool_manager.list_tools()]
    assert "browser_open" in tools
    assert "browser_system_open" in tools
    assert "browser_set_headless" in tools
    assert "browser_snapshot" in tools
    assert "browser_search" in tools
