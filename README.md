# Skills & MCP Servers Collection

A collection of specialized tools, instructions, and MCP (Model Context Protocol) servers for AI-assisted development and deployment.

## Projects in this Repository

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
