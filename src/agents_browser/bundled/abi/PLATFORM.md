# ABI: Platform Discovery & Executables

## Automatic Browser Resolution

### Windows
- `%ProgramFiles%\Google\Chrome\Application\chrome.exe`
- `%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe`
- `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`
- `%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe`
- `%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`
- `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe`

### macOS
- `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge`
- `/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`
- `/Applications/Chromium.app/Contents/MacOS/Chromium`

### Linux
- `google-chrome`, `google-chrome-stable`, `chromium`, `chromium-browser`, `microsoft-edge`, `brave-browser`

## Overrides
| Variable | Purpose |
| --- | --- |
| `AGENTS_BROWSER_BIN` / `CHROME_PATH` / `BROWSER_PATH` | Explicit path to Chromium binary |
| `AGENTS_BROWSER_HEADLESS` | `1` (default) = headless; `0` / `false` / `no` = visible window |

## Launch Flags (managed)
- Always: `--remote-debugging-port=9222`, `--user-data-dir=~/.agents/browser`, `--no-first-run`, `--window-size=1280,900`
- Headless: `--headless=new`, `--disable-gpu`, `--mute-audio`, `--hide-scrollbars`

## Screenshots
- Default write dir: `~/.agents/browser/screenshots/shot-<YYYYMMDD-HHMMSS>.png`
- `browser_screenshot` returns path text + FastMCP `Image` (host displays PNG). Not a raw base64 data-URL string.
