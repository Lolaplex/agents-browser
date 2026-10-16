"""
Sync agents-browser always-on rules, skills, and MCP server configuration across all installed IDEs.
Supports Cursor, Antigravity IDE, Claude Code, Claude Desktop, Zed (context_servers), Codex, VS Code (Cline/Roo-Code), Windsurf.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SKILLS = ["browser-browse", "browser-scrape"]

MARKER = "<!-- agents-browser-sync -->"
MARKER_END = "<!-- /agents-browser-sync -->"
RULE_FILENAME = "agents-browser.mdc"

ALWAYS_ON_BODY = """# Browser Control (`agents-browser`)

- **Zero-Node Headless CDP**: For web verification, live UI testing, DOM snapshots, form filling, or article scraping, ALWAYS use MCP `agents-browser` (`browser_open`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_evaluate`, `browser_screenshot`) instead of spawning Playwright/Puppeteer/Node.
- **Headless by Default**: Runs silently in background (`--headless=new`). Only pass `visible=True` (`browser_open(..., visible=True)`) or `browser_system_open` when the user explicitly asks for a visible window.
- **Indexed `@ref` Workflow**: Call `browser_open(url)` → `browser_snapshot()` to get `@1`, `@2` element refs → `browser_click("@1")` / `browser_type("@2", ...)`."""


def _agents_home() -> Path:
    env = os.environ.get("AGENTS_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".agents"


def mcp_entry() -> Dict[str, Any]:
    """Returns standard MCP server descriptor for agents-browser."""
    return {
        "command": sys.executable if sys.executable else "python",
        "args": ["-m", "agents_browser", "serve"],
    }


def splice_region(existing: str, begin: str, end: str, inner: str) -> str:
    """Replace or append a closed marked region. Text outside the markers stays."""
    payload = inner.strip("\n")
    block = f"{begin}\n{payload}\n{end}"
    text = existing or ""
    if begin in text and end in text:
        pre, rest = text.split(begin, 1)
        _, post = rest.split(end, 1)
        return pre + block + post
    if begin in text:
        pre, _rest = text.split(begin, 1)
        return (pre.rstrip() + "\n\n" if pre.strip() else "") + block + "\n"
    if not text.strip():
        return block + "\n"
    return text.rstrip() + "\n\n" + block + "\n"


def splice_browser_inject(existing: str, inner: str = ALWAYS_ON_BODY) -> str:
    return splice_region(existing or "", MARKER, MARKER_END, inner)


def rule_text() -> str:
    return (
        "---\n"
        "description: Minimal headless CDP browser automation (agents-browser). Always apply.\n"
        "alwaysApply: true\n"
        "---\n\n"
        f"{MARKER}\n\n"
        f"{ALWAYS_ON_BODY.strip()}\n\n"
        f"{MARKER_END}\n"
    )


def _bind_or_copy(dest: Path, src: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if dest.exists() and dest.resolve() == src.resolve():
            return str(dest)
    except OSError:
        pass
    if dest.exists() or dest.is_symlink():
        try:
            dest.unlink()
        except OSError:
            pass
    rel = os.path.relpath(str(src), start=str(dest.parent))
    try:
        os.symlink(rel, str(dest))
        return str(dest)
    except OSError:
        pass
    try:
        os.link(str(src), str(dest))
        return str(dest)
    except OSError:
        shutil.copy2(str(src), str(dest))
        return str(dest)


def zed_config_dir() -> Path:
    home = Path.home()
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(home / "AppData" / "Roaming")
        return Path(appdata) / "Zed"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Zed"
    return home / ".config" / "zed"


def sync_host_rules() -> List[str]:
    """Write ~/.agents/rules/agents-browser.mdc and bind into Cursor, Gemini, Windsurf rules."""
    home = Path.home()
    agents_rules = _agents_home() / "rules"
    agents_rules.mkdir(parents=True, exist_ok=True)
    canonical = agents_rules / RULE_FILENAME
    canonical.write_text(rule_text(), encoding="utf-8")
    written = [str(canonical)]

    host_rule_dirs = [
        home / ".cursor" / "rules",
        home / ".gemini" / "config" / "rules",
        home / ".codeium" / "windsurf" / "rules",
    ]
    for rdir in host_rule_dirs:
        rdir.mkdir(parents=True, exist_ok=True)
        written.append(_bind_or_copy(rdir / RULE_FILENAME, canonical))
    return written


def _upsert_agents_md(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = ""
    if path.exists() and not path.is_symlink():
        try:
            old = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            old = ""
    elif path.is_symlink():
        try:
            old = path.read_text(encoding="utf-8", errors="replace")
            path.unlink()
        except OSError:
            old = ""
    path.write_text(splice_browser_inject(old, ALWAYS_ON_BODY), encoding="utf-8")
    return str(path)


def sync_always_on_files() -> List[str]:
    """Splice <!-- agents-browser-sync --> block into global AGENTS.md / CLAUDE.md files."""
    home = Path.home()
    agents_home = _agents_home()
    targets = [
        agents_home / "AGENTS.md",
        home / ".gemini" / "config" / "AGENTS.md",
        zed_config_dir() / "AGENTS.md",
        home / ".claude" / "AGENTS.md",
    ]
    written: List[str] = []
    for target in targets:
        written.append(_upsert_agents_md(target))

    for pair_dir in (agents_home, home / ".claude"):
        agents_md = pair_dir / "AGENTS.md"
        claude_md = pair_dir / "CLAUDE.md"
        if claude_md.exists() and not claude_md.is_symlink():
            try:
                c_text = claude_md.read_text(encoding="utf-8", errors="replace")
                a_text = agents_md.read_text(encoding="utf-8", errors="replace")
                if c_text != a_text and MARKER not in c_text:
                    written.append(_upsert_agents_md(claude_md))
                    continue
            except OSError:
                pass
        written.append(_bind_or_copy(claude_md, agents_md))
    return written


def known_host_mcp_paths() -> List[Path]:
    """Returns a list of all potential MCP configuration file paths on the host system."""
    home = Path.home()
    paths: List[Path] = [
        home / ".cursor" / "mcp.json",
        _agents_home() / "mcp.json",
        home / ".claude.json",
        home / ".claude" / "mcp.json",
        home / ".claude" / "settings.json",
        home / ".codeium" / "windsurf" / "mcp_config.json",
        home / ".gemini" / "antigravity-ide" / "mcp_config.json",
        home / ".gemini" / "config" / "mcp_config.json",
        home / ".gemini" / "config" / "mcp.json",
        home / ".codex" / "mcp.json",
        home / ".codex" / "config.json",
    ]

    ide_Products = ["Cursor", "Code", "Code - Insiders", "VSCodium", "Windsurf"]
    ext_ids = ["rooveterinaryinc.roo-cline", "saoudrizwan.claude-dev"]

    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA") or str(home / "AppData" / "Roaming"))
        paths.append(appdata / "Claude" / "claude_desktop_config.json")
        for prod in ide_Products:
            for ext in ext_ids:
                paths.append(appdata / prod / "User" / "globalStorage" / ext / "settings" / "cline_mcp_settings.json")
    elif sys.platform == "darwin":
        app_support = home / "Library" / "Application Support"
        paths.append(app_support / "Claude" / "claude_desktop_config.json")
        for prod in ide_Products:
            for ext in ext_ids:
                paths.append(app_support / prod / "User" / "globalStorage" / ext / "settings" / "cline_mcp_settings.json")
    else:
        config = home / ".config"
        paths.append(config / "Claude" / "claude_desktop_config.json")
        for prod in ide_Products:
            for ext in ext_ids:
                paths.append(config / prod / "User" / "globalStorage" / ext / "settings" / "cline_mcp_settings.json")

    return paths


def known_zed_paths() -> List[Path]:
    """Returns potential Zed settings.json paths."""
    home = Path.home()
    paths: List[Path] = [
        home / ".config" / "zed" / "settings.json",
    ]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(home / "AppData" / "Roaming")
        paths.append(Path(appdata) / "Zed" / "settings.json")
    elif sys.platform == "darwin":
        paths.append(home / "Library" / "Application Support" / "Zed" / "settings.json")
    return paths


def _strip_jsonc(text: str) -> str:
    """Strip single-line and multi-line comments from JSONC text."""
    out: List[str] = []
    i = 0
    n = len(text)
    in_str = False
    escape = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_str:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _merge_mcp_server_into_file(path: Path) -> str:
    """Safely insert or update agents-browser in an MCP settings file."""
    if not path.parent.exists():
        return ""
    if path.exists():
        raw = path.read_text(encoding="utf-8", errors="replace")
        try:
            clean = _strip_jsonc(raw)
            data = json.loads(clean) if clean.strip() else {}
        except json.JSONDecodeError as e:
            return f"FAIL {path}: invalid JSON ({e})"
        if not isinstance(data, dict):
            return f"FAIL {path}: root is not an object"
    else:
        data = {}

    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return f"FAIL {path}: mcpServers is not an object"

    servers["agents-browser"] = mcp_entry()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"OK {path}"


def _merge_zed_settings(path: Path) -> str:
    """Safely insert or update agents-browser in Zed context_servers and allow tool permissions."""
    if not path.parent.exists():
        return ""
    if path.exists():
        raw = path.read_text(encoding="utf-8", errors="replace")
        try:
            clean = _strip_jsonc(raw)
            data = json.loads(clean) if clean.strip() else {}
        except json.JSONDecodeError as e:
            return f"FAIL {path}: invalid JSON ({e})"
        if not isinstance(data, dict):
            return f"FAIL {path}: root is not an object"
    else:
        data = {}

    context_servers = data.setdefault("context_servers", {})
    if isinstance(context_servers, list):
        if "agents-browser" not in context_servers:
            context_servers.append("agents-browser")
    elif isinstance(context_servers, dict):
        context_servers["agents-browser"] = mcp_entry()

    agent_cfg = data.setdefault("agent", {})
    if isinstance(agent_cfg, dict):
        perms = agent_cfg.setdefault("tool_permissions", {})
        if isinstance(perms, dict):
            perms.setdefault("default", "allow")

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"OK {path} (Zed context_servers)"


def merge_agent_mcp() -> List[str]:
    """Insert/update the agents-browser server in all installed host MCP configs and Zed."""
    results: List[str] = []
    seen: set[str] = set()

    for target in known_host_mcp_paths():
        key = str(target.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        if target.parent.exists():
            res = _merge_mcp_server_into_file(target)
            if res:
                results.append(res)

    for zed_target in known_zed_paths():
        key = str(zed_target.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        if zed_target.parent.exists():
            res = _merge_zed_settings(zed_target)
            if res:
                results.append(res)

    return results


def get_skill_source(skill_name: str) -> Path:
    """Find skill directory in bundled package or development tree."""
    dev_path = Path(__file__).resolve().parents[2] / "skills" / skill_name
    if dev_path.exists():
        return dev_path
    bundled_path = Path(__file__).resolve().parent / "bundled" / "skills" / skill_name
    if bundled_path.exists():
        return bundled_path
    raise FileNotFoundError(f"Skill '{skill_name}' not found.")


def sync_skills() -> List[str]:
    """Copy skills to ~/.gemini/config/skills/, ~/.agents/skills/, ~/.cursor/skills/, and ~/.claude/skills/."""
    home = Path.home()
    targets = [
        home / ".gemini" / "config" / "skills",
        _agents_home() / "skills",
        home / ".cursor" / "skills",
        home / ".claude" / "skills",
    ]
    synced = []
    for skill in SKILLS:
        try:
            src = get_skill_source(skill)
        except FileNotFoundError:
            continue

        for target_base in targets:
            dest = target_base / skill
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / "SKILL.md", dest / "SKILL.md")
            synced.append(str(dest / "SKILL.md"))
    return synced


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync agents-browser rules, skills, and MCP server config.")
    parser.add_argument("--init", action="store_true", help="Auto-configure rules, skills, and MCP server in all installed IDEs")
    parser.parse_args(argv)

    rules_synced = sync_host_rules()
    always_on_synced = sync_always_on_files()
    print(f"Synced {len(rules_synced)} always-apply rules and {len(always_on_synced)} global instruction files.")

    skills_synced = sync_skills()
    print(f"Synced {len(skills_synced)} skill files:")
    for s in skills_synced:
        print(f" * {s}")

    mcp_results = merge_agent_mcp()
    print(f"\nConfigured MCP servers across {len(mcp_results)} host configs:")
    for r in mcp_results:
        print(f" * {r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
