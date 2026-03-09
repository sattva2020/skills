# Security Checklist for Authentication

Comprehensive security hardening guide. Apply after initial auth implementation.

## Password Security

### NIST SP 800-63B Guidelines

| Rule | Requirement |
|------|-------------|
| Minimum length | 8 characters (NIST), 12+ recommended |
| Maximum length | At least 64 characters |
| Complexity rules | Do NOT enforce (upper/lower/special) — NIST recommends against |
| Breached password check | Check against known breached passwords (HaveIBeenPwned API) |
| Hashing algorithm | argon2id (preferred) or bcrypt (cost ≥ 10) |
| No password hints | Do not store or display password hints |
| Allow paste | Allow password paste (for password managers) |

### Breached Password Check

```typescript
import crypto from 'crypto';

async function isPasswordBreached(password: string): Promise<boolean> {
  const sha1 = crypto.createHash('sha1').update(password).digest('hex').toUpperCase();
  const prefix = sha1.slice(0, 5);
  const suffix = sha1.slice(5);

  const response = await fetch(`https://api.pwnedpasswords.com/range/${prefix}`);
  const text = await response.text();

  return text.split('\n').some(line => line.startsWith(suffix));
}
```

### Password Validation

```typescript
function validatePassword(password: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (password.length < 8) errors.push('Password must be at least 8 characters');
  if (password.length > 128) errors.push('Password must be at most 128 characters');
  if (/^\s|\s$/.test(password)) errors.push('Password must not start or end with whitespace');

  return { valid: errors.length === 0, errors };
}
```

## CSRF Protection

### When CSRF is Needed

| Auth Method | CSRF Needed? | Why |
|-------------|-------------|-----|
| Cookie-based sessions | YES | Browser auto-sends cookies |
| JWT in Authorization header | NO | Not auto-sent |
| JWT in HttpOnly cookie | YES | Browser auto-sends cookies |
| API key in header | NO | Not auto-sent |

### SameSite Cookie (Primary Defense)

```typescript
// SameSite=Lax — blocks cross-origin POST but allows top-level navigation
cookie: {
  sameSite: 'lax',    // Good default
  httpOnly: true,
  secure: true,
}

// SameSite=Strict — blocks all cross-origin requests (may break OAuth redirects)
cookie: {
  sameSite: 'strict',
  httpOnly: true,
  secure: true,
}
```

### Double-Submit Cookie Pattern

```typescript
import crypto from 'crypto';

// Generate CSRF token
function generateCsrfToken(): string {
  return crypto.randomBytes(32).toString('hex');
}

// Set CSRF cookie (readable by JS) + return token
app.use((req, res, next) => {
  if (!req.cookies.csrf_token) {
    const token = generateCsrfToken();
    res.cookie('csrf_token', token, {
      httpOnly: false, // JS must read this
      secure: true,
      sameSite: 'lax',
    });
  }
  next();
});

// Verify CSRF on state-changing requests
function verifyCsrf(req, res, next) {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) return next();

  const cookieToken = req.cookies.csrf_token;
  const headerToken = req.headers['x-csrf-token'];

  if (!cookieToken || !headerToken || cookieToken !== headerToken) {
    return res.status(403).json({ error: 'CSRF validation failed' });
  }
  next();
}
```

### Next.js Server Actions

Next.js Server Actions have built-in CSRF protection. No additional setup needed.

## XSS Prevention

### Token Storage Decision Matrix

| Storage | XSS Safe? | CSRF Safe? | Verdict |
|---------|-----------|------------|---------|
| localStorage | NO | YES | Never for auth tokens |
| sessionStorage | NO | YES | Never for auth tokens |
| HttpOnly cookie | YES | NO (add CSRF) | Recommended |
| In-memory (JS variable) | Partial | YES | Good for access tokens |
| Web Worker | YES | YES | Best but complex |

### Cookie Configuration

```typescript
// Secure cookie settings
const secureCookieOptions = {
  httpOnly: true,      // Cannot be read by JavaScript
  secure: true,        // Only sent over HTTPS
  sameSite: 'lax',     // CSRF protection
  path: '/',           // Available site-wide
  maxAge: 7 * 24 * 60 * 60, // 7 days
  // domain: '.example.com', // For subdomain sharing
};
```

### Content Security Policy

```typescript
// Express middleware
app.use((req, res, next) => {
  res.setHeader('Content-Security-Policy', [
    "default-src 'self'",
    "script-src 'self'",           // No inline scripts
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "connect-src 'self'",
    "frame-ancestors 'none'",       // Prevent clickjacking
    "form-action 'self'",           // Restrict form submissions
  ].join('; '));
  next();
});
```

## Rate Limiting

### Endpoints to Rate Limit

| Endpoint | Limit | Key | Notes |
|----------|-------|-----|-------|
| POST /login | 5/min | IP + email | Prevent brute force |
| POST /register | 3/min | IP | Prevent mass registration |
| POST /forgot-password | 3/hour | email | Prevent email flooding |
| POST /verify-otp | 5/min | user_id | Prevent OTP brute force |
| POST /api/* | 100/min | API key | General API limit |

### Implementation (Express + rate-limit)

```typescript
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import { createClient } from 'redis';

const redisClient = createClient({ url: process.env.REDIS_URL });

// Login rate limit
const loginLimiter = rateLimit({
  store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
  windowMs: 60 * 1000,   // 1 minute
  max: 5,                  // 5 attempts
  keyGenerator: (req) => `${req.ip}:${req.body.email}`,
  message: { error: 'Too many login attempts. Try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
});

app.post('/api/auth/login', loginLimiter, loginHandler);

// Registration rate limit
const registerLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 3,
  keyGenerator: (req) => req.ip,
});

app.post('/api/auth/register', registerLimiter, registerHandler);
```

### Account Lockout

```typescript
const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_DURATION_MS = 15 * 60 * 1000; // 15 minutes

async function checkAccountLockout(email: string) {
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user) return { locked: false };

  if (user.failedAttempts >= MAX_FAILED_ATTEMPTS) {
    const lockoutEnd = new Date(user.lastFailedAt!.getTime() + LOCKOUT_DURATION_MS);
    if (new Date() < lockoutEnd) {
      return { locked: true, retryAfter: lockoutEnd };
    }
    // Lockout expired, reset
    await prisma.user.update({
      where: { id: user.id },
      data: { failedAttempts: 0 },
    });
  }

  return { locked: false };
}

async function recordFailedAttempt(email: string) {
  await prisma.user.update({
    where: { email },
    data: {
      failedAttempts: { increment: 1 },
      lastFailedAt: new Date(),
    },
  });
}

async function resetFailedAttempts(userId: string) {
  await prisma.user.update({
    where: { id: userId },
    data: { failedAttempts: 0, lastFailedAt: null },
  });
}
```

## Session Security

### Session Fixation Prevention

```typescript
// After successful authentication, regenerate session ID
app.post('/login', async (req, res) => {
  // ... validate credentials ...

  // Regenerate session to prevent fixation
  req.session.regenerate((err) => {
    if (err) return res.status(500).json({ error: 'Session error' });
    req.session.userId = user.id;
    req.session.role = user.role;
    req.session.save((err) => {
      if (err) return res.status(500).json({ error: 'Session error' });
      res.json({ user });
    });
  });
});
```

### Session Timeouts

| Type | Duration | Use Case |
|------|----------|----------|
| Absolute timeout | 8-24 hours | Max session lifetime |
| Idle timeout | 30-60 minutes | Inactivity logout |
| Remember me | 7-30 days | Persistent sessions |

```typescript
// Idle timeout middleware
function idleTimeout(maxIdleMs: number) {
  return (req, res, next) => {
    if (req.session.lastActivity) {
      const idle = Date.now() - req.session.lastActivity;
      if (idle > maxIdleMs) {
        return req.session.destroy(() => {
          res.status(401).json({ error: 'Session expired due to inactivity' });
        });
      }
    }
    req.session.lastActivity = Date.now();
    next();
  };
}
```

### Invalidate Sessions on Password Change

```typescript
async function changePassword(userId: string, newPassword: string, currentSessionId: string) {
  const passwordHash = await hash(newPassword);
  await prisma.user.update({
    where: { id: userId },
    data: { passwordHash },
  });

  // Delete all sessions except current
  await prisma.session.deleteMany({
    where: {
      userId,
      id: { not: currentSessionId },
    },
  });
}
```

## Secure Headers

```typescript
import helmet from 'helmet';

app.use(helmet()); // Sets many security headers

// Or manually:
app.use((req, res, next) => {
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '0'); // Modern browsers: rely on CSP instead
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  next();
});
```

### Next.js Security Headers

```typescript
// next.config.js
const securityHeaders = [
  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
];

module.exports = {
  async headers() {
    return [{ source: '/(.*)', headers: securityHeaders }];
  },
};
```

## CORS for Auth Endpoints

```typescript
import cors from 'cors';

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true,        // Required for cookies
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token'],
  maxAge: 86400,            // Preflight cache: 24 hours
}));
```

## MFA / 2FA Implementation

### TOTP (Time-based One-Time Password)

```typescript
import { TOTP, Secret } from 'otpauth';
import QRCode from 'qrcode';

// Enable MFA — Step 1: Generate secret
async function enableMfa(userId: string) {
  const secret = new Secret({ size: 20 });

  // Store encrypted secret in DB (not yet verified)
  await prisma.user.update({
    where: { id: userId },
    data: { mfaSecret: secret.base32, mfaEnabled: false },
  });

  const totp = new TOTP({
    issuer: 'MyApp',
    label: user.email,
    algorithm: 'SHA1',
    digits: 6,
    period: 30,
    secret,
  });

  const uri = totp.toString();
  const qrCode = await QRCode.toDataURL(uri);

  return { secret: secret.base32, qrCode };
}

// Enable MFA — Step 2: Verify first code
async function verifyAndEnableMfa(userId: string, code: string) {
  const user = await prisma.user.findUnique({ where: { id: userId } });
  const totp = new TOTP({ secret: Secret.fromBase32(user.mfaSecret) });

  const isValid = totp.validate({ token: code, window: 1 }) !== null;
  if (!isValid) throw new Error('Invalid code');

  // Generate recovery codes
  const recoveryCodes = Array.from({ length: 8 }, () =>
    crypto.randomBytes(4).toString('hex'),
  );

  await prisma.user.update({
    where: { id: userId },
    data: {
      mfaEnabled: true,
      recoveryCodes: recoveryCodes.map(c =>
        crypto.createHash('sha256').update(c).digest('hex'),
      ),
    },
  });

  return { recoveryCodes }; // Show once
}

// Verify MFA during login
async function verifyMfaCode(userId: string, code: string): Promise<boolean> {
  const user = await prisma.user.findUnique({ where: { id: userId } });
  const totp = new TOTP({ secret: Secret.fromBase32(user.mfaSecret) });
  return totp.validate({ token: code, window: 1 }) !== null;
}
```

### WebAuthn / Passkeys

```bash
npm install @simplewebauthn/server @simplewebauthn/browser
```

```typescript
// Server — Registration
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
} from '@simplewebauthn/server';

const rpName = 'MyApp';
const rpID = 'example.com';
const origin = 'https://example.com';

async function startRegistration(user: User) {
  const options = await generateRegistrationOptions({
    rpName,
    rpID,
    userID: new TextEncoder().encode(user.id),
    userName: user.email,
    attestationType: 'none',
    authenticatorSelection: {
      residentKey: 'preferred',
      userVerification: 'preferred',
    },
  });

  // Store challenge in session
  await saveChallenge(user.id, options.challenge);

  return options;
}

async function finishRegistration(user: User, response: RegistrationResponseJSON) {
  const expectedChallenge = await getChallenge(user.id);

  const verification = await verifyRegistrationResponse({
    response,
    expectedChallenge,
    expectedOrigin: origin,
    expectedRPID: rpID,
  });

  if (verification.verified && verification.registrationInfo) {
    await prisma.authenticator.create({
      data: {
        userId: user.id,
        credentialId: Buffer.from(verification.registrationInfo.credential.id),
        publicKey: Buffer.from(verification.registrationInfo.credential.publicKey),
        counter: verification.registrationInfo.credential.counter,
      },
    });
  }

  return verification.verified;
}
```

## Email Verification Flow

```typescript
import crypto from 'crypto';

// Generate verification token
async function sendVerificationEmail(userId: string, email: string) {
  const token = crypto.randomBytes(32).toString('hex');
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

  await prisma.verificationToken.create({
    data: {
      identifier: email,
      token: tokenHash,
      type: 'email_verify',
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours
    },
  });

  const verifyUrl = `${process.env.APP_URL}/verify-email?token=${token}`;
  await sendEmail({ to: email, subject: 'Verify Email', body: `Click: ${verifyUrl}` });
}

// Verify email
async function verifyEmail(token: string) {
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

  const record = await prisma.verificationToken.findFirst({
    where: { token: tokenHash, type: 'email_verify', expiresAt: { gt: new Date() } },
  });

  if (!record) throw new Error('Invalid or expired token');

  await prisma.user.update({
    where: { email: record.identifier },
    data: { emailVerified: true },
  });

  await prisma.verificationToken.delete({ where: { id: record.id } });
}
```

## Password Reset Flow

```typescript
// Request reset
async function requestPasswordReset(email: string) {
  const user = await prisma.user.findUnique({ where: { email } });
  // Always return success (prevent user enumeration)
  if (!user) return;

  // Delete existing reset tokens
  await prisma.verificationToken.deleteMany({
    where: { identifier: email, type: 'password_reset' },
  });

  const token = crypto.randomBytes(32).toString('hex');
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

  await prisma.verificationToken.create({
    data: {
      identifier: email,
      token: tokenHash,
      type: 'password_reset',
      expiresAt: new Date(Date.now() + 60 * 60 * 1000), // 1 hour
    },
  });

  const resetUrl = `${process.env.APP_URL}/reset-password?token=${token}`;
  await sendEmail({ to: email, subject: 'Reset Password', body: `Click: ${resetUrl}` });
}

// Execute reset
async function resetPassword(token: string, newPassword: string) {
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

  const record = await prisma.verificationToken.findFirst({
    where: { token: tokenHash, type: 'password_reset', expiresAt: { gt: new Date() } },
  });
  if (!record) throw new Error('Invalid or expired token');

  const passwordHash = await hash(newPassword);

  const user = await prisma.user.update({
    where: { email: record.identifier },
    data: { passwordHash },
  });

  // Invalidate all sessions
  await prisma.session.deleteMany({ where: { userId: user.id } });

  // Delete token
  await prisma.verificationToken.delete({ where: { id: record.id } });
}
```

## Quick Reference: Security Headers

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'self'; script-src 'self'; frame-ancestors 'none'
```
