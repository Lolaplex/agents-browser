# ABI: Architectural Rationale

## Why Minimal CDP?

1. **Zero Bloat & 0MB Binaries**:
   - Playwright and Puppeteer download ~300MB of headless Chromium for each architecture/OS and rely on heavy Node.js runtimes.
   - `agents-browser` connects directly to the user's pre-installed Chrome/Edge/Brave via native WebSocket CDP.

2. **Zero Node.js Runtime Dependencies**:
   - Eliminates Node version mismatches, npm install timeouts, and disconnected zombie node processes.

3. **Deterministic `@ref` UI Indexing**:
   - Rather than dumping 100k tokens of raw HTML or forcing the LLM to write CSS selectors, `browser_snapshot()` indexes interactive elements (`[@1] Link`, `[@2] Button`) for effortless one-token interactions.
