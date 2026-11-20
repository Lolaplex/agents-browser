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


def test_cdp_session_isolation():
    from agents_browser.cdp import CDPClient
    c_default = CDPClient()
    c_alpha = CDPClient(session="alpha")
    c_beta = CDPClient(session="beta")
    assert c_default.port == 9222
    assert c_alpha.port != 9222
    assert c_alpha.port != c_beta.port
    assert c_alpha.user_data_dir.name == "alpha"
    assert c_alpha.user_data_dir.parent.name == "sessions"


def test_session_state_persistence():
    from agents_browser.cdp import CDPClient
    with tempfile.TemporaryDirectory() as tmpdir:
        c = CDPClient(user_data_dir=tmpdir)
        c._save_session_state(target_id="TAB_123", last_interactive=["[@1] Button: OK"])
        loaded = c._load_session_state()
        assert loaded["target_id"] == "TAB_123"
        assert loaded["last_interactive"] == ["[@1] Button: OK"]


def test_help_json_cli_parity():
    from agents_browser.help_json import help_json
    spec = help_json()
    cmds = spec["commands"]
    expected = [
        "serve", "init", "sync", "install", "skills", "open", "system-open", "headless", "close",
        "snapshot", "click", "type", "fill", "select", "scroll", "back", "reload",
        "wait", "find", "tabs", "switch-tab", "search", "read", "scrape", "screenshot",
        "download", "fetch", "extract-pdf", "audit", "inspect", "styles", "layout",
        "logs", "viewport", "eval", "record"
    ]
    for cmd in expected:
        assert cmd in cmds, f"Missing command in help_json: {cmd}"
        assert "side_effects" in cmds[cmd], f"Missing side_effects on {cmd}"


def test_cli_skills_command():
    import io
    from contextlib import redirect_stdout
    from agents_browser.__main__ import main

    f = io.StringIO()
    with redirect_stdout(f):
        main(["skills", "core"])
    out = f.getvalue()
    assert "Browser Browse Skill" in out
    assert "agents-browser snapshot -i" in out


def test_mcp_tools_registered():
    from agents_browser.mcp_server import mcp
    tools = [t.name for t in mcp._tool_manager.list_tools()]
    assert "browser_open" in tools
    assert "browser_system_open" in tools
    assert "browser_set_headless" in tools
    assert "browser_snapshot" in tools
    assert "browser_search" in tools
    assert "browser_screenshot" in tools
    assert "browser_download" in tools
    assert "browser_fetch" in tools
    assert "browser_extract_pdf" in tools
    # Coder evaluation & recording tools
    assert "browser_inspect" in tools
    assert "browser_audit" in tools
    assert "browser_get_styles" in tools
    assert "browser_get_layout" in tools
    assert "browser_get_logs" in tools
    assert "browser_set_viewport" in tools
    assert "browser_record" in tools
    assert "browser_record_start" in tools
    assert "browser_record_stop" in tools
    # Stdlib no-Chrome web tools
    assert "web_search" in tools
    assert "web_extract" in tools


def test_webtext_extract_blocks_and_links():
    from agents_browser.webtext import _TextExtractor

    html = """<html><head><title>T</title><style>x{}</style></head><body>
    <nav>menu</nav><h1>Head</h1><p>Hello world.</p>
    <a href="https://a.test/x">alink</a><script>bad()</script>
    </body></html>"""
    p = _TextExtractor()
    p.feed(html)
    texts = [t for _tag, t in p.blocks]
    assert "Head" in texts and "Hello world." in texts
    assert all("menu" not in t and "bad" not in t for t in texts)
    assert ("alink", "https://a.test/x") in p.links
    assert p.title == "T"


def test_webtext_ddg_parser_and_unwrap():
    from agents_browser.webtext import _DDGParser, _unwrap_url

    html = """<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fr.test%2F&rut=x">Title One</a>
    <a class="result__snippet">snip one</a>"""
    p = _DDGParser()
    p.feed(html)
    assert p.results[0]["title"] == "Title One"
    assert _unwrap_url(p.results[0]["url"]) == "https://r.test/"
    assert p.results[0]["snippet"] == "snip one"


def test_webtext_search_bad_engine():
    from agents_browser.webtext import web_search

    out = web_search("q", engine="nope")
    assert "Unknown engine" in out


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
        monkeypatch.setenv("AGENTS_HOST_DIR", str(fake_home / ".agents"))
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        rules = sync_mod.sync_host_rules()
        assert any("agents-browser.mdc" in r for r in rules)
        mdc = fake_home / ".agents" / "workspaces" / "default" / "rules" / "agents-browser.mdc"
        assert mdc.is_file()
        assert "alwaysApply: true" in mdc.read_text(encoding="utf-8")

        files = sync_mod.sync_always_on_files()
        agents_md = fake_home / ".agents" / "workspaces" / "default" / "AGENTS.md"
        assert agents_md.is_file()
        assert sync_mod.MARKER in agents_md.read_text(encoding="utf-8")
        assert len(files) >= 4


def test_downloads_dir():
    from agents_browser.mcp_server import downloads_dir
    d = downloads_dir()
    assert d.exists()
    assert d.name == "downloads"


def test_event_listeners():
    from agents_browser.cdp import CDPClient
    c = CDPClient()
    received = []

    def listener(params):
        received.append(params)

    c.add_event_listener("Test.event", listener)
    assert "Test.event" in c._event_listeners
    c._dispatch_event("Test.event", {"hello": "world"})
    assert len(received) == 1
    assert received[0] == {"hello": "world"}

    c.remove_event_listener("Test.event", listener)
    c._dispatch_event("Test.event", {"foo": "bar"})
    assert len(received) == 1


def test_cdp_fetch_fast():
    import asyncio
    from agents_browser.cdp import CDPClient
    c = CDPClient()

    async def _test():
        res = await c.fetch("https://httpbin.org/get")
        assert "HTTP 200 GET" in res
        assert "application/json" in res

    asyncio.run(_test())


def test_recordings_dir():
    from agents_browser.mcp_server import recordings_dir
    d = recordings_dir()
    assert d.exists()
    assert d.name == "recordings"


def test_client_init_fields():
    from agents_browser.cdp import CDPClient
    c = CDPClient()
    assert hasattr(c, "console_logs")
    assert hasattr(c, "network_logs")
    assert hasattr(c, "recordings_dir")
    assert c.recordings_dir.name == "recordings"

def test_workspace_scoped_artifacts(monkeypatch, tmp_path):
    host = tmp_path / "host"
    (host / "workspaces" / "alpha").mkdir(parents=True)
    (host / "workspaces" / "alpha" / "workspace.json").write_text('{"id": "alpha"}')
    (host / "workspaces" / "beta").mkdir(parents=True)
    (host / "workspaces" / "beta" / "workspace.json").write_text('{"id": "beta"}')
    monkeypatch.setenv("AGENTS_HOST_DIR", str(host))
    from agents_browser.cdp import artifacts_dir, CDPClient
    monkeypatch.setenv("AGENTS_WORKSPACE", "alpha")
    a = artifacts_dir("screenshots")
    assert a == host / "workspaces" / "alpha" / "browser" / "screenshots"
    monkeypatch.setenv("AGENTS_WORKSPACE", "beta")
    b = artifacts_dir("screenshots")
    assert b == host / "workspaces" / "beta" / "browser" / "screenshots"
    # profile lives on the host, shared across workspaces
    monkeypatch.setenv("AGENTS_BROWSER_PROFILE", "sess one")
    c = CDPClient()
    assert c.user_data_dir == host / "browser" / "sessions" / "sess_one"


def test_managed_browser_candidates(monkeypatch, tmp_path):
    from agents_browser import cdp
    base = tmp_path / "browser"
    (base / "bin" / "chrome-headless-shell-linux64").mkdir(parents=True)
    (base / "bin" / "chrome-headless-shell-linux64" / "chrome-headless-shell").write_text("x")
    (base / "bin" / "chrome-linux64").mkdir(parents=True)
    (base / "bin" / "chrome-linux64" / "chrome").write_text("x")
    monkeypatch.setattr(cdp, "browser_home", lambda: base)
    cands = cdp.managed_browser_candidates()
    assert len(cands) == 2
    assert cands[0].endswith("chrome")  # full chrome preferred over shell
    assert "headless-shell" in cands[1]


def test_is_headless_shell():
    from agents_browser.cdp import is_headless_shell
    assert is_headless_shell("/x/chrome-headless-shell")
    assert is_headless_shell("C:\\bin\\chrome-headless-shell.exe")
    assert not is_headless_shell("/usr/bin/google-chrome")


def test_lite_default_and_blocklists(monkeypatch):
    monkeypatch.delenv("AGENTS_BROWSER_LITE", raising=False)
    from agents_browser.cdp import CDPClient, _LITE_BLOCK_URLS, _AD_BLOCK_URLS
    c = CDPClient()
    assert c._lite is True
    assert "*.png" in _LITE_BLOCK_URLS and "*.mp4" in _LITE_BLOCK_URLS
    assert "*doubleclick.net*" in _AD_BLOCK_URLS
    monkeypatch.setenv("AGENTS_BROWSER_LITE", "0")
    assert CDPClient()._lite is False


def test_disable_lite_offline():
    import asyncio
    from agents_browser.cdp import CDPClient
    c = CDPClient()
    asyncio.run(c._disable_lite())
    assert c._lite is False


def test_set_lite_toggle():
    import asyncio
    from agents_browser.cdp import CDPClient
    c = CDPClient()
    assert "off" in asyncio.run(c.set_lite(False))
    c2 = CDPClient()
    c2._lite = False
    assert "on" in asyncio.run(c2.set_lite(True))
    assert c2._lite is True


def test_fetch_text_json_passthrough(monkeypatch):
    from agents_browser import webtext
    monkeypatch.setattr(
        webtext, "_request", lambda url, timeout=20.0: b'{"a": 1, "b": [2, 3]}'
    )
    out = webtext.fetch_text("https://api.test/data")
    assert "```json" in out and '"a": 1' in out


def test_fill_form_accepts_dict_alias(monkeypatch):
    import asyncio
    from agents_browser import mcp_server

    class Fake:
        async def fill_form(self, fields, submit_selector=""):
            return f"{fields}|{submit_selector}"

    monkeypatch.setattr(mcp_server, "_client", Fake())
    out = asyncio.run(mcp_server.browser_fill_form(fields={"@1": "x"}))
    assert "'@1': 'x'" in out
    out2 = asyncio.run(mcp_server.browser_fill_form(fields_json='{"@2": "y"}'))
    assert "'@2': 'y'" in out2


def test_in_container_detection(monkeypatch):
    import os
    import sys
    from agents_browser import cdp
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    monkeypatch.setattr(Path, "read_text", lambda self, **kw: (_ for _ in ()).throw(OSError()))
    assert cdp._in_container() is False
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/.dockerenv")
    assert cdp._in_container() is True
    monkeypatch.setattr(sys, "platform", "win32")
    assert cdp._in_container() is False

