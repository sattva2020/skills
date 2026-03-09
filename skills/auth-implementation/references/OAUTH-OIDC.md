# OAuth 2.0 & OpenID Connect

Comprehensive guide to OAuth 2.0 flows, OIDC, and SaaS auth provider integration.

## OAuth 2.0 Overview

OAuth 2.0 is an **authorization** framework. It lets users grant limited access to their resources on one service to another service, without sharing credentials.

### Roles

| Role | Description | Example |
|------|-------------|---------|
| Resource Owner | The user | End user |
| Client | Your application | Your web app |
| Authorization Server | Issues tokens | Google, GitHub |
| Resource Server | Holds protected resources | Google API, GitHub API |

## Authorization Code Flow + PKCE

**Recommended for all clients** (web, mobile, SPA). PKCE prevents authorization code interception.

```
┌──────┐                                    ┌─────────────┐
│Client│                                    │Auth Server   │
└──┬───┘                                    └──────┬──────┘
   │  1. Generate code_verifier + code_challenge   │
   │  2. Redirect to /authorize                    │
   │─────────────────────────────────────────────►│
   │                                               │
   │  3. User authenticates + consents             │
   │                                               │
   │  4. Redirect back with authorization code     │
   │◄─────────────────────────────────────────────│
   │                                               │
   │  5. POST /token with code + code_verifier     │
   │─────────────────────────────────────────────►│
   │                                               │
   │  6. Returns access_token + id_token           │
   │◄─────────────────────────────────────────────│
```

### PKCE Implementation

```typescript
import crypto from 'crypto';

function generateCodeVerifier(): string {
  return crypto.randomBytes(32).toString('base64url');
}

function generateCodeChallenge(verifier: string): string {
  return crypto.createHash('sha256').update(verifier).digest('base64url');
}

// Step 1: Create authorization URL
function getAuthorizationUrl(provider: OAuthProvider) {
  const state = crypto.randomBytes(16).toString('hex');
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = generateCodeChallenge(codeVerifier);

  // Store state + codeVerifier in session/cookie
  const url = new URL(provider.authorizationEndpoint);
  url.searchParams.set('client_id', provider.clientId);
  url.searchParams.set('redirect_uri', provider.redirectUri);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('scope', provider.scopes.join(' '));
  url.searchParams.set('state', state);
  url.searchParams.set('code_challenge', codeChallenge);
  url.searchParams.set('code_challenge_method', 'S256');

  return { url: url.toString(), state, codeVerifier };
}

// Step 2: Exchange code for tokens
async function exchangeCode(code: string, codeVerifier: string, provider: OAuthProvider) {
  const response = await fetch(provider.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: provider.redirectUri,
      client_id: provider.clientId,
      client_secret: provider.clientSecret,
      code_verifier: codeVerifier,
    }),
  });

  return response.json();
  // Returns: { access_token, token_type, expires_in, refresh_token, id_token, scope }
}
```

### State Parameter (CSRF Protection)

**Always use `state`** to prevent CSRF attacks:

```typescript
// Before redirect: generate and store state
const state = crypto.randomBytes(16).toString('hex');
cookies.set('oauth_state', state, { httpOnly: true, maxAge: 600 });

// In callback: verify state matches
const storedState = cookies.get('oauth_state');
const returnedState = searchParams.get('state');
if (!storedState || storedState !== returnedState) {
  throw new Error('Invalid state parameter');
}
```

## Client Credentials Flow

**For machine-to-machine** (no user involved). Service authenticates as itself.

```typescript
async function getM2MToken(clientId: string, clientSecret: string, tokenEndpoint: string) {
  const response = await fetch(tokenEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString('base64')}`,
    },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      scope: 'read:data write:data',
    }),
  });

  return response.json();
  // Returns: { access_token, token_type, expires_in }
}
```

## Device Authorization Flow

**For devices without browsers** (smart TV, CLI tools, IoT).

```typescript
// Step 1: Request device code
const deviceResponse = await fetch('https://oauth2.example.com/device/code', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    client_id: CLIENT_ID,
    scope: 'openid profile email',
  }),
});
const { device_code, user_code, verification_uri, interval } = await deviceResponse.json();

// Step 2: Show user_code and verification_uri to user
console.log(`Go to ${verification_uri} and enter code: ${user_code}`);

// Step 3: Poll for token
async function pollForToken(deviceCode: string, interval: number) {
  while (true) {
    await new Promise(resolve => setTimeout(resolve, interval * 1000));
    const response = await fetch('https://oauth2.example.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
        client_id: CLIENT_ID,
        device_code: deviceCode,
      }),
    });
    const data = await response.json();
    if (data.access_token) return data;
    if (data.error === 'expired_token') throw new Error('Device code expired');
    // 'authorization_pending' or 'slow_down' → keep polling
  }
}
```

## OpenID Connect (OIDC)

OIDC is an **identity** layer on top of OAuth 2.0. It adds:
- **ID Token** — JWT with user identity claims
- **UserInfo endpoint** — get user profile data
- **Discovery** — `.well-known/openid-configuration`

### ID Token Claims

```json
{
  "iss": "https://accounts.google.com",
  "sub": "110169484474386276334",
  "aud": "your-client-id",
  "exp": 1700000900,
  "iat": 1700000000,
  "nonce": "abc123",
  "email": "user@gmail.com",
  "email_verified": true,
  "name": "John Doe",
  "picture": "https://..."
}
```

### Nonce (Replay Protection)

```typescript
// Before redirect
const nonce = crypto.randomBytes(16).toString('hex');
cookies.set('oauth_nonce', nonce, { httpOnly: true, maxAge: 600 });
// Add to authorization URL: &nonce=...

// In callback: verify nonce in ID token
import { jwtVerify } from 'jose';
const { payload } = await jwtVerify(idToken, publicKey);
if (payload.nonce !== cookies.get('oauth_nonce')) {
  throw new Error('Invalid nonce');
}
```

### Discovery Document

```typescript
async function getOIDCConfig(issuer: string) {
  const response = await fetch(`${issuer}/.well-known/openid-configuration`);
  return response.json();
  // Returns: { authorization_endpoint, token_endpoint, userinfo_endpoint, jwks_uri, ... }
}

// Google: https://accounts.google.com/.well-known/openid-configuration
// Microsoft: https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration
```

### UserInfo Endpoint

```typescript
async function getUserInfo(accessToken: string, userInfoEndpoint: string) {
  const response = await fetch(userInfoEndpoint, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.json();
  // Returns: { sub, name, email, picture, ... }
}
```

## Provider Setup

### Google

```
Authorization: https://accounts.google.com/o/oauth2/v2/auth
Token:         https://oauth2.googleapis.com/token
UserInfo:      https://openidconnect.googleapis.com/v1/userinfo
Scopes:        openid email profile
Console:       https://console.cloud.google.com/apis/credentials
```

```typescript
const googleConfig = {
  clientId: process.env.GOOGLE_CLIENT_ID!,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
  authorizationEndpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
  tokenEndpoint: 'https://oauth2.googleapis.com/token',
  redirectUri: `${process.env.APP_URL}/api/auth/callback/google`,
  scopes: ['openid', 'email', 'profile'],
};
```

### GitHub

```
Authorization: https://github.com/login/oauth/authorize
Token:         https://github.com/login/oauth/access_token
User API:      https://api.github.com/user
Emails API:    https://api.github.com/user/emails
Scopes:        user:email read:user
Console:       https://github.com/settings/developers
```

Note: GitHub doesn't support OIDC. Use the User API instead.

```typescript
// Get user after OAuth
const user = await fetch('https://api.github.com/user', {
  headers: { Authorization: `Bearer ${accessToken}`, Accept: 'application/json' },
}).then(r => r.json());

// Get primary email
const emails = await fetch('https://api.github.com/user/emails', {
  headers: { Authorization: `Bearer ${accessToken}`, Accept: 'application/json' },
}).then(r => r.json());
const primaryEmail = emails.find(e => e.primary)?.email;
```

### Apple

```
Authorization: https://appleid.apple.com/auth/authorize
Token:         https://appleid.apple.com/auth/token
Scopes:        name email
Console:       https://developer.apple.com/account/resources/identifiers
```

Apple-specific requirements:
- Generate client secret as JWT signed with your private key
- User info (name, email) only sent on first authorization
- Must store name from first auth — Apple won't send it again

### Microsoft / Azure AD

```
Authorization: https://login.microsoftonline.com/{tenant}/oauth2/v2/authorize
Token:         https://login.microsoftonline.com/{tenant}/oauth2/v2/token
Scopes:        openid email profile User.Read
Console:       https://portal.azure.com → App registrations
```

Tenant options: `common` (any), `organizations` (work/school), `consumers` (personal), or specific tenant ID.

### Discord

```
Authorization: https://discord.com/api/oauth2/authorize
Token:         https://discord.com/api/oauth2/token
User API:      https://discord.com/api/users/@me
Scopes:        identify email
Console:       https://discord.com/developers/applications
```

## SaaS Auth Providers

### Clerk

Fully managed auth with pre-built UI components.

```bash
npm install @clerk/nextjs
```

```typescript
// .env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...

// app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs';

export default function RootLayout({ children }) {
  return (
    <ClerkProvider>
      <html><body>{children}</body></html>
    </ClerkProvider>
  );
}

// middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

const isProtectedRoute = createRouteMatcher(['/dashboard(.*)']);

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) await auth.protect();
});

export const config = {
  matcher: ['/((?!.*\\..*|_next).*)', '/', '/(api|trpc)(.*)'],
};

// Client component
import { useUser, SignInButton, UserButton } from '@clerk/nextjs';

export function Header() {
  const { isSignedIn, user } = useUser();
  return isSignedIn ? <UserButton /> : <SignInButton />;
}
```

### Auth0

```bash
npm install @auth0/nextjs-auth0
```

```typescript
// .env
AUTH0_SECRET=<random-32-chars>
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://your-tenant.auth0.com
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...

// app/api/auth/[auth0]/route.ts
import { handleAuth } from '@auth0/nextjs-auth0';
export const GET = handleAuth();

// app/layout.tsx
import { UserProvider } from '@auth0/nextjs-auth0/client';
export default function RootLayout({ children }) {
  return <UserProvider>{children}</UserProvider>;
}

// Server component
import { getSession } from '@auth0/nextjs-auth0';
export default async function Dashboard() {
  const session = await getSession();
  if (!session) redirect('/api/auth/login');
  return <div>Welcome, {session.user.name}</div>;
}

// Client component
import { useUser } from '@auth0/nextjs-auth0/client';
export function Profile() {
  const { user, isLoading } = useUser();
  if (isLoading) return <div>Loading...</div>;
  return user ? <div>{user.name}</div> : <a href="/api/auth/login">Login</a>;
}
```

### Supabase Auth

```bash
npm install @supabase/supabase-js @supabase/ssr
```

```typescript
// lib/supabase/server.ts (Next.js App Router)
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll(); },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        },
      },
    },
  );
}

// Sign up
const supabase = await createClient();
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123',
});

// Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123',
});

// OAuth
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: { redirectTo: `${origin}/auth/callback` },
});

// Get session
const { data: { session } } = await supabase.auth.getSession();
```

### Firebase Auth

```bash
npm install firebase firebase-admin
```

```typescript
// Client-side
import { getAuth, signInWithPopup, GoogleAuthProvider } from 'firebase/auth';
import { initializeApp } from 'firebase/app';

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Google sign-in
const provider = new GoogleAuthProvider();
const result = await signInWithPopup(auth, provider);
const user = result.user;
const idToken = await user.getIdToken();

// Send idToken to your backend for verification

// Server-side verification
import { getAuth } from 'firebase-admin/auth';

async function verifyFirebaseToken(idToken: string) {
  const decodedToken = await getAuth().verifyIdToken(idToken);
  return decodedToken; // { uid, email, ... }
}
```

## Linking Multiple Providers

When a user signs in with different providers using the same email:

```typescript
async function findOrCreateUser(provider: string, providerAccountId: string, email: string, name: string) {
  // Check if OAuth account exists
  const existingAccount = await prisma.oAuthAccount.findUnique({
    where: { provider_providerAccountId: { provider, providerAccountId } },
    include: { user: true },
  });
  if (existingAccount) return existingAccount.user;

  // Check if user with same email exists (link accounts)
  const existingUser = await prisma.user.findUnique({ where: { email } });
  if (existingUser) {
    await prisma.oAuthAccount.create({
      data: { userId: existingUser.id, provider, providerAccountId },
    });
    return existingUser;
  }

  // Create new user + account
  return prisma.user.create({
    data: {
      email,
      name,
      emailVerified: true,
      oauthAccounts: {
        create: { provider, providerAccountId },
      },
    },
  });
}
```

## Security Considerations

1. **Always validate `state` parameter** — prevents CSRF
2. **Always use PKCE** — prevents authorization code interception
3. **Validate `nonce` in ID tokens** — prevents replay attacks
4. **Validate `iss` and `aud` in ID tokens** — prevents token injection
5. **Use exact redirect URI matching** — prevents open redirects
6. **Store tokens securely** — access tokens in memory, refresh tokens in HttpOnly cookies
7. **Check `email_verified` claim** — don't trust unverified emails for account linking
8. **Implement proper logout** — revoke tokens at provider, clear local session

## Common Issues

| Issue | Solution |
|-------|----------|
| Redirect URI mismatch | Must match exactly (including trailing slash, http vs https) |
| CORS errors on token endpoint | Token exchange must happen server-side |
| ID token validation fails | Check clock skew, verify with provider's JWKS |
| Email not returned | Request correct scopes (e.g., GitHub needs `user:email`) |
| `state` mismatch | Ensure cookies are not blocked (SameSite, third-party) |
