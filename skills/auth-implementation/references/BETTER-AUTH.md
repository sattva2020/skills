# Better Auth

Modern TypeScript auth library with plugin system. Works with Next.js, SvelteKit, Nuxt, Astro, Express, Hono.

## Installation

```bash
npm install better-auth
# Database driver (pick one):
npm install @prisma/client prisma
npm install drizzle-orm
npm install kysely
npm install better-sqlite3
```

## Core Setup

### auth.ts (server)

```typescript
import { betterAuth } from 'better-auth';
import { prismaAdapter } from 'better-auth/adapters/prisma';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export const auth = betterAuth({
  database: prismaAdapter(prisma, {
    provider: 'postgresql', // or 'mysql', 'sqlite'
  }),
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    maxPasswordLength: 128,
  },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    },
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    },
    discord: {
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: process.env.DISCORD_CLIENT_SECRET!,
    },
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // Update session every 24h
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60, // Cache for 5 minutes
    },
  },
});
```

### auth-client.ts (client)

```typescript
import { createAuthClient } from 'better-auth/react'; // or /svelte, /vue, /solid

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL!, // Base URL of your app
});

export const { signIn, signUp, signOut, useSession } = authClient;
```

### API Route (Next.js App Router)

```typescript
// app/api/auth/[...all]/route.ts
import { auth } from '@/lib/auth';
import { toNextJsHandler } from 'better-auth/next-js';

export const { GET, POST } = toNextJsHandler(auth);
```

### API Route (Express)

```typescript
import express from 'express';
import { toNodeHandler } from 'better-auth/node';
import { auth } from './auth';

const app = express();

// Mount Better Auth handler
app.all('/api/auth/*', toNodeHandler(auth));
```

### API Route (SvelteKit)

```typescript
// src/hooks.server.ts
import { auth } from '$lib/server/auth';
import { toSvelteKitHandler } from 'better-auth/svelte-kit';

export const handle = toSvelteKitHandler(auth);
```

## Database Setup

### Generate Schema

```bash
npx @better-auth/cli generate
# Or push directly:
npx @better-auth/cli migrate
```

### Prisma Schema (generated)

```prisma
model User {
  id            String    @id
  name          String
  email         String    @unique
  emailVerified Boolean   @default(false)
  image         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  sessions      Session[]
  accounts      Account[]
}

model Session {
  id        String   @id
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  token     String   @unique
  expiresAt DateTime
  ipAddress String?
  userAgent String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

model Account {
  id                String  @id
  userId            String
  user              User    @relation(fields: [userId], references: [id], onDelete: Cascade)
  accountId         String
  providerId        String
  accessToken       String?
  refreshToken      String?
  accessTokenExpiresAt  DateTime?
  refreshTokenExpiresAt DateTime?
  scope             String?
  idToken           String?
  password          String?
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt
}

model Verification {
  id         String   @id
  identifier String
  value      String
  expiresAt  DateTime
  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt
}
```

### Drizzle Adapter

```typescript
import { drizzleAdapter } from 'better-auth/adapters/drizzle';
import { db } from './db';

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: 'pg', // or 'mysql', 'sqlite'
  }),
  // ...
});
```

## Client-Side Usage

### React / Next.js

```typescript
'use client';
import { useSession, signIn, signUp, signOut } from '@/lib/auth-client';

export function AuthComponent() {
  const { data: session, isPending } = useSession();

  if (isPending) return <div>Loading...</div>;
  if (!session) {
    return (
      <div>
        <button onClick={() => signIn.social({ provider: 'google' })}>
          Sign in with Google
        </button>
        <button onClick={() => signIn.social({ provider: 'github' })}>
          Sign in with GitHub
        </button>
      </div>
    );
  }

  return (
    <div>
      <p>Welcome, {session.user.name}</p>
      <button onClick={() => signOut()}>Sign Out</button>
    </div>
  );
}
```

### Email/Password Sign In

```typescript
const { data, error } = await signIn.email({
  email: 'user@example.com',
  password: 'password123',
  callbackURL: '/dashboard',
});
```

### Email/Password Sign Up

```typescript
const { data, error } = await signUp.email({
  email: 'user@example.com',
  password: 'password123',
  name: 'John Doe',
  callbackURL: '/dashboard',
});
```

### Social Sign In

```typescript
await signIn.social({
  provider: 'google', // or 'github', 'discord', etc.
  callbackURL: '/dashboard',
});
```

## Server-Side Session Access

### Next.js Server Component

```typescript
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';

export default async function DashboardPage() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) redirect('/login');

  return <div>Welcome, {session.user.name}</div>;
}
```

### Next.js Middleware

```typescript
// middleware.ts
import { auth } from '@/lib/auth';
import { NextRequest, NextResponse } from 'next/server';

export async function middleware(request: NextRequest) {
  const session = await auth.api.getSession({
    headers: request.headers,
  });

  if (!session && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  return NextResponse.next();
}
```

## Plugins

Better Auth's plugin system extends functionality without bloating core.

### Two-Factor Authentication (2FA)

```typescript
import { betterAuth } from 'better-auth';
import { twoFactor } from 'better-auth/plugins';

export const auth = betterAuth({
  plugins: [
    twoFactor({
      issuer: 'MyApp',
      totpOptions: {
        digits: 6,
        period: 30,
      },
    }),
  ],
});
```

Client:
```typescript
import { createAuthClient } from 'better-auth/react';
import { twoFactorClient } from 'better-auth/client/plugins';

export const authClient = createAuthClient({
  plugins: [twoFactorClient()],
});

// Enable 2FA
await authClient.twoFactor.enable({ password: 'current-password' });
// Verify TOTP
await authClient.twoFactor.verifyTotp({ code: '123456' });
```

### Organizations

```typescript
import { organization } from 'better-auth/plugins';

export const auth = betterAuth({
  plugins: [
    organization({
      allowUserToCreateOrganization: true,
    }),
  ],
});
```

### Admin

```typescript
import { admin } from 'better-auth/plugins';

export const auth = betterAuth({
  plugins: [
    admin(), // Adds admin endpoints and role management
  ],
});
```

### API Keys

```typescript
import { apiKey } from 'better-auth/plugins';

export const auth = betterAuth({
  plugins: [
    apiKey({
      prefix: 'myapp_',
      expiresIn: 60 * 60 * 24 * 90, // 90 days
    }),
  ],
});
```

### Magic Link

```typescript
import { magicLink } from 'better-auth/plugins';

export const auth = betterAuth({
  plugins: [
    magicLink({
      sendMagicLink: async ({ email, url }) => {
        await sendEmail({ to: email, subject: 'Sign In', body: `Click: ${url}` });
      },
    }),
  ],
});
```

## Email Verification

```typescript
export const auth = betterAuth({
  emailVerification: {
    sendVerificationEmail: async ({ user, url }) => {
      await sendEmail({
        to: user.email,
        subject: 'Verify your email',
        body: `Click to verify: ${url}`,
      });
    },
    sendOnSignUp: true,
  },
});
```

## Password Reset

```typescript
export const auth = betterAuth({
  emailAndPassword: {
    enabled: true,
    sendResetPassword: async ({ user, url }) => {
      await sendEmail({
        to: user.email,
        subject: 'Reset Password',
        body: `Click to reset: ${url}`,
      });
    },
  },
});
```

Client:
```typescript
// Request reset
await authClient.forgetPassword({ email: 'user@example.com' });

// Reset with token (from URL)
await authClient.resetPassword({
  token: searchParams.get('token')!,
  newPassword: 'new-password123',
});
```

## Migration from NextAuth

Key differences:
- Better Auth uses its own schema (run `@better-auth/cli generate`)
- No adapter config needed — database is configured directly
- Client uses `createAuthClient()` instead of `SessionProvider` + `useSession()`
- Plugins replace NextAuth's callback-based customization
- Session includes more data by default (IP, user agent)

Migration steps:
1. Install `better-auth`, remove `next-auth`
2. Create `auth.ts` with Better Auth config
3. Replace route handler
4. Run schema migration
5. Update client code to use `createAuthClient()`
6. Update middleware

## Rate Limiting

```typescript
export const auth = betterAuth({
  rateLimit: {
    window: 60, // 60 seconds
    max: 10,    // max 10 requests per window
    customRules: {
      '/sign-in/email': { window: 60, max: 5 },
      '/sign-up/email': { window: 60, max: 3 },
      '/forget-password': { window: 3600, max: 3 },
    },
  },
});
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Database schema mismatch | Run `npx @better-auth/cli migrate` |
| CORS errors | Set `baseURL` correctly in client config |
| Session not persisting | Check cookie settings and `baseURL` |
| Plugin types not showing | Add plugin to both server and client configs |
| OAuth redirect error | Check callback URL: `{baseURL}/api/auth/callback/{provider}` |
