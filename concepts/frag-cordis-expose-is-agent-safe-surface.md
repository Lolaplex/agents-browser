---
type: belief
id: frag-cordis-expose-is-agent-safe-surface
provenance: 2026-11-24 — R06 review: init/sync/install (setup + ~100MB binary download) sat on the cordis_expose surface and serve read 'read-only'
ts: 2026-11-24
---

`cordis_expose: True` means the harness treats every entry in
`commands` as an agent-callable action. Setup commands are not
agent-safe: `init` and `sync` rewrite host IDE configs, `install`
downloads a ~100MB Chrome binary. They stay argparse subparsers for
humans but are never emitted in `commands` — exposure is a smaller set
than the CLI surface, never a mirror of it.

The ruling: `side_effects` classifies what a command *does*, not what it
is named — `serve` launches a host-bound MCP server over stdio, so it is
`mutating` + `host_local`, never `read-only`. Missing metadata already
fails closed to `mutating`; a wrong label is worse than a missing one.

Open questions: whether `skills` (prints host-instructions) needs
`host_local`; whether a `cli_only` manifest should enumerate the hidden
subparsers for audit.
