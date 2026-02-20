# Dokploy API Reference

Source: OpenAPI 3.0.3 spec from `settings.getOpenApiDocument` — **421 endpoints**.

## Authentication

All requests require the `x-api-key` header:

```
x-api-key: <your-api-token>
```

Generate token: Dashboard → Settings → Profile → API/CLI → Generate.
Tokens never expire by default.

## Retrieving the OpenAPI Spec

```bash
curl -s "${DOKPLOY_URL}/api/settings.getOpenApiDocument" \
  -H "x-api-key: ${DOKPLOY_API_KEY}"
```

Returns the full OpenAPI 3.0.3 JSON document with all 421 endpoints.

## Request Formats

Dokploy uses tRPC. Two formats depending on operation type.

### Queries (GET) — Read operations

```bash
curl -s -X GET \
  "${DOKPLOY_URL}/api/trpc/<router>.<procedure>?input=$(python3 -c "
import urllib.parse, json
print(urllib.parse.quote(json.dumps({'json': {<params>}})))
")" \
  -H "x-api-key: ${DOKPLOY_API_KEY}"
```

The `input` query parameter must be URL-encoded JSON with a `{"json": {...}}` wrapper.

### Mutations (POST) — Write operations

```bash
curl -s -X POST "${DOKPLOY_URL}/api/<router>.<procedure>" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"json": {<params>}}'
```

### Response Format

```json
{
  "result": {
    "data": {
      "json": { ... }
    }
  }
}
```

Extract data: `response.result.data.json`

## Project (4 endpoints)

| Endpoint | Method | Required Params | Optional Params |
|----------|--------|-----------------|-----------------|
| `project.all` | GET | — | — |
| `project.one` | GET | `projectId` | — |
| `project.create` | POST | `name` | `description`, `env` |
| `project.remove` | POST | `projectId` | — |

Also: `project.duplicate`, `project.update`.

## Application (38 endpoints)

### Core Operations

| Endpoint | Method | Required | Optional |
|----------|--------|----------|----------|
| `application.one` | GET | `applicationId` | — |
| `application.create` | POST | `name`, `environmentId` | `appName`, `description`, `serverId` |
| `application.deploy` | POST | `applicationId` | `title`, `description` |
| `application.redeploy` | POST | `applicationId` | — |
| `application.stop` | POST | `applicationId` | — |
| `application.start` | POST | `applicationId` | — |
| `application.delete` | POST | `applicationId` | — |
| `application.reload` | POST | `applicationId` | — |
| `application.cancelDeployment` | POST | `applicationId` | — |
| `application.killBuild` | POST | `applicationId` | — |

### Configuration

| Endpoint | Method | Required | Optional |
|----------|--------|----------|----------|
| `application.update` | POST | `applicationId` | 80+ fields (see below) |
| `application.saveBuildType` | POST | `applicationId`, `buildType`, `dockerContextPath`, `dockerBuildStage` | `dockerfile`, `herokuVersion`, `publishDirectory`, `isStaticSpa`, `railpackVersion` |
| `application.saveEnvironment` | POST | `applicationId` | `env`, `buildArgs`, `buildSecrets`, `createEnvFile` |
| `application.readTraefikConfig` | GET | `applicationId` | — |
| `application.updateTraefikConfig` | POST | `applicationId`, config | — |

### Git Provider Connections

| Endpoint | Method | Required |
|----------|--------|----------|
| `application.saveGithubProvider` | POST | `applicationId`, provider config |
| `application.saveGitlabProvider` | POST | `applicationId`, provider config |
| `application.saveGiteaProvider` | POST | `applicationId`, provider config |
| `application.saveBitbucketProvider` | POST | `applicationId`, provider config |
| `application.saveGitProvider` | POST | `applicationId`, provider config |
| `application.saveDockerProvider` | POST | `applicationId`, provider config |
| `application.disconnectGitProvider` | POST | `applicationId` |

### Build Types (`buildType` enum)

```
dockerfile | heroku_buildpacks | paketo_buildpacks | nixpacks | static | railpack
```

### Application Statuses (`applicationStatus` enum)

```
idle | running | done | error
```

### Key `application.update` Fields

Resource limits:
- `memoryReservation`, `memoryLimit`, `cpuReservation`, `cpuLimit`

Git settings:
- `sourceType`: `github|docker|git|gitlab|bitbucket|gitea|drop`
- `repository`, `owner`, `branch`, `buildPath`
- `autoDeploy`: boolean
- `triggerType`: `push|tag`
- `enableSubmodules`: boolean

Docker settings:
- `dockerfile`, `dockerContextPath`, `dockerBuildStage`
- `dockerImage`, `registryUrl`

Build:
- `buildArgs`, `buildSecrets`, `cleanCache`
- `createEnvFile`: boolean

Preview deployments:
- `isPreviewDeploymentsActive`, `previewEnv`, `previewPort`, `previewHttps`, `previewLimit`

Swarm mode:
- `healthCheckSwarm`, `restartPolicySwarm`, `placementSwarm`, `replicas`

## Deployment (5 endpoints)

| Endpoint | Method | Required |
|----------|--------|----------|
| `deployment.all` | GET | `applicationId` |
| `deployment.allByCompose` | GET | `composeId` |
| `deployment.allByServer` | GET | `serverId` |
| `deployment.allByType` | GET | type params |
| `deployment.removeDeployment` | POST | `deploymentId` |
| `deployment.killProcess` | POST | `deploymentId` |

**IMPORTANT:** Build logs and container logs are **WebSocket only**.
No REST endpoint exists for reading logs. Use the Dashboard UI.

## Domain (7 endpoints)

| Endpoint | Method | Required | Optional |
|----------|--------|----------|----------|
| `domain.byApplicationId` | GET | `applicationId` | — |
| `domain.byComposeId` | GET | `composeId` | — |
| `domain.one` | GET | `domainId` | — |
| `domain.create` | POST | `host` | `path`, `port`, `https`, `applicationId`, `composeId`, `certificateType`, `serviceName`, `domainType`, `stripPath`, `internalPath` |
| `domain.update` | POST | `domainId`, fields | — |
| `domain.delete` | POST | `domainId` | — |
| `domain.generateDomain` | POST | params | — |
| `domain.validateDomain` | POST | params | — |

### Certificate Types

```
letsencrypt | none | custom
```

### Domain Types

```
compose | application | preview
```

## PostgreSQL (14 endpoints)

| Endpoint | Method | Required | Optional |
|----------|--------|----------|----------|
| `postgres.one` | GET | `postgresId` | — |
| `postgres.create` | POST | `name`, `databaseName`, `databaseUser`, `databasePassword`, `environmentId` | `appName`, `dockerImage`, `description`, `serverId` |
| `postgres.update` | POST | `postgresId`, fields | — |
| `postgres.remove` | POST | `postgresId` | — |
| `postgres.deploy` | POST | `postgresId` | — |
| `postgres.start` | POST | `postgresId` | — |
| `postgres.stop` | POST | `postgresId` | — |
| `postgres.reload` | POST | `postgresId` | — |
| `postgres.rebuild` | POST | `postgresId` | — |
| `postgres.saveExternalPort` | POST | `postgresId`, `externalPort` (nullable) | — |
| `postgres.saveEnvironment` | POST | `postgresId`, env | — |
| `postgres.changeStatus` | POST | `postgresId`, status | — |
| `postgres.move` | POST | `postgresId`, target | — |

## Redis (14 endpoints)

| Endpoint | Method | Required | Optional |
|----------|--------|----------|----------|
| `redis.one` | GET | `redisId` | — |
| `redis.create` | POST | `name`, `databasePassword`, `environmentId` | `appName`, `dockerImage`, `description`, `serverId` |
| `redis.update` | POST | `redisId`, fields | — |
| `redis.remove` | POST | `redisId` | — |
| `redis.deploy` | POST | `redisId` | — |
| `redis.start` | POST | `redisId` | — |
| `redis.stop` | POST | `redisId` | — |
| `redis.reload` | POST | `redisId` | — |
| `redis.rebuild` | POST | `redisId` | — |
| `redis.saveExternalPort` | POST | `redisId`, `externalPort` | — |
| `redis.saveEnvironment` | POST | `redisId`, env | — |

## Docker (6 endpoints)

| Endpoint | Method | Required |
|----------|--------|----------|
| `docker.getContainers` | GET | — |
| `docker.getContainersByAppLabel` | GET | `appLabel` |
| `docker.getContainersByAppNameMatch` | GET | `appName` |
| `docker.getServiceContainersByAppName` | GET | `appName` |
| `docker.getStackContainersByAppName` | GET | `appName` |
| `docker.getConfig` | GET | — |
| `docker.restartContainer` | POST | `containerId` |

**No Docker exec endpoint exists.**

## Docker Compose (25 endpoints)

| Endpoint | Method | Required |
|----------|--------|----------|
| `compose.one` | GET | `composeId` |
| `compose.create` | POST | `name`, `environmentId` |
| `compose.deploy` | POST | `composeId` |
| `compose.stop` | POST | `composeId` |
| `compose.start` | POST | `composeId` |
| `compose.delete` | POST | `composeId` |
| `compose.update` | POST | `composeId`, fields |
| `compose.redeploy` | POST | `composeId` |
| `compose.loadServices` | GET | `composeId` |
| `compose.templates` | GET | — |

## Settings / Server

| Endpoint | Method | Description |
|----------|--------|-------------|
| `settings.health` | GET | Server health check |
| `settings.getOpenApiDocument` | GET | Full OpenAPI spec |
| `settings.getDokployVersion` | GET | Dokploy version |
| `settings.getIp` | GET | Server IP |
| `settings.reloadServer` | POST | Reload server |
| `settings.reloadTraefik` | POST | Reload Traefik |
| `settings.cleanDockerPrune` | POST | Docker system prune |
| `settings.cleanUnusedImages` | POST | Remove unused images |
| `settings.cleanStoppedContainers` | POST | Remove stopped containers |

## Other Database Services

Same pattern as PostgreSQL/Redis (14 endpoints each):

- `mysql.*` — MySQL
- `mariadb.*` — MariaDB
- `mongo.*` — MongoDB

## All 421 Endpoint Categories

| Category | Count | Description |
|----------|-------|-------------|
| `application.*` | 38 | Application management |
| `compose.*` | 25 | Docker Compose services |
| `settings.*` | 40 | Server settings, Traefik, cleanup |
| `notification.*` | 30 | Slack/Telegram/Discord/Email/Webhook |
| `postgres.*` | 14 | PostgreSQL management |
| `redis.*` | 14 | Redis management |
| `mysql.*` | 14 | MySQL management |
| `mariadb.*` | 14 | MariaDB management |
| `mongo.*` | 14 | MongoDB management |
| `server.*` | 18 | Remote server management |
| `user.*` | 18 | User management, API keys |
| `domain.*` | 8 | Domain/SSL management |
| `docker.*` | 7 | Container operations |
| `deployment.*` | 6 | Deployment history |
| `backup.*` | 10 | Database backups |
| `compose templates` | 3 | Service templates |
| `github/gitlab/gitea/bitbucket.*` | 28 | Git providers |
| `sshKey.*` | 5 | SSH key management |
| `certificates.*` | 4 | SSL certificates |
| `registry.*` | 6 | Docker registries |
| `project.*` | 5 | Project management |
| `organization.*` | 8 | Organization management |
| `environment.*` | 5 | Environment management |
| `mounts.*` | 4 | Volume mounts |
| `port.*` | 3 | Port management |
| `redirects.*` | 3 | URL redirects |
| `security.*` | 3 | Security settings |
| `schedule.*` | 5 | Scheduled jobs |
| `rollback.*` | 2 | Deployment rollbacks |
| `sso.*` | 10 | Single Sign-On |
| `licenseKey.*` | 5 | Enterprise licensing |
| `stripe.*` | 4 | Billing (cloud) |
| `cluster.*` | 4 | Docker Swarm cluster |
| `swarm.*` | 3 | Swarm node management |
| `ai.*` | 8 | AI features |
| `volumeBackups.*` | 5 | Volume backup management |
| `previewDeployment.*` | 4 | Preview deployments |
| `gitProvider.*` | 2 | Git provider generic |
| `destination.*` | 5 | S3 backup destinations |
| `admin.*` | 1 | Admin setup |

## Practical Examples

### Deploy and poll until done

```bash
DOKPLOY_URL="https://dokploy.example.com"
DOKPLOY_API_KEY="your-key"
APP_ID="your-app-id"

# Trigger deploy
curl -s -X POST "${DOKPLOY_URL}/api/application.deploy" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"json\":{\"applicationId\":\"${APP_ID}\"}}"

# Poll status every 15 seconds
while true; do
  STATUS=$(curl -s -X GET "${DOKPLOY_URL}/api/trpc/application.one?input=$(python3 -c "
import urllib.parse, json
print(urllib.parse.quote(json.dumps({'json':{'applicationId':'${APP_ID}'}})))
")" -H "x-api-key: ${DOKPLOY_API_KEY}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('result',{}).get('data',{}).get('json',{}).get('applicationStatus','unknown'))
")
  echo "Status: ${STATUS}"
  if [ "$STATUS" = "done" ] || [ "$STATUS" = "error" ]; then break; fi
  sleep 15
done
```

### Set environment variables

```bash
curl -s -X POST "${DOKPLOY_URL}/api/application.saveEnvironment" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "applicationId": "APP_ID",
      "env": "DATABASE_URL=postgresql://user:pass@host:5432/db\nREDIS_URL=redis://:pass@host:6379\nNODE_ENV=production"
    }
  }'
```

### Create a domain with HTTPS

```bash
curl -s -X POST "${DOKPLOY_URL}/api/domain.create" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "applicationId": "APP_ID",
      "host": "app.example.com",
      "https": true,
      "port": 3000,
      "certificateType": "letsencrypt",
      "domainType": "application",
      "stripPath": false
    }
  }'
```

### Create PostgreSQL service

```bash
curl -s -X POST "${DOKPLOY_URL}/api/postgres.create" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "name": "my-postgres",
      "databaseName": "mydb",
      "databaseUser": "myuser",
      "databasePassword": "secure-password",
      "environmentId": "ENV_ID",
      "dockerImage": "postgres:16-alpine"
    }
  }'
```

### Get deployment history

```bash
curl -s -X GET "${DOKPLOY_URL}/api/trpc/deployment.all?input=$(python3 -c "
import urllib.parse, json
print(urllib.parse.quote(json.dumps({'json':{'applicationId':'APP_ID'}})))
")" -H "x-api-key: ${DOKPLOY_API_KEY}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for dep in d.get('result',{}).get('data',{}).get('json',[])[:5]:
    print(f\"{dep.get('status','?'):8} {dep.get('title','')[:50]:50} {dep.get('createdAt','')[:19]}\")
"
```

### List Docker containers

```bash
curl -s -X GET "${DOKPLOY_URL}/api/trpc/docker.getContainersByAppNameMatch?input=$(python3 -c "
import urllib.parse, json
print(urllib.parse.quote(json.dumps({'json':{'appName':'your-app-name'}})))
")" -H "x-api-key: ${DOKPLOY_API_KEY}"
```

### Set build type to Dockerfile

```bash
curl -s -X POST "${DOKPLOY_URL}/api/application.saveBuildType" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "applicationId": "APP_ID",
      "buildType": "dockerfile",
      "dockerfile": "./Dockerfile",
      "dockerContextPath": "./",
      "dockerBuildStage": ""
    }
  }'
```
