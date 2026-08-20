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
2. **First Tool Invocation**: CDP client verifies if `http://127.0.0.1:9222/json/version` is alive.
3. **Auto-Spawn**: If offline, spawns system Chrome/Edge with `--remote-debugging-port=9222` and persistent user profile (`~/.agents/browser`).
4. **WebSocket Connect**: Connects to the active page target via `ws://127.0.0.1:9222/devtools/page/...`.
5. **Execution**: CDP domains `Page`, `Runtime`, `DOM`, `Input` execute operations with timeout safety.
