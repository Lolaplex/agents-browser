# ABI: MCP Protocol & Server Lifecycle

## Server Metadata
- **Protocol**: Model Context Protocol (MCP) over `stdio`
- **Identifier**: `agents-browser`
- **Transport**: JSON-RPC standard input/output

## Configuration Example
```json
{
  "mcpServers": {
    "agents-browser": {
      "command": "python",
      "args": ["-m", "agents_browser"]
    }
  }
}
```

## Lifecycle Flow
1. **Init**: FastMCP server starts on `stdio`.
2. **First Tool Invocation**: CDP client verifies if `http://127.0.0.1:9222/json/version` is alive and matches the requested mode (headless vs visible via User-Agent `HeadlessChrome`).
3. **Auto-Spawn**: If offline (or wrong mode), spawns system Chrome/Edge with `--remote-debugging-port=9222`, persistent user profile (`~/.agents/browser`), and **`--headless=new` by default**.
4. **WebSocket Connect**: Connects to the active page target via `ws://127.0.0.1:9222/devtools/page/...`.
5. **Execution**: CDP domains `Page`, `Runtime`, `DOM`, `Network` execute operations with timeout safety.

## Headless Policy
- Default: headless background automation. Env default `AGENTS_BROWSER_HEADLESS=1`.
- Visible CDP window: `browser_open(url, visible=True)` or `browser_set_headless(False)` (restarts the process).
- OS default browser (no CDP): `browser_system_open(url)` — only when the human asks to open in their personal desktop browser.
