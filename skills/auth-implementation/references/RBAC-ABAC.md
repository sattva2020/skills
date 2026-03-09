# RBAC & ABAC — Authorization Patterns

Role-Based and Attribute-Based Access Control for web applications.

## RBAC (Role-Based Access Control)

Users are assigned roles. Roles have permissions. Access decisions based on role membership.

### Simple Role Model

```
User ──has──► Role ──has──► Permission
              │
              └── admin: [read, write, delete, manage_users]
              └── editor: [read, write]
              └── viewer: [read]
```

### Implementation — Inline Permissions

```typescript
// Simple: define permissions per role in code
const ROLE_PERMISSIONS = {
  admin: ['read', 'write', 'delete', 'manage_users', 'manage_roles'],
  editor: ['read', 'write', 'delete'],
  viewer: ['read'],
} as const;

type Role = keyof typeof ROLE_PERMISSIONS;
type Permission = (typeof ROLE_PERMISSIONS)[Role][number];

function hasPermission(role: Role, permission: Permission): boolean {
  return (ROLE_PERMISSIONS[role] as readonly string[]).includes(permission);
}

function hasAnyPermission(role: Role, permissions: Permission[]): boolean {
  return permissions.some(p => hasPermission(role, p));
}

function hasAllPermissions(role: Role, permissions: Permission[]): boolean {
  return permissions.every(p => hasPermission(role, p));
}
```

### Express Middleware

```typescript
function requirePermission(...permissions: Permission[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    const userRole = req.user?.role as Role;
    if (!userRole) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    if (!hasAnyPermission(userRole, permissions)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }

    next();
  };
}

// Usage
app.get('/api/articles', requirePermission('read'), listArticles);
app.post('/api/articles', requirePermission('write'), createArticle);
app.delete('/api/articles/:id', requirePermission('delete'), deleteArticle);
app.get('/api/admin/users', requirePermission('manage_users'), listUsers);
```

### Next.js Server Action Guard

```typescript
import { auth } from '@/auth';

async function requirePermission(permission: Permission) {
  const session = await auth();
  if (!session) throw new Error('Authentication required');
  if (!hasPermission(session.user.role as Role, permission)) {
    throw new Error('Insufficient permissions');
  }
  return session;
}

// Usage in Server Action
'use server';
export async function deleteArticle(id: string) {
  const session = await requirePermission('delete');
  await prisma.article.delete({ where: { id } });
}
```

### FastAPI Dependency

```python
from fastapi import Depends, HTTPException

ROLE_PERMISSIONS = {
    "admin": {"read", "write", "delete", "manage_users"},
    "editor": {"read", "write", "delete"},
    "viewer": {"read"},
}

def require_permission(*permissions: str):
    async def checker(user = Depends(get_current_user)):
        user_perms = ROLE_PERMISSIONS.get(user.role, set())
        if not any(p in user_perms for p in permissions):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

@app.delete("/api/articles/{id}", dependencies=[Depends(require_permission("delete"))])
async def delete_article(id: str):
    ...
```

## Database-Driven RBAC

For dynamic roles/permissions that change at runtime.

### Schema

```sql
CREATE TABLE roles (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE permissions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(100) UNIQUE NOT NULL,  -- 'articles:read', 'articles:write'
  description TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE role_permissions (
  role_id       UUID REFERENCES roles(id) ON DELETE CASCADE,
  permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);
```

### Prisma Schema

```prisma
model Role {
  id          String   @id @default(cuid())
  name        String   @unique
  description String?
  permissions RolePermission[]
  users       UserRole[]
  createdAt   DateTime @default(now())
}

model Permission {
  id          String   @id @default(cuid())
  name        String   @unique  // "articles:read"
  description String?
  roles       RolePermission[]
  createdAt   DateTime @default(now())
}

model RolePermission {
  roleId       String
  role         Role       @relation(fields: [roleId], references: [id], onDelete: Cascade)
  permissionId String
  permission   Permission @relation(fields: [permissionId], references: [id], onDelete: Cascade)
  @@id([roleId, permissionId])
}

model UserRole {
  userId String
  user   User   @relation(fields: [userId], references: [id], onDelete: Cascade)
  roleId String
  role   Role   @relation(fields: [roleId], references: [id], onDelete: Cascade)
  @@id([userId, roleId])
}
```

### Query User Permissions

```typescript
async function getUserPermissions(userId: string): Promise<string[]> {
  const userWithRoles = await prisma.user.findUnique({
    where: { id: userId },
    include: {
      roles: {
        include: {
          role: {
            include: {
              permissions: {
                include: { permission: true },
              },
            },
          },
        },
      },
    },
  });

  const permissions = new Set<string>();
  for (const ur of userWithRoles?.roles ?? []) {
    for (const rp of ur.role.permissions) {
      permissions.add(rp.permission.name);
    }
  }

  return [...permissions];
}
```

### Role Hierarchy

```typescript
const ROLE_HIERARCHY: Record<string, string[]> = {
  admin: ['editor', 'viewer'],     // admin inherits editor + viewer
  editor: ['viewer'],              // editor inherits viewer
  viewer: [],
};

function getEffectiveRoles(role: string): string[] {
  const roles = new Set<string>([role]);
  const queue = [role];

  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const inherited of ROLE_HIERARCHY[current] ?? []) {
      if (!roles.has(inherited)) {
        roles.add(inherited);
        queue.push(inherited);
      }
    }
  }

  return [...roles];
}
```

## ABAC (Attribute-Based Access Control)

Decisions based on attributes of user, resource, action, and environment.

### Policy Model

```typescript
interface AccessPolicy {
  action: string;
  resource: string;
  condition: (context: PolicyContext) => boolean;
}

interface PolicyContext {
  user: { id: string; role: string; department: string; [key: string]: any };
  resource: { ownerId: string; status: string; [key: string]: any };
  environment: { time: Date; ip: string; [key: string]: any };
}

const policies: AccessPolicy[] = [
  {
    action: 'read',
    resource: 'article',
    condition: () => true, // Everyone can read
  },
  {
    action: 'edit',
    resource: 'article',
    condition: ({ user, resource }) =>
      user.role === 'admin' || resource.ownerId === user.id,
  },
  {
    action: 'delete',
    resource: 'article',
    condition: ({ user, resource }) =>
      user.role === 'admin' ||
      (resource.ownerId === user.id && resource.status === 'draft'),
  },
  {
    action: 'publish',
    resource: 'article',
    condition: ({ user }) =>
      ['admin', 'editor'].includes(user.role),
  },
];

function isAllowed(action: string, resource: string, context: PolicyContext): boolean {
  const applicable = policies.filter(p => p.action === action && p.resource === resource);
  return applicable.some(p => p.condition(context));
}
```

## CASL.js Integration

CASL is an isomorphic authorization library for JavaScript.

```bash
npm install @casl/ability
```

### Define Abilities

```typescript
import { AbilityBuilder, createMongoAbility, MongoAbility } from '@casl/ability';

type Actions = 'read' | 'create' | 'update' | 'delete' | 'manage';
type Subjects = 'Article' | 'Comment' | 'User' | 'all';

export type AppAbility = MongoAbility<[Actions, Subjects]>;

export function defineAbilityFor(user: { id: string; role: string }): AppAbility {
  const { can, cannot, build } = new AbilityBuilder<AppAbility>(createMongoAbility);

  switch (user.role) {
    case 'admin':
      can('manage', 'all'); // Admin can do everything
      break;

    case 'editor':
      can('read', 'Article');
      can('create', 'Article');
      can('update', 'Article');
      can('delete', 'Article', { authorId: user.id }); // Own articles only
      can('read', 'Comment');
      can('create', 'Comment');
      can('delete', 'Comment', { authorId: user.id });
      break;

    case 'viewer':
      can('read', 'Article');
      can('read', 'Comment');
      can('create', 'Comment');
      can('update', 'Comment', { authorId: user.id });
      can('delete', 'Comment', { authorId: user.id });
      break;

    default:
      can('read', 'Article', { published: true });
  }

  return build();
}
```

### Usage

```typescript
const ability = defineAbilityFor(user);

// Check permissions
ability.can('read', 'Article');                           // true
ability.can('delete', 'Article');                          // depends on role
ability.can('delete', subject('Article', { authorId: user.id })); // field-level

// Middleware
function authorize(action: Actions, subject: Subjects) {
  return (req, res, next) => {
    const ability = defineAbilityFor(req.user);
    if (ability.cannot(action, subject)) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    next();
  };
}
```

### CASL with React

```bash
npm install @casl/react
```

```typescript
import { Can } from '@casl/react';

<Can I="delete" a="Article" ability={ability}>
  <button onClick={handleDelete}>Delete</button>
</Can>
```

## Casbin Integration

Casbin supports multiple access control models (ACL, RBAC, ABAC) via policy files.

```bash
npm install casbin
```

### RBAC Model

```ini
# model.conf
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

```csv
# policy.csv
p, admin, articles, read
p, admin, articles, write
p, admin, articles, delete
p, editor, articles, read
p, editor, articles, write
p, viewer, articles, read

g, alice, admin
g, bob, editor
```

### Usage

```typescript
import { newEnforcer } from 'casbin';

const enforcer = await newEnforcer('model.conf', 'policy.csv');

// Check permission
const allowed = await enforcer.enforce('alice', 'articles', 'delete'); // true
const denied = await enforcer.enforce('bob', 'articles', 'delete');   // false

// Middleware
function casbinAuth(obj: string, act: string) {
  return async (req, res, next) => {
    const allowed = await enforcer.enforce(req.user.role, obj, act);
    if (!allowed) return res.status(403).json({ error: 'Forbidden' });
    next();
  };
}
```

## Organization / Team-Scoped Permissions

For multi-tenant SaaS where users have different roles per organization.

### Schema

```sql
CREATE TABLE organizations (
  id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE memberships (
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  role            VARCHAR(50) NOT NULL DEFAULT 'member',
  PRIMARY KEY (user_id, organization_id)
);
```

### Scoped Permission Check

```typescript
async function requireOrgPermission(
  userId: string,
  orgId: string,
  requiredRoles: string[],
) {
  const membership = await prisma.membership.findUnique({
    where: { userId_organizationId: { userId, organizationId: orgId } },
  });

  if (!membership) throw new Error('Not a member of this organization');
  if (!requiredRoles.includes(membership.role)) throw new Error('Insufficient role');

  return membership;
}

// Express middleware
function requireOrgRole(...roles: string[]) {
  return async (req, res, next) => {
    try {
      const orgId = req.params.orgId || req.headers['x-organization-id'];
      await requireOrgPermission(req.user.id, orgId, roles);
      next();
    } catch (err) {
      res.status(403).json({ error: err.message });
    }
  };
}

app.delete('/api/orgs/:orgId/projects/:id', requireOrgRole('owner', 'admin'), deleteProject);
```

## Resource Ownership Checks

Common pattern: users can only access their own resources.

```typescript
// Generic ownership middleware
function requireOwnership(resourceFetcher: (req: Request) => Promise<{ userId: string } | null>) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const resource = await resourceFetcher(req);
    if (!resource) return res.status(404).json({ error: 'Not found' });

    if (resource.userId !== req.user.id && req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Not your resource' });
    }

    req.resource = resource;
    next();
  };
}

// Usage
app.put('/api/articles/:id',
  requireAuth,
  requireOwnership(req => prisma.article.findUnique({ where: { id: req.params.id } })),
  updateArticle,
);
```

## Best Practices

1. **Default deny** — if no policy matches, deny access
2. **Check on the server** — client-side checks are for UX only
3. **Use resource-level checks** — not just role checks (ownership matters)
4. **Cache permissions** — avoid DB queries on every request (Redis or in-memory)
5. **Audit permission changes** — log who granted/revoked what
6. **Principle of least privilege** — start with minimal permissions, add as needed
7. **Separate authn from authz** — authentication (who) and authorization (what) are different concerns
