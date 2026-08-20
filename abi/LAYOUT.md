# ABI: Filesystem Layout & Storage

## Directory Structure
- **Persistent Profile**: `~/.agents/browser/`
  - Stores cookies, session tokens, localStorage, and login state across agent turns.
- **Skills**: `~/.gemini/config/skills/` and `~/.agents/skills/`
  - Synced automatically via `python -m agents_browser sync`.
- **Debugging Port**: `127.0.0.1:9222` (default). Configurable via environment or client parameters.
