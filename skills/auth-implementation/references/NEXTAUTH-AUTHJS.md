# Auth.js v5 (NextAuth) — Next.js App Router

Complete guide for Auth.js v5 with Next.js App Router (14+).

## Installation

```bash
npm install next-auth@beta
# For database adapter (pick one):
npm install @auth/prisma-adapter @prisma/client prisma
npm install @auth/drizzle-adapter
npm install @auth/typeorm-adapter
```

## Core Configuration

### auth.ts (root)

```typescript
import NextAuth from 'next-auth';
import Google from 'next-auth/providers/google';
import GitHub from 'next-auth/providers/github';
import Credentials from 'next-auth/providers/credentials';
import { PrismaAdapter } from '@auth/prisma-adapter';
import { prisma } from '@/lib/prisma';
import bcrypt from 'bcryptjs';

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(prisma),
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
    Credentials({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const user = await prisma.user.findUnique({
          where: { email: credentials.email as string },
        });
        if (!user?.passwordHash) return null;

        const isValid = await bcrypt.compare(
          credentials.password as string,
          user.passwordHash,
        );
        if (!isValid) return null;

        return { id: user.id, email: user.email, name: user.name, role: user.role };
      },
    }),
  ],
  session: {
    strategy: 'jwt', // 'jwt' or 'database'
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  pages: {
    signIn: '/login',
    error: '/login',
    newUser: '/onboarding',
  },
  callbacks: {
    async jwt({ token, user, trigger, session }) {
      if (user) {
        token.id = user.id;
        token.role = user.role;
      }
      // Handle session update (e.g., after profile change)
      if (trigger === 'update' && session) {
        token.name = session.name;
      }
      return token;
    },
    async session({ session, token }) {
      session.user.id = token.id as string;
      session.user.role = token.role as string;
      return session;
    },
    async signIn({ user, account, profile }) {
      // Block sign-in for unverified emails (OAuth)
      if (account?.provider === 'google' && !profile?.email_verified) {
        return false;
      }
      return true;
    },
    async redirect({ url, baseUrl }) {
      // Allow relative URLs and same-origin
      if (url.startsWith('/')) return `${baseUrl}${url}`;
      if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
  },
});
```

### Environment Variables

```env
AUTH_SECRET=<random-32-char-string>  # npx auth secret
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
DATABASE_URL=postgresql://...
```

### Route Handler

```typescript
// app/api/auth/[...nextauth]/route.ts
import { handlers } from '@/auth';
export const { GET, POST } = handlers;
```

## Type Extensions

```typescript
// types/next-auth.d.ts
import { DefaultSession } from 'next-auth';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      role: string;
    } & DefaultSession['user'];
  }

  interface User {
    role?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id: string;
    role: string;
  }
}
```

## Providers

### Google

```typescript
import Google from 'next-auth/providers/google';

Google({
  clientId: process.env.GOOGLE_CLIENT_ID!,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
  authorization: {
    params: {
      prompt: 'consent',
      access_type: 'offline',
      response_type: 'code',
    },
  },
})
```

Console: https://console.cloud.google.com/apis/credentials
Redirect URI: `http://localhost:3000/api/auth/callback/google`

### GitHub

```typescript
import GitHub from 'next-auth/providers/github';

GitHub({
  clientId: process.env.GITHUB_CLIENT_ID!,
  clientSecret: process.env.GITHUB_CLIENT_SECRET!,
})
```

Console: https://github.com/settings/developers
Redirect URI: `http://localhost:3000/api/auth/callback/github`

### Discord

```typescript
import Discord from 'next-auth/providers/discord';

Discord({
  clientId: process.env.DISCORD_CLIENT_ID!,
  clientSecret: process.env.DISCORD_CLIENT_SECRET!,
})
```

### Apple

```typescript
import Apple from 'next-auth/providers/apple';

Apple({
  clientId: process.env.APPLE_CLIENT_ID!,
  clientSecret: process.env.APPLE_CLIENT_SECRET!,
})
```

Note: Apple requires a paid developer account and specific key configuration.

### Credentials (Email + Password)

Already shown in core config. Key points:
- Credentials provider does NOT work with database sessions (use JWT strategy)
- You must handle password hashing yourself
- No built-in signup — implement separately

## Database Adapters

### Prisma Adapter

```typescript
import { PrismaAdapter } from '@auth/prisma-adapter';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();
// In NextAuth config:
adapter: PrismaAdapter(prisma),
```

Required Prisma schema — see DATABASE-SCHEMAS.md for full schema.

### Drizzle Adapter

```typescript
import { DrizzleAdapter } from '@auth/drizzle-adapter';
import { db } from '@/lib/db';

// In NextAuth config:
adapter: DrizzleAdapter(db),
```

## Session Strategies

### JWT Strategy (default)

```typescript
session: {
  strategy: 'jwt',
  maxAge: 30 * 24 * 60 * 60,
}
```

- Session data stored in encrypted JWT cookie
- No database calls on every request
- Cannot revoke individual sessions (use short expiry + refresh)
- Works with all providers including Credentials

### Database Strategy

```typescript
session: {
  strategy: 'database',
  maxAge: 30 * 24 * 60 * 60,
}
```

- Session stored in database, cookie holds session ID
- Can revoke sessions by deleting from DB
- Requires database adapter
- Does NOT work with Credentials provider

## Route Protection

### Middleware (recommended for page protection)

```typescript
// middleware.ts
import { auth } from '@/auth';

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const isOnDashboard = req.nextUrl.pathname.startsWith('/dashboard');
  const isOnAuth = req.nextUrl.pathname.startsWith('/login');

  if (isOnDashboard && !isLoggedIn) {
    return Response.redirect(new URL('/login', req.nextUrl));
  }
  if (isOnAuth && isLoggedIn) {
    return Response.redirect(new URL('/dashboard', req.nextUrl));
  }
});

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

### Server Component

```typescript
import { auth } from '@/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect('/login');

  return <div>Welcome, {session.user.name}</div>;
}
```

### Server Action

```typescript
'use server';
import { auth } from '@/auth';

export async function updateProfile(formData: FormData) {
  const session = await auth();
  if (!session) throw new Error('Unauthorized');

  // ... update logic
}
```

### API Route Handler

```typescript
// app/api/protected/route.ts
import { auth } from '@/auth';

export const GET = auth(async function GET(req) {
  if (!req.auth) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }
  return Response.json({ data: 'protected data' });
});
```

## Custom Sign-In Page

```typescript
// app/login/page.tsx
import { signIn } from '@/auth';

export default function LoginPage() {
  return (
    <div>
      <form
        action={async (formData) => {
          'use server';
          await signIn('credentials', {
            email: formData.get('email'),
            password: formData.get('password'),
            redirectTo: '/dashboard',
          });
        }}
      >
        <input name="email" type="email" required />
        <input name="password" type="password" required />
        <button type="submit">Sign In</button>
      </form>

      <form
        action={async () => {
          'use server';
          await signIn('google', { redirectTo: '/dashboard' });
        }}
      >
        <button type="submit">Sign in with Google</button>
      </form>

      <form
        action={async () => {
          'use server';
          await signIn('github', { redirectTo: '/dashboard' });
        }}
      >
        <button type="submit">Sign in with GitHub</button>
      </form>
    </div>
  );
}
```

## Sign Out

```typescript
// Server Component
import { signOut } from '@/auth';

export function SignOutButton() {
  return (
    <form
      action={async () => {
        'use server';
        await signOut({ redirectTo: '/' });
      }}
    >
      <button type="submit">Sign Out</button>
    </form>
  );
}
```

## Client-Side Session Access

```typescript
// app/layout.tsx — wrap with SessionProvider
import { SessionProvider } from 'next-auth/react';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}

// Client component
'use client';
import { useSession, signIn, signOut } from 'next-auth/react';

export function UserMenu() {
  const { data: session, status } = useSession();

  if (status === 'loading') return <div>Loading...</div>;
  if (!session) return <button onClick={() => signIn()}>Sign In</button>;

  return (
    <div>
      <span>{session.user.name}</span>
      <button onClick={() => signOut()}>Sign Out</button>
    </div>
  );
}
```

## Extending Session with Role

The callbacks in the core config already show this. Summary:

1. Add `role` field to User model in database
2. In `jwt` callback: copy `user.role` to `token.role`
3. In `session` callback: copy `token.role` to `session.user.role`
4. Extend TypeScript types (see Type Extensions section)

## Signup Flow

Auth.js v5 does NOT provide built-in signup. Implement as a Server Action:

```typescript
'use server';
import bcrypt from 'bcryptjs';
import { prisma } from '@/lib/prisma';
import { signIn } from '@/auth';

export async function signUp(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const name = formData.get('name') as string;

  // Validate
  if (!email || !password || password.length < 8) {
    return { error: 'Invalid input' };
  }

  // Check existing
  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) {
    return { error: 'Email already registered' };
  }

  // Create user
  const passwordHash = await bcrypt.hash(password, 12);
  await prisma.user.create({
    data: { email, passwordHash, name, role: 'user' },
  });

  // Auto sign in
  await signIn('credentials', { email, password, redirectTo: '/dashboard' });
}
```

## Common Issues

| Issue | Solution |
|-------|----------|
| `NEXTAUTH_URL` not set | Set `AUTH_URL` in env (v5 uses `AUTH_URL`) |
| Credentials + database strategy | Use JWT strategy with Credentials provider |
| Session is null in middleware | Ensure `auth` wrapper is used correctly |
| OAuth redirect mismatch | Check callback URL matches provider console |
| Type errors on session.user | Add type declarations (see Type Extensions) |
| CSRF token mismatch | Ensure `AUTH_SECRET` is set and stable |

## Migration from v4 to v5

Key changes:
- `next-auth` → `next-auth@beta` (v5)
- `[...nextauth].ts` → `auth.ts` at root + route handler
- `getServerSession()` → `auth()`
- `NEXTAUTH_SECRET` → `AUTH_SECRET`
- `NEXTAUTH_URL` → `AUTH_URL`
- Middleware uses `auth()` wrapper instead of `withAuth()`
- `unstable_getServerSession` → just `auth()`
