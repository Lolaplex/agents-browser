"""Browserless web access: stdlib search + readable-text extraction.

Fallback path for hosts without a Chrome/CDP instance. DuckDuckGo's
``html.duckduckgo.com`` endpoint is server-rendered, so a plain urllib
request plus an HTMLParser pass yields real results. ``fetch_text`` strips
script/style/nav noise and returns readable article text.
"""

from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Optional

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

_SKIP_TAGS = frozenset({
    "script", "style", "noscript", "iframe", "svg", "form", "select",
    "button", "input", "textarea", "nav", "header", "footer", "aside",
})
_TEXT_TAGS = frozenset({
    "p", "h1", "h2", "h3", "h4", "li", "blockquote", "pre", "td", "th",
    "figcaption", "dt", "dd",
})
_HEADING_LEVEL = {"h1": "#", "h2": "##", "h3": "###", "h4": "####"}


def _request(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    return urllib.request.urlopen(req, timeout=timeout).read()


class _TextExtractor(HTMLParser):
    """Collect readable text blocks, skipping nav/script/ad chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_tag: Optional[str] = None
        self.skip_same = 0
        self.in_link = False
        self.link_href = ""
        self.link_text: list[str] = []
        self.blocks: list[tuple[str, str]] = []  # (tag, text)
        self.links: list[tuple[str, str]] = []  # (text, href)
        self.title = ""
        self._in_title = False
        self._buf: list[str] = []
        self._tag: Optional[str] = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if self.skip_tag is not None:
            if tag == self.skip_tag:
                self.skip_same += 1
            return
        if tag in _SKIP_TAGS:
            self.skip_tag = tag
            self.skip_same = 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "a":
            self.in_link = True
            self.link_href = dict(attrs).get("href") or ""
            self.link_text = []
        if tag in _TEXT_TAGS:
            self._tag = tag
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if self.skip_tag is not None:
            if tag == self.skip_tag:
                self.skip_same -= 1
                if self.skip_same == 0:
                    self.skip_tag = None
            return
        if tag == "title":
            self._in_title = False
        if tag == "a" and self.in_link:
            text = " ".join("".join(self.link_text).split())
            href = self.link_href
            if text and href and href.startswith("http"):
                self.links.append((text, href))
            self.in_link = False
        if tag == self._tag and self._buf:
            text = " ".join("".join(self._buf).split())
            if text:
                self.blocks.append((self._tag, text))
            self._tag = None
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self.skip_tag is not None:
            return
        if self._in_title:
            self.title += data
        if self.in_link:
            self.link_text.append(data)
        if self._tag is not None:
            self._buf.append(data)


def fetch_text(url: str, max_chars: int = 12000, timeout: float = 20.0) -> str:
    """Fetch ``url`` and return readable markdown-ish text + link list."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    raw = _request(url, timeout=timeout)
    text = raw.decode("utf-8", errors="replace")

    # Raw JSON endpoint: no HTML blocks to extract — pretty-print instead.
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")) and "<html" not in text[:2000].lower():
        try:
            pretty = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
            return f"# {url}\n**URL**: {url}\n\n```json\n{pretty[:max_chars]}\n```"
        except ValueError:
            pass

    parser = _TextExtractor()
    parser.feed(text)

    out: list[str] = []
    size = 0
    for tag, text in parser.blocks:
        line = f"{_HEADING_LEVEL[tag]} {text}" if tag in _HEADING_LEVEL else text
        if size + len(line) > max_chars:
            break
        out.append(line)
        size += len(line)

    seen: set[str] = set()
    link_lines: list[str] = []
    for text, href in parser.links:
        if href in seen or len(link_lines) >= 30:
            continue
        seen.add(href)
        link_lines.append(f"- [{text}]({href})")

    head = f"# {parser.title.strip() or url}\n**URL**: {url}\n\n"
    body = "\n\n".join(out) or "(no readable text extracted)"
    links = "\n\n## Links\n" + "\n".join(link_lines) if link_lines else ""
    return head + body + links


class _DDGParser(HTMLParser):
    """Parse html.duckduckgo.com result rows."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict] = []
        self._in_title_a = False
        self._in_snippet = False
        self._cur: dict = {}
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        cls = " ".join(dict(attrs).get("class", "").split())
        if tag == "a" and "result__a" in cls:
            self._in_title_a = True
            self._cur = {"url": dict(attrs).get("href") or "", "title": ""}
            self._buf = []
        elif "result__snippet" in cls:
            self._in_snippet = True
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title_a:
            self._cur["title"] = " ".join("".join(self._buf).split())
            if self._cur["title"]:
                self.results.append(self._cur)
            self._in_title_a = False
        elif self._in_snippet and tag in ("a", "div", "td"):
            if self.results:
                self.results[-1]["snippet"] = " ".join(
                    "".join(self._buf).split())
            self._in_snippet = False
        if self._in_title_a or self._in_snippet:
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._in_title_a or self._in_snippet:
            self._buf.append(data)


def _unwrap_url(url: str) -> str:
    """Resolve engine-wrapped outbound links to their real target."""
    # DDG wraps links in //duckduckgo.com/l/?uddg=<urlencoded>
    if "uddg=" in url:
        return urllib.parse.unquote(url.split("uddg=", 1)[1].split("&", 1)[0])
    # Bing wraps links in /ck/a?...&u=a1<base64url>
    m = re.search(r"[?&]u=a1([^&]+)", url)
    if m:
        try:
            import base64

            return base64.urlsafe_b64decode(m.group(1) + "===").decode("utf-8", errors="replace")
        except Exception:
            return url
    return url


def _format_results(query: str, results: list[dict], max_results: int = 10) -> str:
    """Render [{title, url, snippet}] rows as markdown; shared by all engines."""
    results = results[:max_results]
    if not results:
        return f"No results for '{query}'."
    lines = [f"### Search Results for '{query}':\n"]
    for i, r in enumerate(results, 1):
        url = _unwrap_url(r.get("url", ""))
        lines.append(f"{i}. **[{r.get('title')}]({url})**")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
    return "\n".join(lines)


def ddg_search(query: str, max_results: int = 10, timeout: float = 20.0) -> str:
    """DuckDuckGo html-endpoint search without a browser."""
    encoded = urllib.parse.quote_plus(query)
    raw = _request(f"https://html.duckduckgo.com/html/?q={encoded}", timeout)
    parser = _DDGParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return _format_results(query, parser.results, max_results)


class _BingParser(HTMLParser):
    """Parse bing.com/search result rows (<li class='b_algo'>)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict] = []
        self._in_algo = False
        self._in_h2 = False
        self._in_title_a = False
        self._in_snippet = False
        self._cur: dict = {}
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        cls = " ".join(dict(attrs).get("class", "").split())
        if tag == "li" and "b_algo" in cls:
            self._in_algo = True
            self._cur = {"url": "", "title": "", "snippet": ""}
        elif self._in_algo:
            if tag == "h2":
                self._in_h2 = True
            elif tag == "a" and self._in_h2 and not self._cur.get("url"):
                self._cur["url"] = dict(attrs).get("href") or ""
                self._in_title_a = True
                self._buf = []
            elif tag == "p" and not self._cur.get("snippet"):
                self._in_snippet = True
                self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title_a:
            self._cur["title"] = " ".join("".join(self._buf).split())
            self._in_title_a = False
        elif tag == "h2" and self._in_h2:
            self._in_h2 = False
        elif tag == "p" and self._in_snippet:
            self._cur["snippet"] = " ".join("".join(self._buf).split())
            self._in_snippet = False
        elif tag == "li" and self._in_algo:
            if self._cur.get("title") and self._cur.get("url"):
                self.results.append(self._cur)
            self._in_algo = False
            self._in_h2 = False

    def handle_data(self, data: str) -> None:
        if self._in_title_a or self._in_snippet:
            self._buf.append(data)


def bing_search(query: str, max_results: int = 10, timeout: float = 20.0) -> str:
    """Bing HTML search without a browser."""
    encoded = urllib.parse.quote_plus(query)
    raw = _request(f"https://www.bing.com/search?q={encoded}&count={max_results}", timeout)
    parser = _BingParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return _format_results(query, parser.results, max_results)


def searxng_search(
    query: str,
    max_results: int = 10,
    timeout: float = 20.0,
    base_url: str = "",
) -> str:
    """SearXNG JSON API search. Self-hosted metasearch: aggregates many engines,
    no per-engine rate limit. Needs an instance URL (env AGENTS_SEARXNG_URL)."""
    base = (base_url or os.environ.get("AGENTS_SEARXNG_URL", "")).rstrip("/")
    if not base:
        return "SearXNG needs an instance URL: set AGENTS_SEARXNG_URL."
    encoded = urllib.parse.quote_plus(query)
    req = urllib.request.Request(
        f"{base}/search?q={encoded}&format=json", headers={"User-Agent": _UA}
    )
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in data.get("results", [])
    ]
    return _format_results(query, results, max_results)


def web_search(
    query: str,
    engine: str = "auto",
    max_results: int = 10,
    timeout: float = 20.0,
    searxng_url: str = "",
) -> str:
    """Multi-engine browserless search.

    ``auto`` tries searxng first when AGENTS_SEARXNG_URL is set (self-hosted
    instances have no rate limits and aggregate every other engine), then
    duckduckgo, then bing. Returns the first non-empty answer.
    """
    engine = (engine or "auto").lower()
    if engine in ("duckduckgo", "ddg"):
        return ddg_search(query, max_results, timeout)
    if engine == "bing":
        return bing_search(query, max_results, timeout)
    if engine == "searxng":
        return searxng_search(query, max_results, timeout, searxng_url)
    if engine == "auto":
        chain = []
        if searxng_url or os.environ.get("AGENTS_SEARXNG_URL"):
            chain.append(
                lambda q, n, t: searxng_search(q, n, t, searxng_url)
            )
        chain += [ddg_search, bing_search]
        for fn in chain:
            try:
                out = fn(query, max_results, timeout)
                if not out.startswith("No results"):
                    return out
            except Exception:
                continue
        return f"Error searching '{query}': all engines failed."
    return f"Unknown engine '{engine}' (duckduckgo|bing|searxng|auto)."
