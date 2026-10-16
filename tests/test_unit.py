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
    assert "browser_screenshot" in tools


def test_resolve_screenshot_path():
    from agents_browser.mcp_server import resolve_screenshot_path, screenshots_dir

    default = resolve_screenshot_path("")
    assert default.parent == screenshots_dir()
    assert default.name.startswith("shot-")
    assert default.suffix == ".png"

    named = resolve_screenshot_path("gangnam.png")
    assert named == screenshots_dir() / "gangnam.png"

    with tempfile.TemporaryDirectory() as tmpdir:
        abs_path = Path(tmpdir) / "custom.png"
        assert resolve_screenshot_path(str(abs_path)) == abs_path


def test_splice_browser_inject_preserves_other_blocks():
    from agents_browser.sync import splice_browser_inject, MARKER, MARKER_END

    existing = "<!-- agents-memory-sync -->\n# Memory\n<!-- /agents-memory-sync -->\n"
    spliced = splice_browser_inject(existing)
    assert "<!-- agents-memory-sync -->" in spliced
    assert MARKER in spliced
    assert MARKER_END in spliced
    # Idempotent second splice
    again = splice_browser_inject(spliced)
    assert again.count(MARKER) == 1


def test_sync_host_rules_and_always_on(monkeypatch):
    from agents_browser import sync as sync_mod

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_home = Path(tmpdir)
        monkeypatch.setenv("AGENTS_HOME", str(fake_home / ".agents"))
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        rules = sync_mod.sync_host_rules()
        assert any("agents-browser.mdc" in r for r in rules)
        mdc = fake_home / ".agents" / "rules" / "agents-browser.mdc"
        assert mdc.is_file()
        assert "alwaysApply: true" in mdc.read_text(encoding="utf-8")

        files = sync_mod.sync_always_on_files()
        agents_md = fake_home / ".agents" / "AGENTS.md"
        assert agents_md.is_file()
        assert sync_mod.MARKER in agents_md.read_text(encoding="utf-8")
        assert len(files) >= 4

