# Remediation catalog

Concrete actions per layer. Always confirm with the user before writing/installing anything from here (see SKILL.md Step 6.5). Everything below is a starting template — adapt names, paths and stack-specific syntax to what Step 1 actually found in the project, never paste it verbatim.

Before using any raw scaffold below, SKILL.md Step 6.3 says to check skills.sh first (`npx skills search "<query>"`) for a maintained skill that already covers the layer — these templates are the fallback when no good match exists there, not the default.

## Tools & MCP — four-layer discovery waterfall

Try each layer in order; stop at the first one that produces a good, evidence-matched candidate. Search using the service names found in SKILL.md Step 6.2.1 (e.g. "github", "postgres", "stripe", "slack").

### Layer A — environment connector registry (highest trust, narrowest availability)
If `SearchMcpRegistry` / `SuggestConnectors` / `ListConnectors` are available (Cowork/claude.ai), use them first — product-curated, one-click enable, always current. Not present in plain Claude Code or other harnesses; skip straight to Layer B there.

### Layer B — official MCP Registry (open, protocol-level aggregator)
`https://registry.modelcontextprotocol.io` — an open catalog + OpenAPI-spec API maintained by the MCP steering group (Anthropic, PulseMCP, GitHub). This is the closest thing to a single canonical aggregator for the whole ecosystem, and the right first stop once Layer A isn't available.
- Query it with `WebFetch`/`WebSearch` against the registry's API/site — e.g. fetch `https://registry.modelcontextprotocol.io/v0/servers?search=<service-name>` (check current API shape in `https://registry.modelcontextprotocol.io/docs` if the exact path has moved — it's in preview and can change).
- Status caveat: **preview**, breaking changes possible, listings are self-reported by maintainers with community moderation — a hit means "registered," not "vetted." Still apply the trust check in SKILL.md Step 6.2.3 before proposing it.

### Layer C — community/commercial marketplaces (broadest coverage today)
Use when Layer B has no match. These pre-date the official registry and currently index more servers, with their own curation layers:
- [Smithery](https://smithery.ai) — hosted MCP servers with one-click deploy.
- [Glama](https://glama.ai/mcp/servers) — directory with quality/security signals per server.
- [PulseMCP](https://www.pulsemcp.com/servers) — large directory (tens of thousands of entries), supports filtering to `official-providers` — prefer that classification over unbadged community listings for the same service when both exist.
Query via `WebFetch`/`WebSearch` against these sites' search pages (no stable public API for all three — treat this as best-effort discovery, not a guaranteed structured query like Layer B).

### Layer D — standard reference MCP servers (last resort, always available, no network needed)
Only Anthropic's small set of reference implementations. Verify current package names before proposing, since the ecosystem moves fast — these examples may drift out of date faster than the file itself.

```jsonc
// .mcp.json — only include entries the codebase evidence actually supports
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "<project-root>"]
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "<project-root>"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "<from user's existing secret store, never hardcode>" }
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "<connection-string-env-var>"]
    }
  }
}
```

Scope every server as narrowly as the project needs — e.g. `filesystem` scoped to the repo root, not `/`; a DB server pointed at a read-only role where one exists. Explain to the user what each grants access to before writing the file. Never inline a real credential — reference the env var the project already uses.

## Context Engineering — starter `AGENTS.md` / `CLAUDE.md`

```md
# Project context for AI agents

## What this project is
<one paragraph, pulled from README/package description found in Step 1>

## Structure
<real top-level folders found by Step 1, one line each on what lives there>

## Commands
- Install: `<real command from package manifest>`
- Test: `<real test command found>`
- Build: `<real build command found>`

## Conventions
<pull from any existing lint config / style guide found; otherwise leave a TODO for the user, don't invent conventions>

## Do not touch
<leave as a TODO for the user to fill in — this skill should not guess forbidden paths>
```

Keep it short — this is a *starter*, so ~150 lines is already generous for a fresh file. Per the source video, a good context file is minimal and curated, not a dump. See `harness-rubric.md`'s Context Engineering section for how the length bar shifts once the file is established and the project has grown (the anchor there is relative to project size, not a fixed number).

## Memory & State — starter decision log

```md
# ADR 0001: Record architecture decisions

## Status
Accepted

## Context
<why this project needs a decision log — filled by the user on first real decision>

## Decision
We will record significant architectural decisions in `docs/adr/NNNN-title.md`, one file per decision, numbered sequentially.

## Consequences
Future agent sessions and contributors can read prior decisions instead of re-deriving them from code archaeology.
```

## Tests & Evals — minimal eval starter

If the project has no eval layer at all, propose the smallest possible starting point rather than a full framework:

```md
# evals/smoke.md — first agent-behavior eval

**Task**: <a real, small task from this project, e.g. "add a field to the X model">
**Expected tool sequence**: <e.g. read schema file → edit model → run migration command>
**Pass condition**: agent calls the tools in a sensible order and does not skip the migration step, regardless of which model executed it.
```

Only propose a heavier framework (promptfoo, deepeval, etc.) if the project's scale and existing test sophistication justify it — match harness complexity to project complexity, per the source video.

## Observability — minimal starter

For a project with no agent-run tracing at all, the smallest viable step is structured logging around tool calls, not a full APM integration:

```md
Wrap tool/MCP calls with a single structured log line per call:
{ "ts": ..., "layer": "tools_mcp", "tool": "<name>", "duration_ms": ..., "ok": true|false }
```
Suggest a real tracing backend (OpenTelemetry, Langfuse, LangSmith) only once the project has enough call volume/complexity that a plain log file stops being enough to debug from.

## Guardrails & Approvals — starter permission scope

```jsonc
// .claude/settings.json — starter, tighten based on what Step 1 found as sensitive paths
{
  "permissions": {
    "allow": ["Read(**)", "Edit(src/**)", "Bash(npm test)", "Bash(npm run build)"],
    "deny": ["Read(.env*)", "Edit(.github/workflows/**)", "Bash(rm -rf *)"]
  }
}
```

If CI exists and touches deploy/migration paths, also propose a required-reviewers rule on those specific workflow files rather than the whole repo — narrower approval gates get adopted, blanket ones get bypassed.
