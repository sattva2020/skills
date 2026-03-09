# Custom JWT Authentication

Build your own JWT auth when existing libraries don't fit. **Read the warnings first.**

## When to Build Custom JWT

### DO build custom when:
- Microservice-to-microservice auth (no user sessions)
- Existing auth library doesn't support your framework
- You need full control over token format/claims
- API-only backend with no browser clients
- You're integrating with a legacy system that issues JWTs

### DON'T build custom when:
- Full-stack Next.js/SvelteKit app → use Auth.js, Better Auth, or Lucia
- Express with social login → use Passport.js
- You need OAuth/OIDC → use a library (Arctic, openid-client)
- You want managed auth → use Clerk, Auth0, Supabase Auth
- You're not sure → **use a library**

Building custom JWT auth means you own every security decision. Most auth vulnerabilities come from implementation mistakes, not library bugs.

## JWT Fundamentals

### Structure

```
header.payload.signature

Header:  { "alg": "HS256", "typ": "JWT" }
Payload: { "sub": "user123", "role": "admin", "iat": 1700000000, "exp": 1700000900 }
Signature: HMAC-SHA256(base64(header) + "." + base64(payload), secret)
```

### Algorithm Selection

| Algorithm | Type | Key | Use Case |
|-----------|------|-----|----------|
| HS256 | Symmetric | Shared secret | Single service, simple |
| RS256 | Asymmetric | RSA key pair | Multiple services, public verification |
| ES256 | Asymmetric | EC key pair | Multiple services, smaller tokens |
| EdDSA | Asymmetric | Ed25519 key pair | Modern, fast, small keys |

**Recommendation:** HS256 for single-service, RS256/ES256 for microservices.

### Standard Claims

| Claim | Name | Usage |
|-------|------|-------|
| `sub` | Subject | User ID |
| `iat` | Issued At | Token creation time |
| `exp` | Expiration | Token expiry time |
| `iss` | Issuer | Service that created the token |
| `aud` | Audience | Intended recipient service |
| `jti` | JWT ID | Unique token identifier (for revocation) |

## Token Architecture

```
┌─────────────────────────────────────────────┐
│  Access Token                                │
│  - Short-lived: 15 minutes                   │
│  - Contains: sub, role, permissions           │
│  - Transport: Authorization header OR cookie  │
│  - Storage: Memory (SPA) or HttpOnly cookie   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Refresh Token                               │
│  - Long-lived: 7-30 days                     │
│  - Contains: sub, jti, family                 │
│  - Transport: HttpOnly cookie (ALWAYS)        │
│  - Stored in DB: hash + family + expiry       │
│  - Rotated on every use                       │
└─────────────────────────────────────────────┘
```

## Implementation: Node.js (jose)

`jose` is the recommended JWT library for Node.js — it supports all runtimes (Node, Deno, Bun, Edge).

```bash
npm install jose
```

### Key Generation

```typescript
// HS256 — symmetric secret
const secret = new TextEncoder().encode(process.env.JWT_SECRET); // min 32 bytes

// RS256 — asymmetric key pair
import { generateKeyPair, exportSPKI, exportPKCS8 } from 'jose';

const { publicKey, privateKey } = await generateKeyPair('RS256');
const publicKeyPem = await exportSPKI(publicKey);
const privateKeyPem = await exportPKCS8(privateKey);
```

### Create Tokens

```typescript
import { SignJWT } from 'jose';
import crypto from 'crypto';

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

async function createAccessToken(userId: string, role: string): Promise<string> {
  return new SignJWT({ sub: userId, role })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('15m')
    .setIssuer('myapp')
    .setAudience('myapp')
    .sign(secret);
}

async function createRefreshToken(userId: string): Promise<{ token: string; jti: string }> {
  const jti = crypto.randomUUID();
  const token = new SignJWT({ sub: userId })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('7d')
    .setJti(jti)
    .sign(secret);

  return { token: await token, jti };
}
```

### Verify Tokens

```typescript
import { jwtVerify, errors } from 'jose';

async function verifyAccessToken(token: string) {
  try {
    const { payload } = await jwtVerify(token, secret, {
      issuer: 'myapp',
      audience: 'myapp',
    });
    return { valid: true, payload };
  } catch (err) {
    if (err instanceof errors.JWTExpired) {
      return { valid: false, error: 'expired' };
    }
    return { valid: false, error: 'invalid' };
  }
}
```

### Auth Middleware (Express)

```typescript
async function authMiddleware(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing token' });
  }

  const token = authHeader.slice(7);
  const result = await verifyAccessToken(token);

  if (!result.valid) {
    return res.status(401).json({ error: result.error });
  }

  req.user = {
    id: result.payload.sub as string,
    role: result.payload.role as string,
  };
  next();
}
```

### Auth Middleware (Next.js Route Handler)

```typescript
import { NextRequest, NextResponse } from 'next/server';

async function withAuth(
  request: NextRequest,
  handler: (req: NextRequest, user: TokenPayload) => Promise<NextResponse>,
) {
  const token = request.headers.get('Authorization')?.replace('Bearer ', '');
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const result = await verifyAccessToken(token);
  if (!result.valid) {
    return NextResponse.json({ error: result.error }, { status: 401 });
  }

  return handler(request, result.payload);
}
```

## Refresh Token Rotation

Rotate refresh tokens on every use. Detect reuse (token theft).

### Database Table

```sql
CREATE TABLE refresh_tokens (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  family     UUID NOT NULL,         -- Group of rotated tokens
  expires_at TIMESTAMPTZ NOT NULL,
  revoked    BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(family);
```

### Rotation Logic

```typescript
import crypto from 'crypto';

function hashToken(token: string): string {
  return crypto.createHash('sha256').update(token).digest('hex');
}

async function rotateRefreshToken(oldToken: string) {
  const oldHash = hashToken(oldToken);

  // Find existing token
  const existing = await prisma.refreshToken.findUnique({
    where: { tokenHash: oldHash },
  });

  if (!existing || existing.revoked || existing.expiresAt < new Date()) {
    // If revoked token is reused → potential theft → revoke entire family
    if (existing?.revoked) {
      await prisma.refreshToken.updateMany({
        where: { family: existing.family },
        data: { revoked: true },
      });
    }
    throw new Error('Invalid refresh token');
  }

  // Revoke old token
  await prisma.refreshToken.update({
    where: { id: existing.id },
    data: { revoked: true },
  });

  // Create new tokens
  const accessToken = await createAccessToken(existing.userId, /* role */);
  const { token: newRefreshToken, jti } = await createRefreshToken(existing.userId);

  // Store new refresh token with same family
  await prisma.refreshToken.create({
    data: {
      userId: existing.userId,
      tokenHash: hashToken(newRefreshToken),
      family: existing.family, // Same family for rotation detection
      expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
    },
  });

  return { accessToken, refreshToken: newRefreshToken };
}
```

### Refresh Endpoint

```typescript
app.post('/api/auth/refresh', async (req, res) => {
  const refreshToken = req.cookies.refresh_token;
  if (!refreshToken) {
    return res.status(401).json({ error: 'No refresh token' });
  }

  try {
    // Verify JWT signature first
    const { payload } = await jwtVerify(refreshToken, secret);

    // Then rotate
    const tokens = await rotateRefreshToken(refreshToken);

    // Set new refresh token cookie
    res.cookie('refresh_token', tokens.refreshToken, {
      httpOnly: true,
      secure: true,
      sameSite: 'strict',
      path: '/api/auth/refresh',
      maxAge: 7 * 24 * 60 * 60 * 1000,
    });

    res.json({ accessToken: tokens.accessToken });
  } catch (err) {
    res.clearCookie('refresh_token');
    res.status(401).json({ error: 'Invalid refresh token' });
  }
});
```

## Token Revocation (Blocklist)

For access tokens that need immediate revocation:

```typescript
// Redis blocklist (TTL = remaining token lifetime)
import { createClient } from 'redis';

const redis = createClient({ url: process.env.REDIS_URL });

async function revokeAccessToken(token: string, expiresAt: number) {
  const ttl = expiresAt - Math.floor(Date.now() / 1000);
  if (ttl > 0) {
    await redis.set(`blocklist:${token}`, '1', { EX: ttl });
  }
}

async function isTokenRevoked(token: string): Promise<boolean> {
  const result = await redis.get(`blocklist:${token}`);
  return result !== null;
}

// Update middleware to check blocklist
async function authMiddleware(req, res, next) {
  // ... extract and verify token ...
  if (await isTokenRevoked(token)) {
    return res.status(401).json({ error: 'Token revoked' });
  }
  // ... continue ...
}
```

## Implementation: Python (PyJWT)

```bash
pip install PyJWT[crypto] bcrypt
```

```python
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = os.environ["JWT_SECRET"]

def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "iss": "myapp",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=["HS256"],
            issuer="myapp",
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

### FastAPI Middleware

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
```

## Implementation: Go (golang-jwt)

```bash
go get github.com/golang-jwt/jwt/v5
```

```go
package auth

import (
    "time"
    "github.com/golang-jwt/jwt/v5"
)

var jwtSecret = []byte(os.Getenv("JWT_SECRET"))

type Claims struct {
    Role string `json:"role"`
    jwt.RegisteredClaims
}

func CreateAccessToken(userID, role string) (string, error) {
    claims := Claims{
        Role: role,
        RegisteredClaims: jwt.RegisteredClaims{
            Subject:   userID,
            Issuer:    "myapp",
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(15 * time.Minute)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
        },
    }
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(jwtSecret)
}

func VerifyAccessToken(tokenString string) (*Claims, error) {
    token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(t *jwt.Token) (interface{}, error) {
        if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
            return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
        }
        return jwtSecret, nil
    })
    if err != nil {
        return nil, err
    }
    claims, ok := token.Claims.(*Claims)
    if !ok || !token.Valid {
        return nil, fmt.Errorf("invalid token")
    }
    return claims, nil
}
```

### Go HTTP Middleware

```go
func AuthMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        authHeader := r.Header.Get("Authorization")
        if !strings.HasPrefix(authHeader, "Bearer ") {
            http.Error(w, "Unauthorized", http.StatusUnauthorized)
            return
        }
        tokenStr := strings.TrimPrefix(authHeader, "Bearer ")
        claims, err := VerifyAccessToken(tokenStr)
        if err != nil {
            http.Error(w, "Invalid token", http.StatusUnauthorized)
            return
        }
        ctx := context.WithValue(r.Context(), "user", claims)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

## Cookie vs Authorization Header

| Aspect | HttpOnly Cookie | Authorization Header |
|--------|----------------|---------------------|
| XSS protection | Yes (JS can't read) | No (if in localStorage) |
| CSRF vulnerable | Yes (needs mitigation) | No |
| Cross-origin | Needs CORS config | Works with CORS |
| Mobile apps | Awkward | Natural |
| SSR / Server Components | Easy to read | Need client-side code |

**Recommendation:**
- **Browser SPA + same-origin API** → HttpOnly cookie
- **Browser SPA + cross-origin API** → Authorization header (store token in memory, not localStorage)
- **Mobile app** → Authorization header (secure storage)
- **Server-to-server** → Authorization header

### Cookie Transport Example

```typescript
// Login endpoint — set tokens as cookies
app.post('/api/auth/login', async (req, res) => {
  // ... validate credentials ...

  const accessToken = await createAccessToken(user.id, user.role);
  const { token: refreshToken } = await createRefreshToken(user.id);

  res.cookie('access_token', accessToken, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: 15 * 60 * 1000, // 15 min
  });

  res.cookie('refresh_token', refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    path: '/api/auth/refresh', // Only sent to refresh endpoint
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
  });

  res.json({ user: { id: user.id, email: user.email } });
});
```

## Security Checklist for Custom JWT

- [ ] Use strong algorithm (HS256 with 256-bit secret, or RS256/ES256)
- [ ] Set short access token expiry (15 min max)
- [ ] Rotate refresh tokens on every use
- [ ] Detect refresh token family reuse (revoke entire family)
- [ ] Store refresh tokens as hashes in DB
- [ ] Always verify `alg` header (prevent `none` algorithm attack)
- [ ] Validate `iss`, `aud`, `exp` claims
- [ ] Use HttpOnly cookies for browser transport
- [ ] Add CSRF protection if using cookies
- [ ] Never put sensitive data in JWT payload (it's base64, not encrypted)
- [ ] Implement logout: revoke refresh token + optionally blocklist access token
- [ ] Use `crypto.timingSafeEqual` for any token comparisons (not relevant for JWT signature verification but important for refresh token hash comparison)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `jsonwebtoken` in Edge Runtime | Use `jose` (works everywhere) |
| No algorithm validation | Always specify `algorithms` in verify |
| Storing JWT in localStorage | Use HttpOnly cookie or in-memory |
| Giant JWT payloads | Keep payload small, query DB for details |
| Same secret for access + refresh | Use different secrets/keys |
| No token expiry | Always set `exp` claim |
| Refresh without rotation | Rotate on every use, store hash in DB |
