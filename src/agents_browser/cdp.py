"""Minimal, ultra-lightweight Chrome DevTools Protocol (CDP) client in Python.
Zero-Node, Zero-Puppeteer/Playwright. Reuses local Chrome/Edge/Brave.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
import websockets


def find_browser_executable() -> str:
    """Find installed Chrome, Edge, or Brave on Windows, macOS, or Linux."""
    custom = os.environ.get("CHROME_PATH") or os.environ.get("BROWSER_PATH")
    if custom and os.path.exists(custom):
        return custom

    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:
        candidates = [
            shutil.which(b)
            for b in [
                "google-chrome",
                "google-chrome-stable",
                "chromium",
                "chromium-browser",
                "microsoft-edge",
                "brave-browser",
            ]
            if shutil.which(b)
        ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    raise RuntimeError("No Chrome/Edge/Brave browser found on system. Set CHROME_PATH.")


class CDPClient:
    """Async client communicating directly with Chrome/Edge via WebSocket CDP."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9222,
        user_data_dir: Optional[str] = None,
        headless: bool = False,
    ):
        self.host = host
        self.port = port
        self.user_data_dir = (
            Path(user_data_dir)
            if user_data_dir
            else Path.home() / ".agents" / "browser"
        )
        self.headless = headless
        self.proc: Optional[subprocess.Popen] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._msg_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._current_target_id: Optional[str] = None

    def _is_server_ready(self) -> bool:
        try:
            url = f"http://{self.host}:{self.port}/json/version"
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def ensure_browser_running(self) -> None:
        if self._is_server_ready():
            return

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        exe = find_browser_executable()

        cmd = [
            exe,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1280,900",
        ]
        if self.headless:
            cmd.extend(["--headless=new", "--disable-gpu"])

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        for _ in range(50):
            if self._is_server_ready():
                return
            time.sleep(0.1)

        raise RuntimeError(f"Failed to start browser on port {self.port}")

    def _get_targets(self) -> List[Dict[str, Any]]:
        url = f"http://{self.host}:{self.port}/json/list"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _is_ws_open(self) -> bool:
        if self.ws is None:
            return False
        if hasattr(self.ws, "state"):
            return getattr(self.ws.state, "name", "") == "OPEN"
        return getattr(self.ws, "open", True) and not getattr(self.ws, "closed", False)

    async def connect(self, target_id: Optional[str] = None) -> None:
        self.ensure_browser_running()
        targets = self._get_targets()
        page_targets = [t for t in targets if t.get("type") == "page"]

        selected = None
        if target_id:
            selected = next((t for t in targets if t.get("id") == target_id), None)

        if not selected and page_targets:
            selected = page_targets[0]

        if not selected:
            # Create a new tab if none exists
            new_url = f"http://{self.host}:{self.port}/json/new"
            req = urllib.request.Request(new_url, method="PUT")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                selected = json.loads(resp.read().decode("utf-8"))

        ws_url = selected.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError(f"Target has no webSocketDebuggerUrl: {selected}")

        if self.ws:
            await self.close_ws()

        self._current_target_id = selected.get("id")
        self.ws = await websockets.connect(ws_url, max_size=50_000_000)
        self._listener_task = asyncio.create_task(self._listen_loop())

        # Enable core domains
        await self.call("Page.enable")
        await self.call("Runtime.enable")
        await self.call("DOM.enable")

    async def _listen_loop(self) -> None:
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                req_id = msg.get("id")
                if req_id is not None and req_id in self._pending_requests:
                    fut = self._pending_requests.pop(req_id)
                    if not fut.done():
                        if "error" in msg:
                            fut.set_exception(RuntimeError(msg["error"].get("message", "CDP Error")))
                        else:
                            fut.set_result(msg.get("result", {}))
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass
        except Exception:
            pass

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 15.0) -> Any:
        if not self._is_ws_open():
            await self.connect(self._current_target_id)

        self._msg_id += 1
        msg_id = self._msg_id
        payload = {"id": msg_id, "method": method, "params": params or {}}

        fut = asyncio.get_running_loop().create_future()
        self._pending_requests[msg_id] = fut

        await self.ws.send(json.dumps(payload))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def open(self, url: str, new_tab: bool = False) -> str:
        if not url.startswith(("http://", "https://", "file://", "about:", "chrome://")):
            url = "https://" + url

        if new_tab:
            res = await self.call("Target.createTarget", {"url": url})
            target_id = res.get("targetId")
            await self.connect(target_id)
            return f"Opened {url} in new tab (Target: {target_id})"

        if not self._is_ws_open():
            await self.connect()

        await self.call("Page.navigate", {"url": url})
        await asyncio.sleep(1.0)
        await self.auto_dismiss_consent()
        title_res = await self.evaluate("document.title")
        return f"Navigated to {url} (Title: '{title_res}')"

    async def auto_dismiss_consent(self) -> Optional[str]:
        """Automatically detect and click common cookie consent and GDPR banners."""
        js_code = """
        (() => {
            const commonSelectors = [
                '#onetrust-accept-btn-handler',
                '#didomi-notice-agree-button',
                '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
                '#CybotCookiebotDialogBodyButtonAccept',
                '[data-testid="uc-accept-all-button"]',
                '#uc-btn-accept-banner',
                '.qc-cmp2-summary-buttons button:first-child',
                '.cmpboxbtn.cmpboxbtnyes',
                'button[aria-label="Alle akzeptieren"]',
                'button[aria-label="Accept all"]',
                'button[aria-label="Agree"]'
            ];

            for (const sel of commonSelectors) {
                try {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {
                        el.click();
                        return `Dismissed via selector: ${sel}`;
                    }
                } catch (e) {}
            }

            const phrases = [
                'akzeptieren und weiter',
                'alle akzeptieren',
                'alles akzeptieren',
                'zustimmen und weiter',
                'ich stimme zu',
                'einverstanden',
                'zustimmen',
                'accept all',
                'accept cookies',
                'allow all',
                'i agree',
                'got it'
            ];

            const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"], input[type="button"], input[type="submit"]'));
            for (const btn of buttons) {
                const txt = (btn.innerText || btn.value || '').trim().toLowerCase();
                if (phrases.some(p => txt === p || txt.startsWith(p))) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        btn.click();
                        return `Dismissed via text: "${txt}"`;
                    }
                }
            }
            return null;
        })()
        """
        try:
            res = await self.evaluate(js_code)
            if res:
                await asyncio.sleep(0.3)
                return str(res)
        except Exception:
            pass
        return None

    async def evaluate(self, script: str) -> Any:
        res = await self.call("Runtime.evaluate", {
            "expression": script,
            "returnByValue": True,
            "awaitPromise": True,
        })
        val = res.get("result", {})
        if "value" in val:
            return val["value"]
        if val.get("type") == "undefined":
            return None
        return val.get("description", str(val))

    async def snapshot(self) -> str:
        """Extract a structured text view of page + indexed interactive elements."""
        await self.auto_dismiss_consent()
        js_code = """
        (() => {
            window.__agents_refs = [];
            const result = {
                title: document.title,
                url: window.location.href,
                headings: [],
                interactive: [],
                textSnippet: ""
            };

            // Headings
            document.querySelectorAll('h1, h2, h3').forEach(h => {
                const text = h.innerText?.trim();
                if (text) result.headings.push(`${h.tagName}: ${text}`);
            });

            // Interactive elements
            const candidates = document.querySelectorAll(
                'a, button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [tabindex="0"]'
            );

            let refCount = 1;
            candidates.forEach(el => {
                const rect = el.getBoundingClientRect();
                const visible = rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
                if (!visible) return;

                window.__agents_refs[refCount] = el;
                const tag = el.tagName.toLowerCase();
                let desc = "";

                if (tag === 'a') {
                    desc = `Link: "${el.innerText?.trim() || el.title || el.getAttribute('aria-label') || 'link'}" -> ${el.getAttribute('href') || ''}`;
                } else if (tag === 'button' || el.getAttribute('role') === 'button') {
                    desc = `Button: "${el.innerText?.trim() || el.getAttribute('aria-label') || el.value || 'button'}"`;
                } else if (tag === 'input') {
                    const type = el.type || 'text';
                    const ph = el.placeholder ? ` placeholder="${el.placeholder}"` : '';
                    const val = el.value ? ` value="${el.value}"` : '';
                    desc = `Input[${type}]: ${ph}${val}`;
                } else if (tag === 'textarea') {
                    const ph = el.placeholder ? ` placeholder="${el.placeholder}"` : '';
                    desc = `Textarea: ${ph} (value: "${el.value || ''}")`;
                } else if (tag === 'select') {
                    const sel = el.selectedOptions[0]?.text || '';
                    desc = `Select: current="${sel}"`;
                } else {
                    desc = `${tag}: "${el.innerText?.trim() || ''}"`;
                }

                result.interactive.push(`[@${refCount}] ${desc}`);
                refCount++;
            });

            // Main body text preview
            const bodyText = document.body?.innerText || "";
            result.textSnippet = bodyText.split('\\n').map(s => s.trim()).filter(Boolean).slice(0, 20).join('\\n');

            return result;
        })()
        """
        data = await self.evaluate(js_code)
        if not isinstance(data, dict):
            return f"Failed to capture snapshot: {data}"

        lines = [
            f"# {data.get('title', 'Untitled')}",
            f"**URL**: {data.get('url')}",
            "",
        ]

        if data.get("headings"):
            lines.append("### Headings")
            for h in data["headings"]:
                lines.append(f"- {h}")
            lines.append("")

        if data.get("interactive"):
            lines.append("### Interactive Elements (use ref like '@1' or CSS selector)")
            for item in data["interactive"]:
                lines.append(f"- {item}")
            lines.append("")

        if data.get("textSnippet"):
            lines.append("### Content Summary")
            lines.append(data["textSnippet"])

        return "\n".join(lines)

    async def click(self, target: str) -> str:
        """Click element by '@1' ref index, CSS selector, or matching text."""
        js_code = f"""
        (() => {{
            const t = {json.dumps(target.strip())};
            let el = null;

            if (t.startsWith('@')) {{
                const idx = parseInt(t.slice(1), 10);
                if (window.__agents_refs && window.__agents_refs[idx]) {{
                    el = window.__agents_refs[idx];
                }}
            }}

            if (!el) {{
                try {{
                    el = document.querySelector(t);
                }} catch (e) {{}}
            }}

            if (!el) {{
                // Search by text content
                const all = document.querySelectorAll('button, a, input[type=button], input[type=submit], [role=button], span, div');
                for (const candidate of all) {{
                    if (candidate.innerText?.trim().toLowerCase() === t.toLowerCase() || candidate.value?.trim().toLowerCase() === t.toLowerCase()) {{
                        el = candidate;
                        break;
                    }}
                }}
            }}

            if (!el) {{
                return `Element not found for target: '${{t}}'`;
            }}

            el.scrollIntoView({{behavior: 'instant', block: 'center', inline: 'center'}});
            el.focus?.();
            el.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, cancelable: true}}));
            el.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, cancelable: true}}));
            el.click();
            return `Clicked element <${{el.tagName.toLowerCase()}}> ('${{t}}')`;
        }})()
        """
        res = await self.evaluate(js_code)
        await asyncio.sleep(0.5)
        return str(res)

    async def type_text(self, target: str, text: str, clear: bool = False, press_enter: bool = False) -> str:
        """Focus input/textarea and type text into it."""
        js_code = f"""
        (() => {{
            const t = {json.dumps(target.strip())};
            const textToType = {json.dumps(text)};
            const shouldClear = {json.dumps(clear)};
            const shouldEnter = {json.dumps(press_enter)};
            let el = null;

            if (t.startsWith('@')) {{
                const idx = parseInt(t.slice(1), 10);
                if (window.__agents_refs && window.__agents_refs[idx]) {{
                    el = window.__agents_refs[idx];
                }}
            }}

            if (!el) {{
                try {{
                    el = document.querySelector(t);
                }} catch (e) {{}}
            }}

            if (!el) {{
                return `Input element not found: '${{t}}'`;
            }}

            el.scrollIntoView({{behavior: 'instant', block: 'center'}});
            el.focus();

            // Append / set value and trigger input events
            const proto = (el instanceof HTMLTextAreaElement) ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;

            const newVal = shouldClear ? textToType : ((el.value || '') + textToType);
            if (setter) {{
                setter.call(el, newVal);
            }} else {{
                el.value = newVal;
            }}

            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));

            if (shouldEnter) {{
                el.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}}));
                el.dispatchEvent(new KeyboardEvent('keypress', {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}}));
                el.dispatchEvent(new KeyboardEvent('keyup', {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}}));
                if (el.form) {{
                    if (el.form.requestSubmit) {{
                        el.form.requestSubmit();
                    }} else {{
                        el.form.submit();
                    }}
                }}
            }}

            return `Typed '${{textToType}}' into <${{el.tagName.toLowerCase()}}> ('${{t}}')`;
        }})()
        """
        res = await self.evaluate(js_code)
        await asyncio.sleep(0.5)
        return str(res)

    async def screenshot(self, full_page: bool = False) -> str:
        """Capture screenshot returning base64 PNG."""
        params: Dict[str, Any] = {"format": "png"}
        if full_page:
            metrics = await self.call("Page.getLayoutMetrics")
            width = metrics.get("contentSize", {}).get("width", 1280)
            height = metrics.get("contentSize", {}).get("height", 900)
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "scale": 1,
            }

        res = await self.call("Page.captureScreenshot", params)
        return res.get("data", "")

    async def list_tabs(self) -> List[Dict[str, str]]:
        """List active browser tabs."""
        targets = self._get_targets()
        return [
            {
                "id": t.get("id", ""),
                "title": t.get("title", ""),
                "url": t.get("url", ""),
                "active": " (CURRENT)" if t.get("id") == self._current_target_id else "",
            }
            for t in targets
            if t.get("type") == "page"
        ]

    async def switch_tab(self, target_id: str) -> str:
        """Switch active CDP focus to another tab ID."""
        await self.connect(target_id)
        await self.call("Target.activateTarget", {"targetId": target_id})
        return f"Switched to tab: {target_id}"

    # --- High-Level Built-in Actions ---

    async def search(self, query: str, engine: str = "duckduckgo") -> str:
        """Execute a search and return clean structured results (Title, URL, Snippet)."""
        encoded = urllib.parse.quote_plus(query)
        if engine.lower() == "duckduckgo":
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            await self.open(url)
            await asyncio.sleep(1.0)

            js_extract = """
            (() => {
                const results = [];
                const items = document.querySelectorAll('.result');
                items.forEach(item => {
                    const titleEl = item.querySelector('.result__title a');
                    const snippetEl = item.querySelector('.result__snippet');
                    if (titleEl) {
                        results.push({
                            title: titleEl.innerText.trim(),
                            url: titleEl.getAttribute('href') || '',
                            snippet: snippetEl ? snippetEl.innerText.trim() : ''
                        });
                    }
                });
                return results.slice(0, 10);
            })()
            """
            data = await self.evaluate(js_extract)
            if isinstance(data, list) and data:
                lines = [f"### Search Results for '{query}':\n"]
                for i, r in enumerate(data, 1):
                    lines.append(f"{i}. **[{r.get('title')}]({r.get('url')})**")
                    if r.get("snippet"):
                        lines.append(f"   {r.get('snippet')}")
                return "\n".join(lines)

        # Fallback to standard open
        fallback_url = f"https://duckduckgo.com/?q={encoded}"
        await self.open(fallback_url)
        await asyncio.sleep(2.0)
        return await self.snapshot()

    async def read_article(self) -> str:
        """Extract clean Reader-Mode article markdown, removing navbars, sidebars, and ads."""
        js_code = """
        (() => {
            const clone = document.body.cloneNode(true);

            // Remove non-content elements
            const removeSelectors = [
                'nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript', 'iframe',
                '.ad', '.ads', '.advertisement', '.social-share', '.comments', '.cookie-banner',
                '#cookie', '#nav', '#menu', '#header', '#footer', '#sidebar'
            ];
            removeSelectors.forEach(sel => {
                clone.querySelectorAll(sel).forEach(el => el.remove());
            });

            // Find best content container
            const candidates = clone.querySelectorAll('article, main, .article, .post, .content, .mw-parser-output');
            const target = candidates.length > 0 ? candidates[0] : clone;

            // Extract headings and paragraphs
            const blocks = [];
            target.querySelectorAll('h1, h2, h3, h4, p, blockquote, pre, code').forEach(el => {
                const tag = el.tagName.toLowerCase();
                const text = el.innerText?.trim();
                if (!text) return;

                if (tag === 'h1') blocks.push(`\\n# ${text}\\n`);
                else if (tag === 'h2') blocks.push(`\\n## ${text}\\n`);
                else if (tag === 'h3') blocks.push(`\\n### ${text}\\n`);
                else if (tag === 'blockquote') blocks.push(`> ${text}`);
                else if (tag === 'pre') blocks.push(`\\`\\`\\`\\n${text}\\n\\`\\`\\``);
                else blocks.push(text);
            });

            return {
                title: document.title,
                url: window.location.href,
                content: blocks.join('\\n\\n')
            };
        })()
        """
        data = await self.evaluate(js_code)
        if isinstance(data, dict):
            return f"# {data.get('title', 'Article')}\n**URL**: {data.get('url')}\n\n{data.get('content', '')}"
        return str(data)

    async def scrape(self, selector: str = "body", mode: str = "text") -> str:
        """Scrape structured data from CSS selector (mode: 'text', 'table', 'links', 'html')."""
        js_code = f"""
        (() => {{
            const sel = {json.dumps(selector)};
            const mode = {json.dumps(mode.lower())};
            const el = document.querySelector(sel);
            if (!el) return `Selector '${{sel}}' not found.`;

            if (mode === 'html') {{
                return el.outerHTML;
            }}

            if (mode === 'links') {{
                const links = [];
                el.querySelectorAll('a[href]').forEach(a => {{
                    const text = a.innerText.trim() || a.title || 'link';
                    links.push(`- [${{text}}](${{a.href}})`);
                }});
                return links.join('\\n') || 'No links found.';
            }}

            if (mode === 'table') {{
                const rows = [];
                el.querySelectorAll('tr').forEach((tr, i) => {{
                    const cells = Array.from(tr.querySelectorAll('th, td')).map(c => c.innerText.trim().replace(/\\|/g, '-'));
                    if (cells.length > 0) {{
                        rows.push('| ' + cells.join(' | ') + ' |');
                        if (i === 0) {{
                            rows.push('| ' + cells.map(() => '---').join(' | ') + ' |');
                        }}
                    }}
                }});
                return rows.join('\\n') || 'No table data found.';
            }}

            return el.innerText.trim();
        }})()
        """
        res = await self.evaluate(js_code)
        return str(res)

    async def fill_form(self, fields: Dict[str, str], submit_selector: str = "") -> str:
        """Batch fill multiple form fields and optionally submit."""
        results = []
        for target, val in fields.items():
            r = await self.type_text(target, val, clear=True, press_enter=False)
            results.append(r)

        if submit_selector:
            click_res = await self.click(submit_selector)
            results.append(click_res)

        return "\n".join(results)

    async def close_ws(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            self._listener_task = None
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def close(self) -> None:
        await self.close_ws()
        if self.proc:
            self.proc.terminate()
            self.proc = None
