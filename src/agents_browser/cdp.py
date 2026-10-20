"""Minimal, ultra-lightweight Chrome DevTools Protocol (CDP) client in Python.
Zero-Node, Zero-Puppeteer/Playwright. Reuses local Chrome/Edge/Brave.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import websockets


def find_browser_executable() -> str:
    """Find installed Chrome, Edge, Brave, Vivaldi, or other Chromium-based browser on Windows, macOS, or Linux."""
    custom = os.environ.get("AGENTS_BROWSER_BIN") or os.environ.get("CHROME_PATH") or os.environ.get("BROWSER_PATH")
    if custom and os.path.exists(custom):
        return custom

    if sys.platform == "win32":
        # 1. Inspect Windows Registry (HKCU and HKLM StartMenuInternet)
        try:
            import winreg

            detected_registry: List[str] = []
            for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
                try:
                    k = winreg.OpenKey(root, r"SOFTWARE\Clients\StartMenuInternet")
                    for i in range(winreg.QueryInfoKey(k)[0]):
                        sub = winreg.EnumKey(k, i)
                        try:
                            cmd_k = winreg.OpenKey(k, rf"{sub}\shell\open\command")
                            raw_val, _ = winreg.QueryValueEx(cmd_k, "")
                            exe_path = raw_val.strip().strip('"')
                            lower_exe = os.path.basename(exe_path).lower()
                            if any(c in lower_exe for c in ["chrome", "msedge", "edge", "brave", "vivaldi", "comet", "chromium", "opera"]):
                                if os.path.exists(exe_path) and exe_path not in detected_registry:
                                    detected_registry.append(exe_path)
                        except Exception:
                            pass
                except Exception:
                    pass

            if detected_registry:
                return detected_registry[0]
        except Exception:
            pass

        # 2. Check standard Windows candidate paths across environment locations
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Chromium\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Perplexity\Comet\Application\comet.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Vivaldi.app/Contents/MacOS/Vivaldi",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Arc.app/Contents/MacOS/Arc",
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
                "vivaldi",
            ]
            if shutil.which(b)
        ]

    for path in candidates:
        if path and os.path.exists(path):
            return path

    raise RuntimeError("No Chromium-based browser (Chrome, Edge, Brave, Vivaldi) found on system. Set AGENTS_BROWSER_BIN or CHROME_PATH.")


class CDPClient:
    """Async client communicating directly with Chrome/Edge via WebSocket CDP."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9222,
        user_data_dir: Optional[str] = None,
        headless: Optional[bool] = None,
    ):
        self.host = host
        self.port = port
        self.user_data_dir = (
            Path(user_data_dir)
            if user_data_dir
            else Path.home() / ".agents" / "browser"
        )
        if headless is None:
            # Headless background mode by default unless AGENTS_BROWSER_HEADLESS=0/false
            env_val = os.environ.get("AGENTS_BROWSER_HEADLESS", "1").strip().lower()
            self.headless = env_val not in ("0", "false", "no")
        else:
            self.headless = headless
        self.proc: Optional[subprocess.Popen] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._msg_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._current_target_id: Optional[str] = None
        self._event_listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.downloads_dir = self.user_data_dir / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.recordings_dir = self.user_data_dir / "recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.console_logs: List[Dict[str, Any]] = []
        self.network_logs: List[Dict[str, Any]] = []
        self._last_download_info: Optional[Dict[str, Any]] = None
        self._recording_active: bool = False
        self._recording_frames: List[str] = []
        self._recording_fps: int = 15
        self._recording_listener: Optional[Callable[[Dict[str, Any]], None]] = None

    def add_event_listener(self, method: str, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Register an event listener callback for a CDP event method name."""
        self._event_listeners.setdefault(method, []).append(listener)

    def remove_event_listener(self, method: str, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Remove an event listener callback."""
        if method in self._event_listeners and listener in self._event_listeners[method]:
            self._event_listeners[method].remove(listener)

    def _dispatch_event(self, method: str, params: Dict[str, Any]) -> None:
        """Dispatch CDP event to all registered listeners."""
        listeners = list(self._event_listeners.get(method, []))
        for listener in listeners:
            try:
                listener(params)
            except Exception:
                pass

    def _get_server_info(self) -> Optional[Dict[str, Any]]:
        try:
            url = f"http://{self.host}:{self.port}/json/version"
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass
        return None

    def _is_server_ready(self) -> bool:
        info = self._get_server_info()
        if not info:
            return False
        if self.headless is not None:
            ua = info.get("User-Agent", "")
            is_headless = "HeadlessChrome" in ua
            if is_headless != self.headless:
                return False
        return True

    def _close_existing_server(self) -> None:
        info = self._get_server_info()
        if not info:
            return
        ws_url = info.get("webSocketDebuggerUrl")
        if ws_url:
            try:
                import websockets.sync.client as ws_sync
                with ws_sync.connect(ws_url, close_timeout=1.0) as s:
                    s.send(json.dumps({"id": 1, "method": "Browser.close"}))
            except Exception:
                pass
        time.sleep(0.5)

    def ensure_browser_running(self) -> None:
        if self._is_server_ready():
            return

        # If an existing browser is running on port with wrong mode (e.g. visible window), close it
        if self._get_server_info() is not None:
            self._close_existing_server()

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
            cmd.extend([
                "--headless=new",
                "--disable-gpu",
                "--mute-audio",
                "--hide-scrollbars",
            ])

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

        # CDP Network-level ad & tracker blocking
        try:
            await self.call("Network.enable")
            await self.call("Network.setBlockedURLs", {
                "urls": [
                    "*doubleclick.net*",
                    "*googlesyndication.com*",
                    "*googleads.g.doubleclick.net*",
                    "*adservice.google.*",
                    "*youtube.com/pagead/*",
                    "*youtube.com/api/stats/ads*",
                    "*youtube.com/youtubei/v1/player/ad_break*",
                    "*youtube.com/get_midroll_info*",
                    "*adnxs.com*",
                    "*scorecardresearch.com*",
                    "*taboola.com*",
                    "*outbrain.com*",
                    "*criteo.com*",
                ]
            })
        except Exception:
            pass

        # Configure default download behavior to prevent uncontrolled downloads to OS Downloads/
        try:
            await self.call("Browser.setDownloadBehavior", {
                "behavior": "allowAndName",
                "downloadPath": str(self.downloads_dir),
                "eventsEnabled": True,
            })
        except Exception:
            try:
                await self.call("Page.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": str(self.downloads_dir),
                })
            except Exception:
                pass

        try:
            await self.call("Log.enable")
        except Exception:
            pass

        # Internal event loggers for developer audits and error capture
        def _on_console(params: Dict[str, Any]) -> None:
            raw_args = params.get("args", [])
            txt = " ".join(str(a.get("value", a.get("description", ""))) for a in raw_args)
            self.console_logs.append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "type": params.get("type", "log"),
                "text": txt
            })
            if len(self.console_logs) > 300:
                self.console_logs.pop(0)

        def _on_exception(params: Dict[str, Any]) -> None:
            details = params.get("exceptionDetails", {})
            txt = details.get("text", "")
            if not txt and "exception" in details:
                txt = details["exception"].get("description", "Uncaught Exception")
            url = details.get("url", "")
            line = details.get("lineNumber", 0)
            loc = f" ({url}:{line})" if url else ""
            self.console_logs.append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "type": "error",
                "text": f"Uncaught: {txt}{loc}"
            })
            if len(self.console_logs) > 300:
                self.console_logs.pop(0)

        def _on_log(params: Dict[str, Any]) -> None:
            entry = params.get("entry", {})
            self.console_logs.append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "type": entry.get("level", "info"),
                "text": entry.get("text", "")
            })
            if len(self.console_logs) > 300:
                self.console_logs.pop(0)

        def _on_response(params: Dict[str, Any]) -> None:
            resp = params.get("response", {})
            status = resp.get("status", 200)
            if status >= 400:
                self.network_logs.append({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "status": status,
                    "url": resp.get("url", ""),
                    "statusText": resp.get("statusText", "")
                })
                if len(self.network_logs) > 100:
                    self.network_logs.pop(0)

        def _on_download(params: Dict[str, Any]) -> None:
            self._last_download_info = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "url": params.get("url", ""),
                "suggestedFilename": params.get("suggestedFilename", ""),
                "guid": params.get("guid", ""),
            }

        self.add_event_listener("Runtime.consoleAPICalled", _on_console)
        self.add_event_listener("Runtime.exceptionThrown", _on_exception)
        self.add_event_listener("Log.entryAdded", _on_log)
        self.add_event_listener("Network.responseReceived", _on_response)
        self.add_event_listener("Page.downloadWillBegin", _on_download)

    async def _listen_loop(self) -> None:
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                method = msg.get("method")
                if method:
                    self._dispatch_event(method, msg.get("params", {}))

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

    async def set_headless(self, headless: bool) -> str:
        """Switch headless mode, restarting the browser process if mode changed."""
        if self.headless == headless and self._is_server_ready():
            mode_str = "headless (background)" if self.headless else "visible (window)"
            return f"Browser is already running in {mode_str} mode."

        # Restart browser with new headless setting
        await self.close()
        self.headless = headless
        self.ensure_browser_running()
        await self.connect()
        mode_str = "headless (background)" if self.headless else "visible (window)"
        return f"Browser restarted in {mode_str} mode."

    async def open(self, url: str, new_tab: bool = False, visible: bool = False) -> str:
        if visible and self.headless:
            await self.set_headless(False)

        if not url.startswith(("http://", "https://", "file://", "about:", "chrome://")):
            url = "https://" + url

        if new_tab:
            res = await self.call("Target.createTarget", {"url": url})
            target_id = res.get("targetId")
            await self.connect(target_id)
            return f"Opened {url} in new tab (Target: {target_id})"

        if not self._is_ws_open():
            await self.connect()

        self._last_download_info = None
        await self.call("Page.navigate", {"url": url})
        await asyncio.sleep(1.0)

        if self._last_download_info:
            dl_file = self._last_download_info.get("suggestedFilename") or "downloaded_file"
            return f"Navigated to {url}. Note: URL triggered direct download of '{dl_file}' into {self.downloads_dir}."

        await self.auto_dismiss_consent()
        title_res = await self.evaluate("document.title")
        return f"Navigated to {url} (Title: '{title_res}')"

    async def auto_dismiss_consent(self) -> Optional[str]:
        """Automatically detect and dismiss common cookie consent, GDPR overlays and backdrops."""
        js_code = """
        (() => {
            const commonSelectors = [
                '#onetrust-accept-btn-handler',
                '#onetrust-pc-btn-handler',
                '#didomi-notice-agree-button',
                '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
                '#CybotCookiebotDialogBodyButtonAccept',
                '[data-testid="uc-accept-all-button"]',
                '#uc-btn-accept-banner',
                '#accept-cookies',
                '#agree-cookie',
                '#btn-cookie-accept',
                '.qc-cmp2-summary-buttons button:first-child',
                '.cmpboxbtn.cmpboxbtnyes',
                '.cmpboxbtncustom',
                '#sp-cc-accept',
                '.fc-cta-consent',
                '.fc-primary-button',
                'button[aria-label="Alle akzeptieren"]',
                'button[aria-label="Alles akzeptieren"]',
                'button[aria-label="Zustimmen"]',
                'button[aria-label="Accept all"]',
                'button[aria-label="Agree"]',
                'button[aria-label="Allow all"]',
                'button[aria-label="Schließen"]',
                'button[aria-label="Close"]',
                '.modal-close',
                '.popup-close',
                '[data-dismiss="modal"]',
                'button.tcf-accept-all',
                'button.save-preference-btn-handler'
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
                'akzeptieren und weiter', 'alle akzeptieren', 'alles akzeptieren',
                'zustimmen und weiter', 'ich stimme zu', 'einverstanden', 'zustimmen',
                'cookies akzeptieren', 'alle zulassen', 'zulassen', 'verstanden',
                'accept all', 'accept cookies', 'allow all', 'i agree', 'got it', 'agree & continue',
                'agree and continue', 'accept all cookies', 'continue without disabling'
            ];
            const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"], input[type="button"], input[type="submit"]'));
            for (const btn of buttons) {
                const txt = (btn.innerText || btn.value || '').trim().toLowerCase();
                if (phrases.some(p => txt === p || txt.startsWith(p) || txt.includes(p))) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.top >= 0) {
                        btn.click();
                        return `Dismissed via text: "${txt}"`;
                    }
                }
            }

            try {
                const blockers = document.querySelectorAll(
                    '.fc-dialog-container, #onetrust-consent-sdk, .tcf-consent-modal, .modal-backdrop, .overlay-backdrop'
                );
                blockers.forEach(b => b.remove());
                if (document.body && document.body.style.overflow === 'hidden') {
                    document.body.style.overflow = 'auto';
                }
                if (document.documentElement && document.documentElement.style.overflow === 'hidden') {
                    document.documentElement.style.overflow = 'auto';
                }
            } catch (e) {}

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
        """Extract a structured text view of page, headings, and interactive elements with index refs (@1, @2)."""
        await self.auto_dismiss_consent()
        js_code = """
        (() => {
            if (!document.getElementById('__agents_browser_style__')) {
                const style = document.createElement('style');
                style.id = '__agents_browser_style__';
                style.textContent = `
                    .agents-target {
                        outline: 2px solid #84cc16 !important;
                        outline-offset: 2px !important;
                        box-shadow: 0 0 12px rgba(132, 204, 22, 0.6) !important;
                        transition: outline 0.15s ease, box-shadow 0.15s ease !important;
                    }
                `;
                (document.head || document.documentElement).appendChild(style);
            }

            window.__agents_refs = [];
            const result = {
                title: document.title || "Untitled",
                url: window.location.href,
                headings: [],
                interactive: [],
                textSnippet: ""
            };

            // Headings
            document.querySelectorAll('h1, h2, h3').forEach(h => {
                const text = h.innerText?.trim();
                if (text && text.length < 120) result.headings.push(`${h.tagName}: ${text}`);
            });

            // Interactive elements & rich web components
            const candidates = document.querySelectorAll(
                'a[href], button, input, select, textarea, video, iframe, [role="button"], [role="link"], [role="checkbox"], [tabindex="0"], ytd-rich-item-renderer, ytd-video-renderer, ytd-compact-video-renderer'
            );

            let refCount = 1;
            const seenEls = new Set();
            candidates.forEach(el => {
                if (seenEls.has(el)) return;

                // Resolve YouTube/WebComponent containers to actual video link
                let target = el;
                if (/^yt[d]-/.test(el.tagName.toLowerCase())) {
                    const link = el.querySelector('a#video-title-link, a#video-title, a[href*="/watch"], a[href*="/results"]') || el.querySelector('a[href]');
                    if (!link) return;
                    target = link;
                    seenEls.add(el);
                }

                const rect = target.getBoundingClientRect();
                const visible = rect.width > 0 && rect.height > 0 && window.getComputedStyle(target).visibility !== 'hidden';
                if (!visible) return;

                window.__agents_refs[refCount] = target;
                const tag = target.tagName.toLowerCase();
                let desc = "";

                if (tag === 'video') {
                    desc = `Video-Player: ${target.currentSrc || target.src || 'HTML5 Video'}`;
                } else if (tag === 'iframe') {
                    const title = target.title || target.getAttribute('aria-label') || target.src || '';
                    desc = `Frame/Video: "${title.slice(0, 60)}"`;
                } else if (tag === 'a') {
                    const text = (target.innerText || target.title || target.getAttribute('aria-label') || '').trim();
                    const href = target.href || target.getAttribute('href') || '';
                    desc = `Link: "${text.slice(0, 80)}"${href ? ' -> ' + href : ''}`;
                } else if (tag === 'button' || target.getAttribute('role') === 'button') {
                    const text = (target.innerText || target.getAttribute('aria-label') || target.value || '').trim();
                    desc = `Button: "${text.slice(0, 60)}"`;
                } else if (tag === 'input') {
                    const type = target.type || 'text';
                    const ph = target.placeholder ? ` placeholder="${target.placeholder}"` : '';
                    const val = target.value ? ` value="${target.value}"` : '';
                    desc = `Input[${type}]: ${ph}${val}`;
                } else if (tag === 'textarea') {
                    const ph = target.placeholder ? ` placeholder="${target.placeholder}"` : '';
                    desc = `Textarea: ${ph} (value: "${target.value || ''}")`;
                } else if (tag === 'select') {
                    const sel = target.selectedOptions[0]?.text || '';
                    desc = `Select: current="${sel}"`;
                } else {
                    const text = (target.innerText || target.title || target.getAttribute('aria-label') || '').trim();
                    desc = `${tag}: "${text.slice(0, 60)}"`;
                }

                result.interactive.push(`[@${refCount}] ${desc}`);
                refCount++;
            });

            // Main body text preview — filter repetitive navigation/footer boilerplate
            const bodyText = document.body?.innerText || "";
            const skipRe = /^(suchen|search|startseite|abonnements|you|verlauf|wiedergabelisten|kanal|themen|einstellungen|beschwerde|hilfe|über|presse|urheberrecht|kontakt|creator|werben|entwickler|bedingungen|datenschutz|richtlinie|sicherheit|funktionen|tests|©|\\d{4})$/i;
            result.textSnippet = bodyText.split('\\n').map(s => s.trim()).filter(Boolean).filter(s => !skipRe.test(s)).slice(0, 30).join('\\n');

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
            lines.append("### Interactive Elements (use ref like '@1', CSS selector, or visible text)")
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
                // Search by text content: prioritize actionable elements first
                const lower = t.toLowerCase();
                const linkSelectors = 'a[href], button, input[type=button], input[type=submit], [role=button], [role=link]';
                for (const sel of [linkSelectors, 'h1, h2, h3, p, span, div']) {{
                    for (const candidate of document.querySelectorAll(sel)) {{
                        const txt = (candidate.innerText || candidate.value || '').trim().toLowerCase();
                        if (!txt || txt.length > 200) continue;
                        if (txt === lower || txt.includes(lower)) {{
                            const inner = candidate.querySelector && candidate.querySelector('a[href]');
                            el = inner || candidate;
                            break;
                        }}
                    }}
                    if (el) break;
                }}
            }}

            if (!el) {{
                return `Element not found for target: '${{t}}'`;
            }}

            el.scrollIntoView({{behavior: 'smooth', block: 'center', inline: 'center'}});
            el.classList.add('agents-target');
            setTimeout(() => el.classList.remove('agents-target'), 800);

            if (el.tagName === 'VIDEO') {{
                try {{
                    if (el.paused) el.play(); else el.pause();
                }} catch (e) {{}}
            }}

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

            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            el.classList.add('agents-target');
            setTimeout(() => el.classList.remove('agents-target'), 800);
            el.focus();

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

    async def select(self, target: str, value: str) -> str:
        """Select an option in a <select> element by option value, exact text, or substring."""
        js_code = f"""
        (() => {{
            const t = {json.dumps(target.strip())};
            const val = {json.dumps(value.strip())};
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

            if (!el) return `Select element not found for target: '${{t}}'`;
            if (el.tagName !== 'SELECT') return `Element is not a <select>: <${{el.tagName.toLowerCase()}}>`;

            el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            el.classList.add('agents-target');
            setTimeout(() => el.classList.remove('agents-target'), 800);

            const wanted = val.toLowerCase();
            let opt = Array.from(el.options).find(o => o.value.toLowerCase() === wanted)
                || Array.from(el.options).find(o => o.text.trim().toLowerCase() === wanted)
                || Array.from(el.options).find(o => o.text.trim().toLowerCase().includes(wanted));

            if (!opt) {{
                const opts = Array.from(el.options).map(o => o.text.trim()).slice(0, 20).join(' | ');
                return `Option '${{val}}' not found. Available options: ${{opts}}`;
            }}

            el.value = opt.value;
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            return `Selected in '${{t}}': "${{opt.text.trim()}}" (value="${{opt.value}}")`;
        }})()
        """
        res = await self.evaluate(js_code)
        await asyncio.sleep(0.3)
        return str(res)

    async def scroll(self, direction: str = "down", amount: int = 400, target: Optional[str] = None) -> str:
        """Scroll the page smoothly in given direction ('down', 'up', 'top', 'bottom'), or scroll a target element into view."""
        if target and target.strip():
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
                    try {{ el = document.querySelector(t); }} catch (e) {{}}
                }}
                if (!el) {{
                    const lower = t.toLowerCase();
                    for (const candidate of document.querySelectorAll('h1, h2, h3, h4, section, div, p, a, button, input')) {{
                        const txt = (candidate.innerText || candidate.value || '').trim().toLowerCase();
                        if (txt && (txt === lower || txt.includes(lower))) {{
                            el = candidate;
                            break;
                        }}
                    }}
                }}
                if (!el) return `Element not found for scroll target: '${{t}}'`;
                el.scrollIntoView({{behavior: 'smooth', block: 'center', inline: 'center'}});
                return `Scrolled element <${{el.tagName.toLowerCase()}}> ('${{t}}') into view`;
            }})()
            """
            res = await self.evaluate(js_code)
            await asyncio.sleep(0.3)
            return str(res)

        js_code = f"""
        (() => {{
            const dir = {json.dumps(direction.lower())};
            const px = {int(amount)};

            if (dir === 'top') {{
                window.scrollTo({{top: 0, behavior: 'smooth'}});
                return 'Scrolled to top';
            }}
            if (dir === 'bottom') {{
                window.scrollTo({{top: document.body.scrollHeight, behavior: 'smooth'}});
                return 'Scrolled to bottom';
            }}

            const dy = dir === 'up' ? -px : px;
            window.scrollBy({{top: dy, behavior: 'smooth'}});
            return `Scrolled ${{dir}} by ${{px}}px`;
        }})()
        """
        res = await self.evaluate(js_code)
        await asyncio.sleep(0.3)
        return str(res)

    async def go_back(self) -> str:
        """Navigate back in browser history."""
        js_code = """
        (() => {
            if (window.history.length <= 1) return 'No history entry to go back to';
            window.history.back();
            return 'Navigated back';
        })()
        """
        res = await self.evaluate(js_code)
        await asyncio.sleep(0.8)
        return str(res)

    async def reload(self, ignore_cache: bool = False) -> str:
        """Reload current page."""
        await self.call("Page.reload", {"ignoreCache": ignore_cache})
        await asyncio.sleep(1.0)
        return "Page reloaded"

    async def wait_stable(self, timeout_ms: int = 8000, quiet_ms: int = 500) -> str:
        """Wait until network requests and DOM mutations settle."""
        js_code = f"""
        (() => {{
            return new Promise((resolve) => {{
                const start = Date.now();
                let lastActivity = Date.now();
                const timeout = {int(timeout_ms)};
                const quiet = {int(quiet_ms)};

                const origFetch = window.fetch;
                let fetchCount = 0;
                window.fetch = function(...args) {{
                    fetchCount++;
                    lastActivity = Date.now();
                    return origFetch.apply(this, args).finally(() => {{
                        lastActivity = Date.now();
                        fetchCount--;
                    }});
                }};

                const obs = new MutationObserver(() => {{
                    lastActivity = Date.now();
                }});
                obs.observe(document.documentElement, {{childList: true, subtree: true, attributes: true}});

                const tick = () => {{
                    const now = Date.now();
                    const isQuiet = now - lastActivity >= quiet && fetchCount === 0;
                    if (isQuiet || now - start >= timeout) {{
                        obs.disconnect();
                        window.fetch = origFetch;
                        resolve(isQuiet ? 'Page stable' : `Timeout after ${{timeout}}ms`);
                        return;
                    }}
                    setTimeout(tick, 150);
                }};
                setTimeout(tick, quiet);
            }});
        }})()
        """
        res = await self.evaluate(js_code)
        return str(res)

    async def find_in_page(self, query: str, forward: bool = True, match_case: bool = False) -> str:
        """Search text in page using window.find and return match stats."""
        js_code = f"""
        (() => {{
            const query = {json.dumps(query)};
            const forward = {json.dumps(forward)};
            const matchCase = {json.dumps(match_case)};

            if (!query) return JSON.stringify({{found: false, total: 0}});

            let total = 0;
            try {{
                const escaped = query.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&");
                const flags = matchCase ? "g" : "gi";
                const m = (document.body?.innerText || "").match(new RegExp(escaped, flags));
                total = m ? m.length : 0;
            }} catch (e) {{}}

            let found = false;
            try {{
                found = window.find(query, matchCase, !forward, true, false, false, false);
            }} catch (e) {{}}

            return JSON.stringify({{found: !!found, total: total, query: query}});
        }})()
        """
        res = await self.evaluate(js_code)
        return str(res)

    async def screenshot(self, full_page: bool = False) -> str:
        """Capture screenshot returning base64 PNG."""
        params: Dict[str, Any] = {"format": "png"}
        if full_page:
            metrics = await self.call("Page.getLayoutMetrics")
            content_size = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
            width = content_size.get("width", 1280)
            height = content_size.get("height", 900)
            params["captureBeyondViewport"] = True
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

    async def download(
        self,
        ref_or_url: str = "",
        dest_path: str = "",
        timeout: float = 60.0,
    ) -> str:
        """Download a file by clicking an element (@ref, selector, text) or triggering a URL download.

        Configures CDP download behavior to 'allowAndName' and listens to Page.downloadWillBegin / Page.downloadProgress
        until state == 'completed', returning the exact local file path.
        """
        if not self._is_ws_open():
            await self.connect()

        default_dl_dir = self.user_data_dir / "downloads"
        default_dl_dir.mkdir(parents=True, exist_ok=True)

        dest_file: Optional[Path] = None
        if dest_path.strip():
            target_p = Path(dest_path).expanduser()
            if not target_p.is_absolute():
                target_p = default_dl_dir / target_p
            if target_p.is_dir() or dest_path.endswith(("\\", "/")):
                dest_dir = target_p
                dest_dir.mkdir(parents=True, exist_ok=True)
            else:
                dest_dir = target_p.parent
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = target_p
        else:
            dest_dir = default_dl_dir

        try:
            await self.call("Browser.setDownloadBehavior", {
                "behavior": "allowAndName",
                "downloadPath": str(dest_dir),
                "eventsEnabled": True,
            })
        except Exception:
            try:
                await self.call("Page.setDownloadBehavior", {
                    "behavior": "allow",
                    "downloadPath": str(dest_dir),
                })
            except Exception:
                pass

        download_info: Dict[str, Any] = {
            "guid": None,
            "url": None,
            "suggestedFilename": None,
            "state": None,
            "filePath": None,
            "bytes": 0,
        }
        completed_event = asyncio.Event()
        error_event = asyncio.Event()

        def _on_will_begin(params: Dict[str, Any]) -> None:
            guid = params.get("guid")
            if not download_info["guid"]:
                download_info["guid"] = guid
            if guid == download_info["guid"]:
                download_info["url"] = params.get("url")
                download_info["suggestedFilename"] = params.get("suggestedFilename")

        def _on_progress(params: Dict[str, Any]) -> None:
            guid = params.get("guid")
            if not download_info["guid"]:
                download_info["guid"] = guid
            if guid == download_info["guid"]:
                state = params.get("state")
                download_info["state"] = state
                download_info["bytes"] = params.get("receivedBytes", params.get("totalBytes", 0))
                if params.get("filePath"):
                    download_info["filePath"] = params.get("filePath")
                if state == "completed":
                    completed_event.set()
                elif state == "canceled":
                    error_event.set()

        for method in ("Browser.downloadWillBegin", "Page.downloadWillBegin"):
            self.add_event_listener(method, _on_will_begin)
        for method in ("Browser.downloadProgress", "Page.downloadProgress"):
            self.add_event_listener(method, _on_progress)

        try:
            target = ref_or_url.strip()
            if target:
                if target.startswith(("http://", "https://", "data:", "file://")):
                    js_code = f"""
                    (() => {{
                        const a = document.createElement('a');
                        a.href = {json.dumps(target)};
                        a.download = '';
                        (document.body || document.documentElement).appendChild(a);
                        a.click();
                        setTimeout(() => a.remove(), 1000);
                    }})()
                    """
                    try:
                        await self.evaluate(js_code)
                    except Exception:
                        await self.call("Page.navigate", {"url": target})
                else:
                    await self.click(target)

            task_comp = asyncio.create_task(completed_event.wait())
            task_err = asyncio.create_task(error_event.wait())
            done, pending = await asyncio.wait(
                [task_comp, task_err],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout,
            )
            for p in pending:
                p.cancel()

            if not done:
                return f"Error: Download timed out after {timeout} seconds (state: {download_info.get('state', 'unknown')})."

            if error_event.is_set():
                return "Error: Download was canceled by browser."

            # Locate downloaded file
            src_file: Optional[Path] = None
            if download_info.get("filePath"):
                p = Path(download_info["filePath"])
                if p.is_file():
                    src_file = p
            if not src_file and download_info.get("guid"):
                p = dest_dir / download_info["guid"]
                if p.is_file():
                    src_file = p
            if not src_file and download_info.get("suggestedFilename"):
                p = dest_dir / download_info["suggestedFilename"]
                if p.is_file():
                    src_file = p

            if not src_file:
                files = sorted(dest_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
                if files and files[0].is_file():
                    src_file = files[0]

            if not src_file or not src_file.exists():
                return f"Error: Download reported completed, but file could not be located in {dest_dir}."

            if dest_file:
                final_path = dest_file
            else:
                sug_name = download_info.get("suggestedFilename") or src_file.name
                final_path = dest_dir / sug_name

            if src_file.resolve() != final_path.resolve():
                if final_path.exists():
                    stem = final_path.stem
                    suffix = final_path.suffix
                    final_path = dest_dir / f"{stem}_{int(time.time())}{suffix}"
                shutil.move(str(src_file), str(final_path))

            size = final_path.stat().st_size
            return (
                f"Download completed successfully.\n"
                f"- File: {final_path.name}\n"
                f"- Path: {final_path.resolve()}\n"
                f"- Size: {size:,} bytes\n"
                f"- Source: {download_info.get('url') or ref_or_url}"
            )
        finally:
            for method in ("Browser.downloadWillBegin", "Page.downloadWillBegin"):
                self.remove_event_listener(method, _on_will_begin)
            for method in ("Browser.downloadProgress", "Page.downloadProgress"):
                self.remove_event_listener(method, _on_progress)
            try:
                await self.call("Browser.setDownloadBehavior", {
                    "behavior": "allowAndName",
                    "downloadPath": str(default_dl_dir),
                    "eventsEnabled": True,
                })
            except Exception:
                pass

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Union[Dict[str, str], str]] = None,
        body: Optional[str] = None,
        json_data: Optional[Any] = None,
        timeout: float = 30.0,
    ) -> str:
        """Fast HTTP/JSON request bypassing DOM rendering, carrying browser session cookies when available."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        req_headers: Dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        if isinstance(headers, str) and headers.strip():
            try:
                headers = json.loads(headers)
            except Exception:
                headers = None
        if isinstance(headers, dict):
            for k, v in headers.items():
                req_headers[str(k)] = str(v)

        has_cookie_header = any(k.lower() == "cookie" for k in req_headers)
        if not has_cookie_header and self._is_ws_open():
            try:
                res = await self.call("Network.getCookies", {"urls": [url]})
                cookies = res.get("cookies", [])
                if cookies:
                    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies if "name" in c and "value" in c)
                    if cookie_str:
                        req_headers["Cookie"] = cookie_str
            except Exception:
                pass

        payload_bytes: Optional[bytes] = None
        if json_data is not None:
            if isinstance(json_data, str):
                try:
                    parsed = json.loads(json_data)
                    payload_bytes = json.dumps(parsed).encode("utf-8")
                except Exception:
                    payload_bytes = json_data.encode("utf-8")
            else:
                payload_bytes = json.dumps(json_data).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")
        elif body is not None:
            payload_bytes = body.encode("utf-8") if isinstance(body, str) else body

        def _do_http() -> tuple[int, Dict[str, str], bytes, Optional[str]]:
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers=req_headers,
                method=method.upper(),
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status, dict(resp.headers), resp.read(), None
            except urllib.error.HTTPError as e:
                return e.code, dict(e.headers), e.read(), None
            except Exception as e:
                return 0, {}, b"", str(e)

        status, resp_headers, raw_body, err = await asyncio.to_thread(_do_http)
        if err:
            return f"Error executing HTTP {method.upper()} to {url}: {err}"

        content_type = resp_headers.get("Content-Type") or resp_headers.get("content-type") or "text/plain"

        is_json = "json" in content_type.lower() or raw_body.strip().startswith((b"{", b"["))
        if is_json:
            try:
                parsed_json = json.loads(raw_body.decode("utf-8"))
                body_text = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            except Exception:
                body_text = raw_body.decode("utf-8", errors="replace")
        else:
            body_text = raw_body.decode("utf-8", errors="replace")

        truncated = False
        if len(body_text) > 40_000:
            body_text = body_text[:40_000] + f"\n\n[... Truncated {len(body_text) - 40_000} remaining characters ...]"
            truncated = True

        lines = [
            f"# HTTP {status} {method.upper()} {url}",
            f"- **Status**: {status}",
            f"- **Content-Type**: {content_type}",
            f"- **Size**: {len(raw_body):,} bytes" + (" (truncated in output)" if truncated else ""),
            "",
            body_text,
        ]
        return "\n".join(lines)

    async def extract_pdf(
        self,
        url_or_ref: str = "",
        save_path: str = "",
        max_pages: int = 20,
    ) -> str:
        """Directly extract PDF streams via Chrome PDF Viewer (Page.printToPDF or Blob-Extract).

        Extracts both raw PDF file to disk and structured text content with page counts.
        """
        if not self._is_ws_open():
            await self.connect()

        default_dl_dir = self.user_data_dir / "downloads"
        default_dl_dir.mkdir(parents=True, exist_ok=True)

        target = url_or_ref.strip()
        pdf_bytes: Optional[bytes] = None
        source_desc = ""

        if target and not target.startswith(("http://", "https://", "file://")):
            js_inspect = f"""
            (() => {{
                const t = {json.dumps(target)};
                let el = null;
                if (t.startsWith('@')) {{
                    const idx = parseInt(t.slice(1), 10);
                    if (window.__agents_refs && window.__agents_refs[idx]) {{
                        el = window.__agents_refs[idx];
                    }}
                }}
                if (!el) {{
                    try {{ el = document.querySelector(t); }} catch(e) {{}}
                }}
                if (!el) return null;
                return {{
                    tag: el.tagName.toLowerCase(),
                    href: el.href || el.getAttribute('href'),
                    src: el.src || el.getAttribute('src') || el.data || el.getAttribute('data')
                }};
            }})()
            """
            el_info = await self.evaluate(js_inspect)
            if isinstance(el_info, dict):
                ref_url = el_info.get("href") or el_info.get("src")
                if ref_url:
                    target = ref_url
                else:
                    dl_res = await self.download(target, dest_path=save_path)
                    if "Path: " in dl_res:
                        import re
                        m = re.search(r"Path:\s*(.+)", dl_res)
                        if m:
                            dl_file = Path(m.group(1).strip())
                            if dl_file.exists():
                                pdf_bytes = dl_file.read_bytes()
                                source_desc = f"Clicked '{url_or_ref}' -> {dl_file.name}"

        if not pdf_bytes and target and target.startswith(("http://", "https://", "file://")):
            source_desc = target
            if target.lower().endswith(".pdf") or "pdf" in target.lower():
                try:
                    req_headers = {"User-Agent": "Mozilla/5.0 Chrome/134.0.0.0 Safari/537.36"}
                    if self._is_ws_open():
                        try:
                            res = await self.call("Network.getCookies", {"urls": [target]})
                            cookies = res.get("cookies", [])
                            if cookies:
                                req_headers["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                        except Exception:
                            pass
                    req = urllib.request.Request(target, headers=req_headers)
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        raw = resp.read()
                        if raw.startswith(b"%PDF"):
                            pdf_bytes = raw
                except Exception:
                    pass

            if not pdf_bytes:
                await self.open(target)
                await asyncio.sleep(1.0)

        if not pdf_bytes:
            source_desc = await self.evaluate("window.location.href") or "current page"
            content_type = await self.evaluate("document.contentType")
            is_pdf_viewer = content_type == "application/pdf" or str(source_desc).lower().endswith(".pdf")

            if is_pdf_viewer:
                js_blob = """
                fetch(window.location.href)
                    .then(r => r.blob())
                    .then(b => new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.onerror = reject;
                        reader.readAsDataURL(b);
                    }))
                """
                try:
                    data_url = await self.evaluate(js_blob)
                    if isinstance(data_url, str) and "," in data_url:
                        b64_data = data_url.split(",", 1)[1]
                        raw = base64.b64decode(b64_data)
                        if raw.startswith(b"%PDF"):
                            pdf_bytes = raw
                except Exception:
                    pass

            if not pdf_bytes:
                try:
                    res = await self.call("Page.printToPDF", {"transferMode": "ReturnAsBase64"})
                    b64_data = res.get("data", "")
                    if b64_data:
                        pdf_bytes = base64.b64decode(b64_data)
                except Exception as e:
                    return f"Error printing page to PDF: {e}"

        if not pdf_bytes:
            return f"Error: Could not extract PDF stream from '{url_or_ref}'."

        if save_path.strip():
            out_file = Path(save_path).expanduser()
            if not out_file.is_absolute():
                out_file = default_dl_dir / out_file
            out_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            out_file = default_dl_dir / f"extracted-{stamp}.pdf"

        out_file.write_bytes(pdf_bytes)

        num_pages = 0
        pages_text: List[str] = []

        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)
            for i in range(min(num_pages, max_pages)):
                p_text = (reader.pages[i].extract_text() or "").strip()
                if p_text:
                    pages_text.append(f"--- Page {i + 1} ---\n{p_text}")
        except Exception:
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                num_pages = len(doc)
                for i in range(min(num_pages, max_pages)):
                    p_text = doc[i].get_text().strip()
                    if p_text:
                        pages_text.append(f"--- Page {i + 1} ---\n{p_text}")
            except Exception:
                pass

        text_preview = "\n\n".join(pages_text) if pages_text else "(No extractable text found in PDF / scanned images)"

        lines = [
            f"# PDF Extracted: {out_file.name}",
            f"- **Path**: {out_file.resolve()}",
            f"- **Pages**: {num_pages if num_pages > 0 else 'Unknown'}",
            f"- **Size**: {len(pdf_bytes):,} bytes",
            f"- **Source**: {source_desc}",
            "",
            f"### Extracted Text Preview (Pages 1-{min(num_pages, max_pages) if num_pages else 1}):",
            text_preview,
        ]
        return "\n".join(lines)


    async def get_styles(self, target: str, properties: Optional[List[str]] = None) -> str:
        """Inspect computed CSS styles of an element (@ref, selector, or text)."""
        props_json = json.dumps(properties) if properties else "null"
        js_code = f"""
        (() => {{
            const t = {json.dumps(target.strip())};
            let el = null;
            if (t.startsWith('@')) {{
                const idx = parseInt(t.slice(1), 10);
                if (window.__agents_refs && window.__agents_refs[idx]) el = window.__agents_refs[idx];
            }}
            if (!el) {{
                try {{ el = document.querySelector(t); }} catch (e) {{}}
            }}
            if (!el) {{
                const lower = t.toLowerCase();
                for (const candidate of document.querySelectorAll('button, a, input, h1, h2, h3, div, p, span')) {{
                    const txt = (candidate.innerText || candidate.value || '').trim().toLowerCase();
                    if (txt && (txt === lower || txt.includes(lower))) {{
                        el = candidate;
                        break;
                    }}
                }}
            }}
            if (!el) return `Error: Element not found for target: '${{t}}'`;

            const style = window.getComputedStyle(el);
            const userProps = {props_json};
            const defaultProps = [
                'font-family', 'font-size', 'font-weight', 'line-height', 'letter-spacing',
                'color', 'background-color', 'border', 'border-radius',
                'display', 'position', 'z-index', 'opacity', 'visibility',
                'margin', 'padding', 'width', 'height', 'box-shadow', 'overflow'
            ];
            const propsToRead = userProps && userProps.length > 0 ? userProps : defaultProps;

            const res = {{
                target: t,
                element: `<${{el.tagName.toLowerCase()}}${{el.id ? '#' + el.id : ''}}${{el.className ? '.' + String(el.className).trim().split(/\s+/).join('.') : ''}}>`,
                styles: {{}}
            }};

            for (const p of propsToRead) {{
                const val = style.getPropertyValue(p) || style[p] || '';
                if (val) res.styles[p] = val;
            }}

            const cssVars = {{}};
            if (el.style) {{
                for (let i = 0; i < el.style.length; i++) {{
                    const name = el.style[i];
                    if (name.startsWith('--')) {{
                        cssVars[name] = el.style.getPropertyValue(name).trim();
                    }}
                }}
            }}
            if (Object.keys(cssVars).length > 0) {{
                res.cssVariables = cssVars;
            }}

            return JSON.stringify(res, null, 2);
        }})()
        """
        res = await self.evaluate(js_code)
        return str(res)

    async def get_layout(self, target: str) -> str:
        """Inspect layout, geometry bounding box, scroll dimensions, and viewport visibility of an element."""
        js_code = f"""
        (() => {{
            const t = {json.dumps(target.strip())};
            let el = null;
            if (t.startsWith('@')) {{
                const idx = parseInt(t.slice(1), 10);
                if (window.__agents_refs && window.__agents_refs[idx]) el = window.__agents_refs[idx];
            }}
            if (!el) {{
                try {{ el = document.querySelector(t); }} catch (e) {{}}
            }}
            if (!el) {{
                const lower = t.toLowerCase();
                for (const candidate of document.querySelectorAll('button, a, input, h1, h2, h3, div, p, span, section')) {{
                    const txt = (candidate.innerText || candidate.value || '').trim().toLowerCase();
                    if (txt && (txt === lower || txt.includes(lower))) {{
                        el = candidate;
                        break;
                    }}
                }}
            }}
            if (!el) return `Error: Element not found for target: '${{t}}'`;

            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const winW = window.innerWidth;
            const winH = window.innerHeight;

            const inViewport = (
                rect.bottom > 0 &&
                rect.right > 0 &&
                rect.top < winH &&
                rect.left < winW
            );

            const isVisible = (
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                parseFloat(style.opacity || '1') > 0 &&
                rect.width > 0 &&
                rect.height > 0
            );

            const res = {{
                target: t,
                element: `<${{el.tagName.toLowerCase()}}${{el.id ? '#' + el.id : ''}}${{el.className ? '.' + String(el.className).trim().split(/\s+/).join('.') : ''}}>`,
                rect: {{
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    top: Math.round(rect.top),
                    right: Math.round(rect.right),
                    bottom: Math.round(rect.bottom),
                    left: Math.round(rect.left)
                }},
                scroll: {{
                    scrollWidth: el.scrollWidth,
                    scrollHeight: el.scrollHeight,
                    scrollTop: el.scrollTop,
                    scrollLeft: el.scrollLeft
                }},
                client: {{
                    clientWidth: el.clientWidth,
                    clientHeight: el.clientHeight
                }},
                viewport: {{
                    width: winW,
                    height: winH,
                    pageScrollX: Math.round(window.scrollX),
                    pageScrollY: Math.round(window.scrollY),
                    docScrollWidth: document.documentElement.scrollWidth,
                    docScrollHeight: document.documentElement.scrollHeight
                }},
                isVisible: isVisible,
                inViewport: inViewport,
                overflowsViewportHorizontal: rect.right > winW || rect.left < 0
            }};
            return JSON.stringify(res, null, 2);
        }})()
        """
        res = await self.evaluate(js_code)
        return str(res)

    async def inspect(self, target: str) -> str:
        """Inspect all aspects of an element in one call: Tag, Attributes, Text, Geometry, Typography, Colors, Box-Model."""
        js_code = f"""
        (() => {{
            const t = {json.dumps(target.strip())};
            let el = null;
            if (t.startsWith('@')) {{
                const idx = parseInt(t.slice(1), 10);
                if (window.__agents_refs && window.__agents_refs[idx]) el = window.__agents_refs[idx];
            }}
            if (!el) {{
                try {{ el = document.querySelector(t); }} catch (e) {{}}
            }}
            if (!el) {{
                const lower = t.toLowerCase();
                for (const candidate of document.querySelectorAll('button, a, input, h1, h2, h3, div, p, span, section')) {{
                    const txt = (candidate.innerText || candidate.value || '').trim().toLowerCase();
                    if (txt && (txt === lower || txt.includes(lower))) {{
                        el = candidate;
                        break;
                    }}
                }}
            }}
            if (!el) return `Error: Element not found for target: '${{t}}'`;

            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const winW = window.innerWidth;
            const winH = window.innerHeight;

            const attrs = {{}};
            for (let i = 0; i < el.attributes.length; i++) {{
                const a = el.attributes[i];
                attrs[a.name] = a.value;
            }}

            const parentInfo = el.parentElement ? `<${{el.parentElement.tagName.toLowerCase()}}${{el.parentElement.id ? '#' + el.parentElement.id : ''}}${{el.parentElement.className ? '.' + String(el.parentElement.className).trim().split(/\s+/).slice(0, 2).join('.') : ''}}>` : 'none';
            const childTags = Array.from(el.children).slice(0, 5).map(c => c.tagName.toLowerCase());

            const isVisible = (
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                parseFloat(style.opacity || '1') > 0 &&
                rect.width > 0 &&
                rect.height > 0
            );

            const inViewport = (
                rect.bottom > 0 &&
                rect.right > 0 &&
                rect.top < winH &&
                rect.left < winW
            );

            let txt = (el.innerText || el.value || '').trim();
            if (txt.length > 200) txt = txt.slice(0, 200) + '...';

            return JSON.stringify({{
                target: t,
                element: `<${{el.tagName.toLowerCase()}}${{el.id ? '#' + el.id : ''}}${{el.className ? '.' + String(el.className).trim().split(/\s+/).join('.') : ''}}>`,
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                classes: el.className ? String(el.className).trim().split(/\s+/) : [],
                text: txt || null,
                attributes: attrs,
                parent: parentInfo,
                childrenCount: el.children.length,
                childrenPreview: childTags,
                geometry: {{
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    isVisible: isVisible,
                    inViewport: inViewport
                }},
                typography: {{
                    fontFamily: style.fontFamily,
                    fontSize: style.fontSize,
                    fontWeight: style.fontWeight,
                    lineHeight: style.lineHeight,
                    color: style.color
                }},
                boxModel: {{
                    backgroundColor: style.backgroundColor,
                    border: style.border,
                    borderRadius: style.borderRadius,
                    padding: `${{style.paddingTop}} ${{style.paddingRight}} ${{style.paddingBottom}} ${{style.paddingLeft}}`,
                    margin: `${{style.marginTop}} ${{style.marginRight}} ${{style.marginBottom}} ${{style.marginLeft}}`,
                    display: style.display,
                    position: style.position,
                    zIndex: style.zIndex
                }}
            }}, null, 2);
        }})()
        """
        res = await self.evaluate(js_code)
        return str(res)

    async def audit(self) -> str:
        """Run an automated developer audit of current page for console errors, layout overflow, broken media, and fonts."""
        js_code = """
        (() => {
            const winW = window.innerWidth;
            const docW = document.documentElement.scrollWidth;
            const hasHorizontalOverflow = docW > winW + 2;

            const overflowElements = [];
            if (hasHorizontalOverflow) {
                for (const el of document.querySelectorAll('*')) {
                    if (el.offsetParent === null) continue;
                    const r = el.getBoundingClientRect();
                    if (r.right > winW + 2) {
                        const tag = `<${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${el.className ? '.' + String(el.className).trim().split(/\s+/).slice(0, 2).join('.') : ''}>`;
                        overflowElements.push({ element: tag, right: Math.round(r.right), excessPx: Math.round(r.right - winW) });
                        if (overflowElements.length >= 5) break;
                    }
                }
            }

            const brokenImages = [];
            for (const img of document.images) {
                if (img.complete && img.naturalWidth === 0) {
                    brokenImages.push(img.src || img.getAttribute('src') || 'unknown image');
                    if (brokenImages.length >= 5) break;
                }
            }

            const fonts = Array.from(document.fonts || []).map(f => `${f.family} (${f.status})`).slice(0, 10);

            return JSON.stringify({
                title: document.title,
                url: window.location.href,
                viewport: { width: winW, height: window.innerHeight },
                horizontalOverflow: hasHorizontalOverflow,
                docScrollWidth: docW,
                overflowElements: overflowElements,
                brokenImages: brokenImages,
                fonts: fonts
            });
        })()
        """
        dom_audit_raw = await self.evaluate(js_code)
        try:
            dom_data = json.loads(dom_audit_raw)
        except Exception:
            dom_data = {}

        err_logs = [log for log in self.console_logs if log.get("type") in ("error", "warning")][-10:]
        net_errs = self.network_logs[-10:]

        lines = [
            f"# Page Audit: {dom_data.get('title', 'Page')}",
            f"**URL:** `{dom_data.get('url', '')}` | **Viewport:** `{dom_data.get('viewport', {}).get('width', 0)}x{dom_data.get('viewport', {}).get('height', 0)}`",
            "",
            "### Findings:"
        ]

        issues_count = 0

        # 1. Overflow
        if dom_data.get("horizontalOverflow"):
            issues_count += 1
            excess = dom_data.get("docScrollWidth", 0) - dom_data.get("viewport", {}).get("width", 0)
            lines.append(f"- ⚠️ **Horizontal Layout Overflow**: Document is `{dom_data.get('docScrollWidth')}px` wide (+{excess}px overflow)!")
            for el in dom_data.get("overflowElements", []):
                lines.append(f"  - Offending element: `{el['element']}` (right: {el['right']}px, +{el['excessPx']}px)")
        else:
            lines.append("- ✅ **Layout**: No horizontal overflow detected.")

        # 2. Console Errors
        if err_logs:
            issues_count += len(err_logs)
            lines.append(f"- ❌ **Console Errors / Warnings** ({len(err_logs)}):")
            for err in err_logs:
                lines.append(f"  - `[{err['type'].upper()}]` {err['text']}")
        else:
            lines.append("- ✅ **Console**: 0 errors or warnings captured.")

        # 3. Broken Images
        broken = dom_data.get("brokenImages", [])
        if broken:
            issues_count += len(broken)
            lines.append(f"- ⚠️ **Broken Images** ({len(broken)}):")
            for b in broken:
                lines.append(f"  - `{b}`")
        else:
            lines.append("- ✅ **Media**: All images loaded successfully.")

        # 4. Network Failures
        if net_errs:
            issues_count += len(net_errs)
            lines.append(f"- ❌ **Failed Network Requests** ({len(net_errs)}):")
            for ne in net_errs:
                lines.append(f"  - HTTP {ne.get('status')}: `{ne.get('url')}`")
        else:
            lines.append("- ✅ **Network**: No failed 4xx/5xx requests.")

        # 5. Fonts
        fonts = dom_data.get("fonts", [])
        if fonts:
            lines.append(f"- ℹ️ **Fonts Active**: {', '.join(fonts)}")

        lines.append("")
        if issues_count == 0:
            lines.append("**Status:** ✅ Page is clean and healthy. No issues detected.")
        else:
            lines.append(f"**Status:** ⚠️ Found {issues_count} potential issue(s) requiring attention.")

        return "\n".join(lines)

    async def get_logs(self, log_type: str = "all", limit: int = 50, clear: bool = False) -> str:
        """Return buffered console logs, runtime errors, and failed network requests."""
        lt = log_type.lower()
        items = []

        if lt in ("all", "console", "error"):
            for entry in self.console_logs:
                if lt == "error" and entry.get("type") != "error":
                    continue
                items.append(f"[{entry['ts']}] [CONSOLE:{entry['type'].upper()}] {entry['text']}")

        if lt in ("all", "network", "error"):
            for net in self.network_logs:
                items.append(f"[{net['ts']}] [NETWORK:{net['status']}] {net['url']} ({net.get('statusText', '')})")

        if clear:
            self.console_logs.clear()
            self.network_logs.clear()

        if not items:
            return f"No logs captured for filter '{log_type}'."

        trimmed = items[-int(limit):]
        return "\n".join(trimmed)

    async def set_viewport(
        self,
        width: int = 1280,
        height: int = 900,
        preset: str = "",
        mobile: bool = False,
        device_scale_factor: float = 1.0,
    ) -> str:
        """Set browser viewport dimensions or select a preset ('mobile', 'tablet', 'desktop', 'fhd')."""
        p = preset.strip().lower()
        if p in ("mobile", "iphone", "phone"):
            width, height, mobile, device_scale_factor = 390, 844, True, 3.0
        elif p in ("tablet", "ipad"):
            width, height, mobile, device_scale_factor = 820, 1180, True, 2.0
        elif p in ("desktop", "laptop"):
            width, height, mobile, device_scale_factor = 1440, 900, False, 1.0
        elif p in ("fhd", "desktop-wide"):
            width, height, mobile, device_scale_factor = 1920, 1080, False, 1.0

        await self.call("Emulation.setDeviceMetricsOverride", {
            "width": int(width),
            "height": int(height),
            "deviceScaleFactor": float(device_scale_factor),
            "mobile": bool(mobile),
        })
        return f"Viewport set to {width}x{height} (preset='{preset or 'custom'}', mobile={mobile}, dsf={device_scale_factor})"

    async def record_start(self, fps: int = 15) -> str:
        """Start capturing a screen recording stream via CDP screencast."""
        if self._recording_active:
            return "Screen recording is already active. Call `browser_record_stop` to finish and save."

        self._recording_active = True
        self._recording_frames = []
        self._recording_fps = max(1, min(30, int(fps)))

        def _on_frame(params: Dict[str, Any]) -> None:
            if self._recording_active:
                data = params.get("data")
                if data:
                    self._recording_frames.append(data)
                sess_id = params.get("sessionId")
                if sess_id is not None:
                    asyncio.create_task(self.call("Page.screencastFrameAck", {"sessionId": sess_id}))

        self._recording_listener = _on_frame
        self.add_event_listener("Page.screencastFrame", _on_frame)
        await self.call("Page.startScreencast", {
            "format": "jpeg",
            "quality": 80,
            "everyNthFrame": 1,
        })
        return f"Screen recording started at {self._recording_fps} FPS. Execute actions, then call `browser_record_stop` to export."

    async def record_stop(self, path: str = "") -> str:
        """Stop screen recording and encode frames to MP4 video (or GIF)."""
        if not self._recording_active:
            return "No active screen recording to stop."

        self._recording_active = False
        try:
            await self.call("Page.stopScreencast")
        except Exception:
            pass

        if self._recording_listener:
            self.remove_event_listener("Page.screencastFrame", self._recording_listener)
            self._recording_listener = None

        frames = list(self._recording_frames)
        self._recording_frames = []

        if not frames:
            return "Screen recording stopped, but no frames were captured."

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if path.strip():
            out_path = Path(path).expanduser()
            if not out_path.is_absolute():
                out_path = self.recordings_dir / out_path.name
        else:
            out_path = self.recordings_dir / f"rec-{stamp}.mp4"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = shutil.which("ffmpeg")

        if ffmpeg_bin:
            is_gif = out_path.suffix.lower() == ".gif"
            cmd = [
                ffmpeg_bin,
                "-y",
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "-framerate", str(self._recording_fps),
                "-i", "-",
            ]
            if is_gif:
                cmd.extend(["-vf", "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"])
            else:
                cmd.extend([
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    "-movflags", "+faststart",
                ])
            cmd.append(str(out_path))

            frames_to_encode = list(frames)
            min_frames = max(10, self._recording_fps)
            if len(frames_to_encode) < min_frames:
                last_frame = frames_to_encode[-1]
                while len(frames_to_encode) < min_frames:
                    frames_to_encode.append(last_frame)

            try:
                input_bytes = b"".join(base64.b64decode(f) for f in frames_to_encode)
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                _, stderr = proc.communicate(input=input_bytes, timeout=15.0)
            except Exception:
                pass

            if out_path.exists() and out_path.stat().st_size > 0:
                return f"Screen recording saved: {out_path} ({len(frames)} frames, {out_path.stat().st_size} bytes)"

        # Fallback if ffmpeg is missing or failed: save frames to a folder
        frames_dir = self.recordings_dir / f"frames-{stamp}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(frames):
            (frames_dir / f"frame_{i:04d}.jpg").write_bytes(base64.b64decode(f))
        return f"Screen recording frames saved ({len(frames)} frames) to: {frames_dir} (Install ffmpeg to enable direct MP4 export)"

    async def record(self, duration_sec: float = 5.0, fps: int = 15, path: str = "") -> str:
        """One-shot helper: record screen for `duration_sec` seconds and export to MP4."""
        start_msg = await self.record_start(fps=fps)
        if "already active" in start_msg:
            return start_msg
        await asyncio.sleep(float(duration_sec))
        return await self.record_stop(path=path)

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

