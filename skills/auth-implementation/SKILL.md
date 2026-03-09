---
name: auth-implementation
description: >-
  Implement authentication and authorization in web applications.
  Use when adding login, signup, sessions, JWT tokens, OAuth, SSO,
  API key auth, role-based access control (RBAC), permissions,
  protected routes, middleware guards, password hashing, MFA/2FA,
  refresh token rotation, CSRF protection, or integrating auth
  providers like NextAuth/Auth.js, Better Auth, Lucia, Clerk,
  Auth0, Supabase Auth, Firebase Auth, Passport.js.
  Covers Next.js, Express, Fastify, Django, FastAPI, Laravel, Go.
  Handles database schema design, security hardening, and common
  auth pitfalls (token storage, session fixation, CORS).
allowed-tools: Read Write Bash(npm *) Bash(npx *) Bash(pnpm *) Bash(yarn *) Bash(pip *) Bash(composer *) Bash(go *) Bash(bunx *) Grep Glob
metadata:
  author: ai-ads-agent
  version: "1.0"
  category: security
---

# Auth Implementation

Comprehensive guide for implementing authentication and authorization in web applications. Covers session-based auth, JWT, OAuth 2.0, SSO, API keys, RBAC/ABAC, and security hardening across all major frameworks and libraries.

## Decision Matrix

Use this table to pick the right approach and library for your stack:

| Use Case | Framework | Recommended Approach | Library | Reference |
|----------|-----------|---------------------|---------|-----------|
| Full-stack app, social login | Next.js App Router | OAuth + sessions | Auth.js v5 | [NEXTAUTH-AUTHJS.md](references/NEXTAUTH-AUTHJS.md) |
| Full-stack app, email/password + social | Next.js / SvelteKit | Session-based | Better Auth | [BETTER-AUTH.md](references/BETTER-AUTH.md) |
| Full-stack, maximum control | Next.js / SvelteKit / Astro | Session-based | Lucia v3 | [LUCIA-AUTH.md](references/LUCIA-AUTH.md) |
| API backend, social login | Express / Fastify | Strategy-based | Passport.js | [PASSPORT-EXPRESS.md](references/PASSPORT-EXPRESS.md) |
| Microservice API | Any | JWT (access + refresh) | jose / jsonwebtoken | [CUSTOM-JWT.md](references/CUSTOM-JWT.md) |
| SaaS, managed auth | Any | Hosted OAuth/OIDC | Clerk / Auth0 / Supabase Auth | [OAUTH-OIDC.md](references/OAUTH-OIDC.md) |
| Django app | Django | Session-based | django.contrib.auth + allauth | [FRAMEWORK-PATTERNS.md](references/FRAMEWORK-PATTERNS.md) |
| Python API | FastAPI | JWT / OAuth2 | python-jose + Depends() | [FRAMEWORK-PATTERNS.md](references/FRAMEWORK-PATTERNS.md) |
| PHP app | Laravel | Session / token | Sanctum / Fortify / Breeze | [FRAMEWORK-PATTERNS.md](references/FRAMEWORK-PATTERNS.md) |
| Go service | net/http / Chi / Gin | Session or JWT | gorilla/sessions / golang-jwt | [FRAMEWORK-PATTERNS.md](references/FRAMEWORK-PATTERNS.md) |
| Enterprise SSO | Any | SAML / OIDC | Provider-specific SDK | [OAUTH-OIDC.md](references/OAUTH-OIDC.md) |
| Machine-to-machine | Any | API keys or Client Credentials | Custom | [CUSTOM-JWT.md](references/CUSTOM-JWT.md) |
| Need RBAC/permissions | Any | Role-permission model | CASL / Casbin / custom | [RBAC-ABAC.md](references/RBAC-ABAC.md) |

## Implementation Workflow

Follow these 5 steps for any auth implementation:

### Step 1: Detect Stack

Read `package.json`, `requirements.txt`, `go.mod`, `composer.json`, or framework config to identify:
- Framework and version (Next.js 14+, Express, Django, FastAPI, Laravel, Go, SvelteKit)
- Database and ORM (Prisma, Drizzle, SQLAlchemy, GORM, Eloquent)
- Existing auth code (check for auth middleware, session config, JWT imports)

### Step 2: Choose Approach

Use the Decision Matrix above. Key factors:
- **Server-rendered app** → session-based (cookies)
- **SPA + API** → JWT (access + refresh tokens) or BFF pattern
- **Mobile + API** → JWT with secure token storage
- **Multiple providers needed** → Auth.js, Better Auth, or Passport.js
- **Enterprise / compliance** → managed provider (Clerk, Auth0) or OIDC
- **Maximum control** → Lucia or custom JWT

### Step 3: Database Schema

Set up auth tables. See [DATABASE-SCHEMAS.md](references/DATABASE-SCHEMAS.md) for full schemas.

Core tables needed:
- `users` — id, email, password_hash, email_verified, created_at
- `sessions` — id, user_id, expires_at (for session-based)
- `accounts` — id, user_id, provider, provider_account_id (for OAuth)

### Step 4: Implement

Use the relevant reference file for step-by-step implementation. Install dependencies, configure auth, add routes, protect endpoints.

### Step 5: Harden

Apply [SECURITY-CHECKLIST.md](references/SECURITY-CHECKLIST.md). At minimum:
- [ ] CSRF protection enabled
- [ ] Cookies: HttpOnly, Secure, SameSite=Lax
- [ ] Password hashing: argon2id or bcrypt
- [ ] Rate limiting on login/register/reset
- [ ] Input validation on all auth endpoints

## Session-Based Auth (Quick Start)

Session-based auth stores session ID in a cookie. Server holds session data.

**When to use:** Server-rendered apps, full-stack frameworks, when you need easy revocation.

### Express + express-session

```typescript
import session from 'express-session';
import RedisStore from 'connect-redis';
import { createClient } from 'redis';

const redisClient = createClient({ url: process.env.REDIS_URL });
await redisClient.connect();

app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET!, // min 32 chars, random
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'lax',
    maxAge: 1000 * 60 * 60 * 24 * 7, // 7 days
  },
}));
```

### Next.js (iron-session)

```typescript
// lib/session.ts
import { getIronSession } from 'iron-session';
import { cookies } from 'next/headers';

export async function getSession() {
  return getIronSession<SessionData>(await cookies(), {
    password: process.env.SESSION_SECRET!,
    cookieName: 'app-session',
    cookieOptions: {
      secure: process.env.NODE_ENV === 'production',
      httpOnly: true,
      sameSite: 'lax',
    },
  });
}
```

## JWT Auth (Quick Start)

JWT auth uses signed tokens. Access token (short-lived) + refresh token (long-lived).

**When to use:** APIs consumed by SPAs, mobile apps, microservices. See [CUSTOM-JWT.md](references/CUSTOM-JWT.md).

### Token Architecture

```
Access Token:  Short-lived (15 min), in memory or Authorization header
Refresh Token: Long-lived (7-30 days), HttpOnly cookie, rotated on use
```

### Node.js (jose library)

```typescript
import { SignJWT, jwtVerify } from 'jose';

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

// Create access token
async function createAccessToken(userId: string, role: string) {
  return new SignJWT({ sub: userId, role })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('15m')
    .sign(secret);
}

// Verify token
async function verifyToken(token: string) {
  const { payload } = await jwtVerify(token, secret);
  return payload;
}
```

### Middleware Pattern

```typescript
async function authMiddleware(req: Request, next: Function) {
  const token = req.headers.get('Authorization')?.replace('Bearer ', '');
  if (!token) return new Response('Unauthorized', { status: 401 });
  try {
    const payload = await verifyToken(token);
    req.user = payload;
    return next();
  } catch {
    return new Response('Invalid token', { status: 401 });
  }
}
```

## OAuth 2.0 / Social Login (Quick Start)

OAuth lets users sign in with existing accounts (Google, GitHub, etc.).

**Flow: Authorization Code + PKCE** (recommended for all clients):

```
1. Client generates code_verifier + code_challenge
2. Redirect to provider: /authorize?response_type=code&code_challenge=...
3. User authenticates with provider
4. Provider redirects back with authorization code
5. Server exchanges code + code_verifier for tokens
6. Server creates session or issues own JWT
```

See [OAUTH-OIDC.md](references/OAUTH-OIDC.md) for provider-specific setup.

## Provider Quick Reference

| Provider | Install | Config Needed | Reference |
|----------|---------|---------------|-----------|
| Auth.js v5 | `npm i next-auth@beta` | `auth.ts` + providers + adapter | [NEXTAUTH-AUTHJS.md](references/NEXTAUTH-AUTHJS.md) |
| Better Auth | `npm i better-auth` | `auth.ts` + DB + plugins | [BETTER-AUTH.md](references/BETTER-AUTH.md) |
| Lucia v3 | `npm i lucia` | Adapter + session config | [LUCIA-AUTH.md](references/LUCIA-AUTH.md) |
| Passport.js | `npm i passport passport-local` | Strategies + serialize | [PASSPORT-EXPRESS.md](references/PASSPORT-EXPRESS.md) |
| Clerk | `npm i @clerk/nextjs` | `CLERK_*` env vars | [OAUTH-OIDC.md](references/OAUTH-OIDC.md) |
| Auth0 | `npm i @auth0/nextjs-auth0` | `AUTH0_*` env vars | [OAUTH-OIDC.md](references/OAUTH-OIDC.md) |
| Supabase Auth | `npm i @supabase/supabase-js` | Supabase project URL + key | [OAUTH-OIDC.md](references/OAUTH-OIDC.md) |
| Firebase Auth | `npm i firebase` | Firebase config | [OAUTH-OIDC.md](references/OAUTH-OIDC.md) |
| Django allauth | `pip install django-allauth` | INSTALLED_APPS + providers | [FRAMEWORK-PATTERNS.md](references/FRAMEWORK-PATTERNS.md) |
| Laravel Sanctum | `composer require laravel/sanctum` | Publish config + middleware | [FRAMEWORK-PATTERNS.md](references/FRAMEWORK-PATTERNS.md) |

## Database Schema Essentials

See [DATABASE-SCHEMAS.md](references/DATABASE-SCHEMAS.md) for full schemas.

### Prisma (Core Tables)

```prisma
model User {
  id            String    @id @default(cuid())
  email         String    @unique
  passwordHash  String?
  emailVerified DateTime?
  name          String?
  role          String    @default("user")
  sessions      Session[]
  accounts      Account[]
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
}

model Session {
  id        String   @id @default(cuid())
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  expiresAt DateTime
  createdAt DateTime @default(now())
  @@index([userId])
}

model Account {
  id                String @id @default(cuid())
  userId            String
  user              User   @relation(fields: [userId], references: [id], onDelete: Cascade)
  provider          String
  providerAccountId String
  accessToken       String?
  refreshToken      String?
  expiresAt         Int?
  @@unique([provider, providerAccountId])
  @@index([userId])
}
```

## Middleware & Route Protection

### Next.js App Router — middleware.ts

```typescript
import { NextRequest, NextResponse } from 'next/server';

const protectedPaths = ['/dashboard', '/settings', '/api/protected'];
const authPaths = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const sessionToken = request.cookies.get('session-token')?.value;
  const { pathname } = request.nextUrl;

  const isProtected = protectedPaths.some(p => pathname.startsWith(p));
  const isAuthPage = authPaths.some(p => pathname.startsWith(p));

  if (isProtected && !sessionToken) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  if (isAuthPage && sessionToken) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/settings/:path*', '/api/protected/:path*', '/login', '/register'],
};
```

### Express Middleware

```typescript
function requireAuth(req, res, next) {
  if (!req.session?.userId) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  next();
}

function requireRole(...roles: string[]) {
  return (req, res, next) => {
    if (!roles.includes(req.session.role)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }
    next();
  };
}

// Usage
app.get('/admin', requireAuth, requireRole('admin'), adminHandler);
```

## RBAC Quick Start

See [RBAC-ABAC.md](references/RBAC-ABAC.md) for full patterns.

### Simple Role Check

```typescript
// Define roles and permissions
const PERMISSIONS = {
  admin: ['read', 'write', 'delete', 'manage_users'],
  editor: ['read', 'write'],
  viewer: ['read'],
} as const;

function hasPermission(role: string, permission: string): boolean {
  return PERMISSIONS[role]?.includes(permission) ?? false;
}

// Middleware
function requirePermission(permission: string) {
  return (req, res, next) => {
    if (!hasPermission(req.user.role, permission)) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    next();
  };
}
```

## Security Checklist (Condensed)

See [SECURITY-CHECKLIST.md](references/SECURITY-CHECKLIST.md) for full details.

| # | Check | Priority | Notes |
|---|-------|----------|-------|
| 1 | Password hashing: argon2id or bcrypt (cost ≥ 10) | Critical | Never SHA-256/MD5 |
| 2 | Cookies: HttpOnly, Secure, SameSite=Lax | Critical | Prevents XSS token theft |
| 3 | CSRF protection on state-changing endpoints | Critical | Double-submit or SameSite |
| 4 | Rate limit login attempts (5/min per IP+user) | Critical | Prevents brute force |
| 5 | Rate limit password reset (3/hour per email) | High | Prevents email flooding |
| 6 | Validate redirect URLs (allowlist origins) | High | Prevents open redirect |
| 7 | Token expiry: access 15min, refresh 7-30d | High | Limit blast radius |
| 8 | Refresh token rotation + family detection | High | Detect token theft |
| 9 | Email verification before full access | Medium | Prevents fake accounts |
| 10 | Account lockout after N failed attempts | Medium | With exponential backoff |
| 11 | HTTPS everywhere (HSTS header) | Critical | No mixed content |
| 12 | Input validation on email, password | High | Zod / Yup / server-side |
| 13 | Secure password reset flow (time-limited token) | High | Token expires in 1h |
| 14 | Audit log for auth events | Medium | Login, logout, password change |
| 15 | MFA/2FA for sensitive operations | Medium | TOTP or WebAuthn |

## Common Pitfalls

| # | Pitfall | Fix |
|---|---------|-----|
| 1 | Storing JWT in localStorage | Use HttpOnly cookie or in-memory only |
| 2 | No refresh token rotation | Rotate on every use, detect reuse |
| 3 | Long-lived access tokens (>1h) | Keep to 15min, use refresh tokens |
| 4 | Comparing passwords with `===` | Use timing-safe comparison (crypto.timingSafeEqual) |
| 5 | Not validating redirect URIs | Allowlist of origins, never open redirect |
| 6 | Session fixation after login | Regenerate session ID after authentication |
| 7 | Missing CSRF on cookie-based auth | Add CSRF token or use SameSite=Strict |
| 8 | Exposing user enumeration | Same response for "user not found" and "wrong password" |
| 9 | No rate limiting on auth endpoints | Rate limit by IP + username combination |
| 10 | Storing unhashed API keys | Store hash, show key only once on creation |
| 11 | Using deprecated crypto (MD5, SHA-1) | Use argon2id for passwords, SHA-256+ for tokens |
| 12 | Not revoking sessions on password change | Invalidate all sessions except current |

## MFA / 2FA Overview

### TOTP (Time-based One-Time Password)

```typescript
// Libraries: otpauth (Node.js), pyotp (Python)
import { TOTP } from 'otpauth';

const totp = new TOTP({
  issuer: 'MyApp',
  label: user.email,
  algorithm: 'SHA1',
  digits: 6,
  period: 30,
  secret: generateSecret(),
});

// Generate QR code URI
const uri = totp.toString(); // otpauth://totp/MyApp:user@email.com?...

// Verify code
const isValid = totp.validate({ token: userCode, window: 1 }) !== null;
```

### WebAuthn / Passkeys

Use `@simplewebauthn/server` + `@simplewebauthn/browser` for passwordless auth. See [SECURITY-CHECKLIST.md](references/SECURITY-CHECKLIST.md) for implementation steps.

## References Index

| File | Topic | When to Read |
|------|-------|-------------|
| [NEXTAUTH-AUTHJS.md](references/NEXTAUTH-AUTHJS.md) | Auth.js v5 + Next.js | Next.js app with social login |
| [BETTER-AUTH.md](references/BETTER-AUTH.md) | Better Auth | Next.js/Svelte with plugin system |
| [LUCIA-AUTH.md](references/LUCIA-AUTH.md) | Lucia v3 | Maximum control, session-based |
| [PASSPORT-EXPRESS.md](references/PASSPORT-EXPRESS.md) | Passport.js | Express/Fastify backend |
| [CUSTOM-JWT.md](references/CUSTOM-JWT.md) | Custom JWT | Microservice API, no framework auth |
| [OAUTH-OIDC.md](references/OAUTH-OIDC.md) | OAuth 2.0 / OIDC | Social login, SSO, managed providers |
| [DATABASE-SCHEMAS.md](references/DATABASE-SCHEMAS.md) | DB schemas | Setting up auth tables |
| [SECURITY-CHECKLIST.md](references/SECURITY-CHECKLIST.md) | Security hardening | After initial implementation |
| [RBAC-ABAC.md](references/RBAC-ABAC.md) | Authorization | Adding roles/permissions |
| [FRAMEWORK-PATTERNS.md](references/FRAMEWORK-PATTERNS.md) | Framework-specific | Django, FastAPI, Laravel, Go, SvelteKit |
