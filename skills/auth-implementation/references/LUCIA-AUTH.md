# Lucia v3 — Session-Based Auth

Lucia v3 is a session library (not a full auth framework). You own the auth logic; Lucia handles session creation, validation, and invalidation.

> **Note:** Lucia v3 is in maintenance mode as of late 2024. The author recommends implementing sessions yourself using Lucia's patterns. This guide covers both Lucia v3 and the DIY approach.

## Installation

```bash
npm install lucia
# For OAuth:
npm install arctic
# Database adapter (pick one):
npm install @lucia-auth/adapter-prisma
npm install @lucia-auth/adapter-drizzle
npm install @lucia-auth/adapter-postgresql
npm install @lucia-auth/adapter-mysql
npm install @lucia-auth/adapter-sqlite
```

## Core Concepts

- **Lucia creates and validates sessions** — stored in your database
- **You handle authentication** — password verification, OAuth, etc.
- **Sessions are cookie-based** — no JWTs
- **Arctic** — companion library for OAuth providers

## Setup

### Initialize Lucia

```typescript
// lib/auth.ts
import { Lucia } from 'lucia';
import { PrismaAdapter } from '@lucia-auth/adapter-prisma';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const adapter = new PrismaAdapter(prisma.session, prisma.user);

export const lucia = new Lucia(adapter, {
  sessionCookie: {
    attributes: {
      secure: process.env.NODE_ENV === 'production',
    },
  },
  getUserAttributes: (attributes) => {
    return {
      email: attributes.email,
      name: attributes.name,
      role: attributes.role,
    };
  },
});

// Type declarations
declare module 'lucia' {
  interface Register {
    Lucia: typeof lucia;
    DatabaseUserAttributes: {
      email: string;
      name: string;
      role: string;
    };
  }
}
```

### Database Schema (Prisma)

```prisma
model User {
  id           String    @id @default(cuid())
  email        String    @unique
  passwordHash String?
  name         String?
  role         String    @default("user")
  sessions     Session[]
  oauthAccounts OAuthAccount[]
  createdAt    DateTime  @default(now())
}

model Session {
  id        String   @id
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  expiresAt DateTime
  @@index([userId])
}

model OAuthAccount {
  id                String @id @default(cuid())
  userId            String
  user              User   @relation(fields: [userId], references: [id], onDelete: Cascade)
  provider          String
  providerAccountId String
  @@unique([provider, providerAccountId])
  @@index([userId])
}
```

### Drizzle Adapter

```typescript
import { DrizzlePostgreSQLAdapter } from '@lucia-auth/adapter-drizzle';
import { db } from './db';
import { userTable, sessionTable } from './schema';

const adapter = new DrizzlePostgreSQLAdapter(db, sessionTable, userTable);
```

## Email/Password Authentication

### Sign Up

```typescript
import { hash } from '@node-rs/argon2'; // or bcrypt
import { generateIdFromEntropySize } from 'lucia';

async function signUp(email: string, password: string, name: string) {
  // Validate input
  if (!email || !password || password.length < 8) {
    throw new Error('Invalid input');
  }

  // Check existing user
  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) throw new Error('Email already registered');

  // Hash password
  const passwordHash = await hash(password, {
    memoryCost: 19456,
    timeCost: 2,
    outputLen: 32,
    parallelism: 1,
  });

  // Create user
  const userId = generateIdFromEntropySize(10);
  const user = await prisma.user.create({
    data: { id: userId, email, passwordHash, name },
  });

  // Create session
  const session = await lucia.createSession(userId, {});
  const sessionCookie = lucia.createSessionCookie(session.id);

  return { user, sessionCookie };
}
```

### Sign In

```typescript
import { verify } from '@node-rs/argon2';

async function signIn(email: string, password: string) {
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user || !user.passwordHash) {
    throw new Error('Invalid credentials'); // Same message for both cases
  }

  const validPassword = await verify(user.passwordHash, password);
  if (!validPassword) {
    throw new Error('Invalid credentials');
  }

  const session = await lucia.createSession(user.id, {});
  const sessionCookie = lucia.createSessionCookie(session.id);

  return { user, sessionCookie };
}
```

### Sign Out

```typescript
async function signOut(sessionId: string) {
  await lucia.invalidateSession(sessionId);
  const blankCookie = lucia.createBlankSessionCookie();
  return blankCookie;
}
```

## Session Validation

### Next.js App Router

```typescript
// lib/auth.ts
import { cookies } from 'next/headers';
import { cache } from 'react';

export const validateRequest = cache(async () => {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(lucia.sessionCookieName)?.value ?? null;

  if (!sessionId) return { user: null, session: null };

  const result = await lucia.validateSession(sessionId);

  try {
    if (result.session?.fresh) {
      const sessionCookie = lucia.createSessionCookie(result.session.id);
      cookieStore.set(sessionCookie.name, sessionCookie.value, sessionCookie.attributes);
    }
    if (!result.session) {
      const blankCookie = lucia.createBlankSessionCookie();
      cookieStore.set(blankCookie.name, blankCookie.value, blankCookie.attributes);
    }
  } catch {
    // Can't set cookies in Server Components (only in Server Actions/Route Handlers)
  }

  return result;
});
```

### Usage in Server Components

```typescript
import { validateRequest } from '@/lib/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const { user } = await validateRequest();
  if (!user) redirect('/login');

  return <div>Welcome, {user.name}</div>;
}
```

### Express Middleware

```typescript
import { verifyRequestOrigin } from 'lucia';

// CSRF protection
app.use((req, res, next) => {
  if (req.method !== 'GET') {
    const originHeader = req.headers.origin;
    const hostHeader = req.headers.host;
    if (!originHeader || !hostHeader || !verifyRequestOrigin(originHeader, [hostHeader])) {
      return res.status(403).end();
    }
  }
  next();
});

// Session validation
app.use(async (req, res, next) => {
  const sessionId = lucia.readSessionCookie(req.headers.cookie ?? '');
  if (!sessionId) {
    res.locals.user = null;
    res.locals.session = null;
    return next();
  }

  const { session, user } = await lucia.validateSession(sessionId);
  if (session?.fresh) {
    res.appendHeader('Set-Cookie', lucia.createSessionCookie(session.id).serialize());
  }
  if (!session) {
    res.appendHeader('Set-Cookie', lucia.createBlankSessionCookie().serialize());
  }

  res.locals.user = user;
  res.locals.session = session;
  next();
});
```

### SvelteKit

```typescript
// src/hooks.server.ts
import { lucia } from '$lib/server/auth';
import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
  const sessionId = event.cookies.get(lucia.sessionCookieName);
  if (!sessionId) {
    event.locals.user = null;
    event.locals.session = null;
    return resolve(event);
  }

  const { session, user } = await lucia.validateSession(sessionId);
  if (session?.fresh) {
    const sessionCookie = lucia.createSessionCookie(session.id);
    event.cookies.set(sessionCookie.name, sessionCookie.value, {
      path: '.',
      ...sessionCookie.attributes,
    });
  }
  if (!session) {
    const blankCookie = lucia.createBlankSessionCookie();
    event.cookies.set(blankCookie.name, blankCookie.value, {
      path: '.',
      ...blankCookie.attributes,
    });
  }

  event.locals.user = user;
  event.locals.session = session;
  return resolve(event);
};
```

## OAuth with Arctic

Arctic is Lucia's companion library for OAuth.

### Setup Google OAuth

```typescript
import { Google } from 'arctic';

export const google = new Google(
  process.env.GOOGLE_CLIENT_ID!,
  process.env.GOOGLE_CLIENT_SECRET!,
  process.env.GOOGLE_REDIRECT_URI!,
);
```

### OAuth Flow (Next.js)

```typescript
// app/api/auth/google/route.ts — Redirect to Google
import { generateState, generateCodeVerifier } from 'arctic';
import { google } from '@/lib/oauth';
import { cookies } from 'next/headers';

export async function GET() {
  const state = generateState();
  const codeVerifier = generateCodeVerifier();
  const url = google.createAuthorizationURL(state, codeVerifier, ['openid', 'email', 'profile']);

  const cookieStore = await cookies();
  cookieStore.set('google_oauth_state', state, { path: '/', httpOnly: true, maxAge: 600 });
  cookieStore.set('google_code_verifier', codeVerifier, { path: '/', httpOnly: true, maxAge: 600 });

  return Response.redirect(url);
}

// app/api/auth/google/callback/route.ts — Handle callback
import { google } from '@/lib/oauth';
import { lucia } from '@/lib/auth';
import { cookies } from 'next/headers';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');

  const cookieStore = await cookies();
  const storedState = cookieStore.get('google_oauth_state')?.value;
  const codeVerifier = cookieStore.get('google_code_verifier')?.value;

  if (!code || !state || !storedState || state !== storedState || !codeVerifier) {
    return new Response('Invalid request', { status: 400 });
  }

  const tokens = await google.validateAuthorizationCode(code, codeVerifier);
  const googleUser = await fetch('https://openidconnect.googleapis.com/v1/userinfo', {
    headers: { Authorization: `Bearer ${tokens.accessToken()}` },
  }).then(r => r.json());

  // Find or create user
  const existingAccount = await prisma.oAuthAccount.findUnique({
    where: { provider_providerAccountId: { provider: 'google', providerAccountId: googleUser.sub } },
  });

  let userId: string;
  if (existingAccount) {
    userId = existingAccount.userId;
  } else {
    const user = await prisma.user.create({
      data: {
        email: googleUser.email,
        name: googleUser.name,
        oauthAccounts: {
          create: { provider: 'google', providerAccountId: googleUser.sub },
        },
      },
    });
    userId = user.id;
  }

  const session = await lucia.createSession(userId, {});
  const sessionCookie = lucia.createSessionCookie(session.id);
  cookieStore.set(sessionCookie.name, sessionCookie.value, sessionCookie.attributes);

  return Response.redirect(new URL('/dashboard', request.url));
}
```

### Available Arctic Providers

Google, GitHub, Apple, Discord, Microsoft, Spotify, Twitter, Facebook, LinkedIn, Slack, GitLab, Bitbucket, and many more.

```typescript
import { GitHub, Discord, Apple } from 'arctic';
```

## DIY Sessions (Post-Lucia Pattern)

If not using Lucia library, implement sessions directly:

```typescript
import { sha256 } from '@oslojs/crypto/sha2';
import { encodeBase32LowerCaseNoPadding, encodeHexLowerCase } from '@oslojs/encoding';

function generateSessionToken(): string {
  const bytes = new Uint8Array(20);
  crypto.getRandomValues(bytes);
  return encodeBase32LowerCaseNoPadding(bytes);
}

async function createSession(token: string, userId: string) {
  const sessionId = encodeHexLowerCase(sha256(new TextEncoder().encode(token)));
  const session = await prisma.session.create({
    data: {
      id: sessionId,
      userId,
      expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 30), // 30 days
    },
  });
  return session;
}

async function validateSessionToken(token: string) {
  const sessionId = encodeHexLowerCase(sha256(new TextEncoder().encode(token)));
  const session = await prisma.session.findUnique({
    where: { id: sessionId },
    include: { user: true },
  });

  if (!session) return { session: null, user: null };
  if (Date.now() >= session.expiresAt.getTime()) {
    await prisma.session.delete({ where: { id: sessionId } });
    return { session: null, user: null };
  }

  // Extend session if close to expiry (within 15 days)
  if (Date.now() >= session.expiresAt.getTime() - 1000 * 60 * 60 * 24 * 15) {
    session.expiresAt = new Date(Date.now() + 1000 * 60 * 60 * 24 * 30);
    await prisma.session.update({
      where: { id: sessionId },
      data: { expiresAt: session.expiresAt },
    });
  }

  return { session, user: session.user };
}

async function invalidateSession(sessionId: string) {
  await prisma.session.delete({ where: { id: sessionId } });
}
```

## Password Hashing

Lucia recommends Argon2id (via `@node-rs/argon2`):

```typescript
import { hash, verify } from '@node-rs/argon2';

// Hash
const passwordHash = await hash(password, {
  memoryCost: 19456,  // 19 MiB
  timeCost: 2,
  outputLen: 32,
  parallelism: 1,
});

// Verify
const isValid = await verify(passwordHash, password);
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Can't set cookies in Server Component | Use Server Actions or Route Handlers for cookie mutation |
| Session cookie not sent | Check `secure` flag (false in dev, true in prod) |
| `fresh` session property | When true, session was just extended — update cookie |
| Arctic OAuth state mismatch | Ensure state cookie is set before redirect |
| Lucia v3 deprecation | Lucia patterns still valid; use DIY approach section above |
