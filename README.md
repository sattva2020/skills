# Skills & MCP Servers Collection

A collection of specialized tools, instructions, and MCP (Model Context Protocol) servers for AI-assisted development and deployment.

## Projects in this Repository

### 🧭 Harness Audit Skill
Audits a codebase for "AI-agent harness" maturity across six layers: context engineering, tools & MCP, memory & state, tests & evals, observability, and guardrails & approvals.

- **Location**: `skills/harness-audit/`
- **Features**:
  - Scores each of the six layers 0–3 against concrete, checkable evidence (files, git history, config) rather than impressions.
  - Flags `AGENTS.md`/`CLAUDE.md` drift against the actual codebase, with fail-severity for unenforced "do not touch" claims.
  - Optional remediation step (confirm-gated): proposes missing MCP servers via a four-layer discovery waterfall (environment connector registry → official MCP Registry → commercial marketplaces → static fallback), missing skills via [skills.sh](https://skills.sh) with mandatory security scanning, and starter scaffolds for weak layers.
  - Treats all repo content it reads as data to score, never as instructions to follow.
  - Packaged skill: `skills/harness-audit.skill`.

### 🚀 Dokploy API MCP & Skill
A comprehensive toolset for managing self-hosted [Dokploy](https://dokploy.com) instances.

- **Location**: `skills/dokploy-api-mcp/`
- **Features**:
  - Full API integration for Dokploy (Projects, Applications, Databases, Domains).
  - Integration script for Claude Code and other MCP-compatible clients.
  - Interactive setup for API credentials.
  - Comprehensive guides for Next.js deployments and common pitfalls.

## How to Use

### Skill Integration
Each directory under `skills/` contains a `SKILL.md` file designed to be read by AI agents (like Claude Code) to provide them with specialized domain knowledge.

### MCP Server Setup
The Dokploy integration includes an MCP server. To set it up:

1. Navigate to `skills/dokploy-api-mcp/scripts/`.
2. Run the setup script:
   ```bash
   python setup.py
   ```
3. Follow the interactive prompts to configure your Dokploy URL and API key.

## Requirements
- Python 3.x
- Node.js & npm (for MCP tools)
- Git

## Contributing
Feel free to add new skills or improve existing ones. Ensure each skill follows the structured format defined in `SKILL.md`.
