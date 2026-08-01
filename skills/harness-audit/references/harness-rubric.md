# Harness signal patterns

Use these as Glob/Grep starting points per layer. Not exhaustive — adapt to the stack you find (JS/TS, Python, Go, etc.). Always report the actual file paths found, not just "pattern matched."

## 1. Context Engineering
Glob: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules/**`, `docs/architecture*`, `**/*.mdc`
Grep (in found docs): mentions of project structure, module map, "do not touch", coding conventions.
Also check for: vector DB config (`chromadb`, `pinecone`, `weaviate`, `pgvector` in manifests), embedding pipeline scripts, a documented `grep`/symbol-search workflow.
Red flag (score down even if present): a single context file that reads as a dump of everything rather than a curated map — the video is explicit that good context is minimal, not maximal. There's no single universal line count that's "too long" across every project (a large monorepo legitimately needs more context than a single script), so judge relative to the project's actual size and complexity found in Step 1 rather than a fixed number. As a rough starting anchor: a freshly scaffolded starter file (see `remediation-catalog.md`) should rarely exceed ~150 lines; an established file for a small-to-medium project pushing past ~300–500 lines is worth a closer look at whether it's still curated or has become a dump.

## 2. Tools & MCP
Glob: `.mcp.json`, `mcp.json`, `**/mcp-server*/**`, `**/tools/*.{ts,py}` with tool/function-calling patterns.
Grep: `"mcpServers"`, `@modelcontextprotocol`, `tool_use`, `function_call`, `zodResponseFormat`/schema definitions for tool args.
Check permission scoping: are tools/MCP servers scoped narrowly (read-only DB access, specific repo paths) or given blanket access?

## 3. Memory & State
Glob: `docs/adr/**`, `**/DECISIONS.md`, `**/CHANGELOG.md`, `.claude/memory/**`, `**/state/*.json`
Grep: "decision log", "ADR", "historical context", references to prior sessions in AGENTS.md/CLAUDE.md instructing the agent to read/update a memory file.
Check whether memory is selective (curated decisions) vs. an unbounded append-only dump (video flags unbounded storage as its own failure mode — "переполнение контекста").

## 4. Tests & Evals
Glob: `test/**`, `tests/**`, `**/*.test.*`, `**/*.spec.*`, `e2e/**`, `evals/**`, `**/*eval*.{ts,py,yaml,json}`
Grep: `promptfoo`, `deepeval`, `langsmith`, `braintrust`, `ragas`, or hand-rolled "agent transcript assertion" style tests.
Distinguish: classic software tests (checking code output) vs. eval tests (checking agent behavior/tool-call sequence/step order) — both should exist; only having the former is a gap specific to this framework.

## 5. Observability
Grep dependencies/config for: `opentelemetry`, `langfuse`, `langsmith`, `helicone`, `sentry`, `@sentry/*`, structured logging of agent runs (trace IDs, span names per layer).
Check whether traces are granular enough to answer "did this fail at context-build, model call, tool call, or eval step?" — per-layer visibility is the bar, not just "an error was logged."

## 6. Guardrails & Approvals
Glob: `.claude/settings.json`, `.claude/settings.local.json`, `Dockerfile`, `docker-compose*.yml`, `.github/CODEOWNERS`, `.github/workflows/*.yml`
Grep: permission allow/deny lists, `sandbox`, required-reviewers/required-approval rules on workflows touching prod/migrations/deploys, explicit forbidden-path documentation.
Check for a human-approval gate specifically on high-risk actions (prod release, data deletion, migrations) — sandboxing alone without an approval step is only half this layer per the video ("Guardrails, очевидно, не гарантирует полную безопасность").
