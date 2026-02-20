# Dokploy MCP Server — 67 Tools Reference

Official MCP server: `@ahdev/dokploy-mcp` (repo: [Dokploy/mcp](https://github.com/Dokploy/mcp))

## Setup

### Claude Code (`~/.claude/mcp.json`)

```json
{
  "mcpServers": {
    "dokploy": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@ahdev/dokploy-mcp"],
      "env": {
        "DOKPLOY_URL": "https://dokploy.example.com/api",
        "DOKPLOY_API_KEY": "<your-token>"
      }
    }
  }
}
```

**Windows:** use `"command": "cmd", "args": ["/c", "npx", "-y", "@ahdev/dokploy-mcp"]`
**macOS/Linux:** use `"command": "npx", "args": ["-y", "@ahdev/dokploy-mcp"]`

Alternative runtimes: `bunx`, `deno`, Docker.

### Transport Modes

- **stdio** (default) — for CLI and desktop apps
- **HTTP** — Streamable HTTP (MCP 2025-03-26) + Legacy SSE (MCP 2024-11-05)

## Tool Annotations

All tools have semantic annotations:

| Annotation | Meaning |
|------------|---------|
| `readOnlyHint: true` | Safe read operation, no side effects |
| `destructiveHint: true` | Modifies or deletes resources |
| `destructiveHint: false` | Creates new resources |
| `idempotentHint: true` | Safe to repeat |
| `openWorldHint: true` | Calls external Dokploy API |

## When to Use MCP vs curl

| Scenario | Use MCP | Use curl/API |
|----------|---------|--------------|
| AI agent managing deployments | Yes | — |
| Claude Code interactive session | Yes | Fallback |
| CI/CD pipeline scripts | — | Yes |
| Automation without AI | — | Yes |
| Complex multi-step workflows | Yes | — |

**MCP advantages:** No need to construct tRPC URLs, handle URL encoding, or parse nested response wrappers. The MCP tools handle all of this internally.

---

## Project Management (6 tools)

| Tool | Description | Required | Optional |
|------|-------------|----------|----------|
| `project-all` | List all projects | — | — |
| `project-one` | Get project by ID | `projectId` | — |
| `project-create` | Create project | `name` | `description`, `env` |
| `project-update` | Update project | `projectId` | `name`, `description`, `env` |
| `project-duplicate` | Clone project | `sourceProjectId`, `name` | `description`, `includeServices`, `selectedServices` |
| `project-remove` | Delete project | `projectId` | — |

### Examples

```
// List all projects
Use tool: project-all

// Create project
Use tool: project-create with name="AI Ads Agent"

// Duplicate with services
Use tool: project-duplicate with sourceProjectId="xxx" name="staging" includeServices=true
```

## Application Management (26 tools)

### Core Operations

| Tool | Description | Required | Optional |
|------|-------------|----------|----------|
| `application-one` | Get app details + status | `applicationId` | — |
| `application-create` | Create new app | `name`, `projectId` | `appName`, `description`, `serverId` |
| `application-update` | Update app config | `applicationId` | 60+ fields (see API reference) |
| `application-delete` | Delete app | `applicationId` | — |
| `application-move` | Move app to another project | `applicationId`, `targetProjectId` | — |

### Deployment & Lifecycle

| Tool | Description | Required |
|------|-------------|----------|
| `application-deploy` | Trigger deployment | `applicationId` |
| `application-redeploy` | Force redeploy | `applicationId` |
| `application-start` | Start stopped app | `applicationId` |
| `application-stop` | Stop running app | `applicationId` |
| `application-cancelDeployment` | Cancel active build | `applicationId` |
| `application-reload` | Reload app | `applicationId`, `appName` |
| `application-markRunning` | Set status to running | `applicationId` |

### Configuration

| Tool | Description | Required | Optional |
|------|-------------|----------|----------|
| `application-saveBuildType` | Set build method | `applicationId`, `buildType` | `dockerContextPath`, `dockerBuildStage`, `herokuVersion` |
| `application-saveEnvironment` | Set env vars | `applicationId` | `env`, `buildArgs` |

**buildType values:** `dockerfile`, `heroku_buildpacks`, `paketo_buildpacks`, `nixpacks`, `static`, `railpack`

### Git Providers

| Tool | Description | Required |
|------|-------------|----------|
| `application-saveGithubProvider` | Connect GitHub | `applicationId`, `owner`, `githubId`, `enableSubmodules` |
| `application-saveGitlabProvider` | Connect GitLab | `applicationId`, `enableSubmodules` |
| `application-saveBitbucketProvider` | Connect Bitbucket | `applicationId` |
| `application-saveGiteaProvider` | Connect Gitea | `applicationId` |
| `application-saveGitProvider` | Generic git URL | `applicationId` |
| `application-saveDockerProvider` | Docker image | `applicationId` |
| `application-disconnectGitProvider` | Remove git connection | `applicationId` |

### Monitoring & Traefik

| Tool | Description | Required |
|------|-------------|----------|
| `application-readAppMonitoring` | Get monitoring metrics | `applicationId` |
| `application-readTraefikConfig` | Read routing config | `applicationId` |
| `application-updateTraefikConfig` | Modify routing | `applicationId` |

### Utilities

| Tool | Description | Required |
|------|-------------|----------|
| `application-refreshToken` | Regenerate webhook token | `applicationId` |
| `application-cleanQueues` | Clear deployment queues | `applicationId` |

### Typical Deployment Workflow (MCP)

```
1. application-one            → check current status
2. application-saveEnvironment → set/update env vars
3. application-saveBuildType   → configure Dockerfile build
4. application-deploy          → trigger deployment
5. application-one            → poll until status = "done"
6. (verify health via curl)
```

## Domain Management (9 tools)

| Tool | Description | Required | Optional |
|------|-------------|----------|----------|
| `domain-byApplicationId` | List app domains | `applicationId` | — |
| `domain-byComposeId` | List compose domains | `composeId` | — |
| `domain-one` | Get domain details | `domainId` | — |
| `domain-create` | Add domain | `name` | SSL, routing config |
| `domain-update` | Modify domain | `domainId` | config fields |
| `domain-delete` | Remove domain | `domainId` | — |
| `domain-validateDomain` | Verify DNS | `domain` | — |
| `domain-generateDomain` | Auto-generate subdomain | `projectId` | — |
| `domain-canGenerateTraefikMeDomains` | Check traefik.me support | — | — |

## PostgreSQL Database (13 tools)

| Tool | Description | Required | Optional |
|------|-------------|----------|----------|
| `postgres-create` | Create DB instance | `name`, `projectId` | `description`, `serverId`, `password`, `rootPassword` |
| `postgres-one` | Get DB details | `postgresId` | — |
| `postgres-update` | Modify DB config | `postgresId` | config fields |
| `postgres-remove` | Delete DB | `postgresId` | — |
| `postgres-move` | Move to project | `postgresId`, `targetProjectId` | — |
| `postgres-deploy` | Deploy DB | `postgresId` | — |
| `postgres-start` | Start DB | `postgresId` | — |
| `postgres-stop` | Stop DB | `postgresId` | — |
| `postgres-reload` | Reload DB | `postgresId` | — |
| `postgres-rebuild` | Rebuild container | `postgresId` | — |
| `postgres-changeStatus` | Set status | `postgresId`, `status` | — |
| `postgres-saveExternalPort` | Set external port | `postgresId`, `externalPort` | — |
| `postgres-saveEnvironment` | Set env vars | `postgresId` | `env`, `password` |

## MySQL Database (13 tools)

Same pattern as PostgreSQL with `mysql-*` prefix and `mysqlId` parameter.

| Tool | Required |
|------|----------|
| `mysql-create` | `name`, `projectId` |
| `mysql-one` | `mysqlId` |
| `mysql-update` | `mysqlId` |
| `mysql-remove` | `mysqlId` |
| `mysql-move` | `mysqlId`, `targetProjectId` |
| `mysql-deploy` | `mysqlId` |
| `mysql-start` | `mysqlId` |
| `mysql-stop` | `mysqlId` |
| `mysql-reload` | `mysqlId` |
| `mysql-rebuild` | `mysqlId` |
| `mysql-changeStatus` | `mysqlId`, `status` |
| `mysql-saveExternalPort` | `mysqlId`, `externalPort` |
| `mysql-saveEnvironment` | `mysqlId` |

## MCP Limitations

Things the MCP server **cannot** do (use Dashboard or curl instead):

| Operation | Reason | Alternative |
|-----------|--------|-------------|
| Read build logs | WebSocket only | Dashboard UI |
| Read container logs | WebSocket only | Dashboard UI |
| Docker exec into container | No API endpoint | SSH to VPS |
| Manage Redis services | Not in MCP tools | Use curl with `redis.*` API |
| Manage MariaDB/MongoDB | Not in MCP tools | Use curl with `mariadb.*`/`mongo.*` API |
| Manage backups | Not in MCP tools | Use curl with `backup.*` API |
| Configure notifications | Not in MCP tools | Use curl with `notification.*` API |
| Manage Docker Compose | Not in MCP tools | Use curl with `compose.*` API |
| Cluster/Swarm operations | Not in MCP tools | Use curl with `cluster.*`/`swarm.*` API |

**Note:** The MCP server covers 67 of 421 total API endpoints. For operations not covered by MCP tools, fall back to the curl-based API (see [API-REFERENCE.md](API-REFERENCE.md)).
