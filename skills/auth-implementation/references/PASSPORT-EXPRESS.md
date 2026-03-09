# Passport.js — Express / Fastify

Strategy-based authentication middleware for Node.js. 500+ strategies available.

## Installation

```bash
npm install passport passport-local express-session
# For JWT:
npm install passport-jwt jsonwebtoken
# For OAuth:
npm install passport-google-oauth20 passport-github2
# Session store:
npm install connect-redis
# Password hashing:
npm install bcryptjs
# Types (TypeScript):
npm install -D @types/passport @types/passport-local @types/express-session @types/bcryptjs
```

## Core Setup — Express + Session

```typescript
import express from 'express';
import session from 'express-session';
import passport from 'passport';
import RedisStore from 'connect-redis';
import { createClient } from 'redis';

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Redis session store
const redisClient = createClient({ url: process.env.REDIS_URL });
await redisClient.connect();

app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET!,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'lax',
    maxAge: 1000 * 60 * 60 * 24 * 7, // 7 days
  },
}));

app.use(passport.initialize());
app.use(passport.session());
```

## Serialization

```typescript
passport.serializeUser((user: any, done) => {
  done(null, user.id);
});

passport.deserializeUser(async (id: string, done) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id },
      select: { id: true, email: true, name: true, role: true },
    });
    done(null, user);
  } catch (err) {
    done(err);
  }
});
```

## Strategies

### Local Strategy (Email + Password)

```typescript
import { Strategy as LocalStrategy } from 'passport-local';
import bcrypt from 'bcryptjs';

passport.use(new LocalStrategy(
  {
    usernameField: 'email',
    passwordField: 'password',
  },
  async (email, password, done) => {
    try {
      const user = await prisma.user.findUnique({ where: { email } });
      if (!user || !user.passwordHash) {
        return done(null, false, { message: 'Invalid credentials' });
      }

      const isValid = await bcrypt.compare(password, user.passwordHash);
      if (!isValid) {
        return done(null, false, { message: 'Invalid credentials' });
      }

      return done(null, user);
    } catch (err) {
      return done(err);
    }
  },
));
```

### JWT Strategy

```typescript
import { Strategy as JwtStrategy, ExtractJwt } from 'passport-jwt';

passport.use(new JwtStrategy(
  {
    jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
    secretOrKey: process.env.JWT_SECRET!,
  },
  async (payload, done) => {
    try {
      const user = await prisma.user.findUnique({ where: { id: payload.sub } });
      if (!user) return done(null, false);
      return done(null, user);
    } catch (err) {
      return done(err, false);
    }
  },
));
```

### Google OAuth 2.0

```typescript
import { Strategy as GoogleStrategy } from 'passport-google-oauth20';

passport.use(new GoogleStrategy(
  {
    clientID: process.env.GOOGLE_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    callbackURL: '/api/auth/google/callback',
    scope: ['email', 'profile'],
  },
  async (accessToken, refreshToken, profile, done) => {
    try {
      // Find or create user
      let account = await prisma.oAuthAccount.findUnique({
        where: {
          provider_providerAccountId: {
            provider: 'google',
            providerAccountId: profile.id,
          },
        },
        include: { user: true },
      });

      if (account) {
        return done(null, account.user);
      }

      // Create new user + account
      const user = await prisma.user.create({
        data: {
          email: profile.emails![0].value,
          name: profile.displayName,
          emailVerified: true,
          oauthAccounts: {
            create: {
              provider: 'google',
              providerAccountId: profile.id,
              accessToken,
              refreshToken,
            },
          },
        },
      });

      return done(null, user);
    } catch (err) {
      return done(err as Error);
    }
  },
));
```

### GitHub OAuth

```typescript
import { Strategy as GitHubStrategy } from 'passport-github2';

passport.use(new GitHubStrategy(
  {
    clientID: process.env.GITHUB_CLIENT_ID!,
    clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    callbackURL: '/api/auth/github/callback',
    scope: ['user:email'],
  },
  async (accessToken, refreshToken, profile, done) => {
    try {
      let account = await prisma.oAuthAccount.findUnique({
        where: {
          provider_providerAccountId: {
            provider: 'github',
            providerAccountId: profile.id,
          },
        },
        include: { user: true },
      });

      if (account) return done(null, account.user);

      const email = profile.emails?.[0]?.value;
      const user = await prisma.user.create({
        data: {
          email: email!,
          name: profile.displayName || profile.username,
          oauthAccounts: {
            create: {
              provider: 'github',
              providerAccountId: profile.id,
              accessToken,
            },
          },
        },
      });

      return done(null, user);
    } catch (err) {
      return done(err as Error);
    }
  },
));
```

## Routes

### Login / Logout

```typescript
// Login with email/password
app.post('/api/auth/login',
  passport.authenticate('local', { failWithError: true }),
  (req, res) => {
    res.json({ user: req.user });
  },
);

// Logout
app.post('/api/auth/logout', (req, res) => {
  req.logout((err) => {
    if (err) return res.status(500).json({ error: 'Logout failed' });
    req.session.destroy((err) => {
      if (err) return res.status(500).json({ error: 'Session destroy failed' });
      res.clearCookie('connect.sid');
      res.json({ message: 'Logged out' });
    });
  });
});
```

### Registration

```typescript
app.post('/api/auth/register', async (req, res) => {
  const { email, password, name } = req.body;

  // Validate
  if (!email || !password || password.length < 8) {
    return res.status(400).json({ error: 'Invalid input' });
  }

  // Check existing
  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) {
    return res.status(409).json({ error: 'Email already registered' });
  }

  // Create user
  const passwordHash = await bcrypt.hash(password, 12);
  const user = await prisma.user.create({
    data: { email, passwordHash, name },
  });

  // Auto-login
  req.login(user, (err) => {
    if (err) return res.status(500).json({ error: 'Login failed' });
    res.status(201).json({ user: { id: user.id, email: user.email, name: user.name } });
  });
});
```

### OAuth Routes

```typescript
// Google
app.get('/api/auth/google',
  passport.authenticate('google', { scope: ['email', 'profile'] }),
);

app.get('/api/auth/google/callback',
  passport.authenticate('google', {
    successRedirect: '/dashboard',
    failureRedirect: '/login',
  }),
);

// GitHub
app.get('/api/auth/github',
  passport.authenticate('github', { scope: ['user:email'] }),
);

app.get('/api/auth/github/callback',
  passport.authenticate('github', {
    successRedirect: '/dashboard',
    failureRedirect: '/login',
  }),
);
```

### Protected Routes

```typescript
// Auth middleware
function requireAuth(req, res, next) {
  if (req.isAuthenticated()) return next();
  res.status(401).json({ error: 'Authentication required' });
}

// Role middleware
function requireRole(...roles: string[]) {
  return (req, res, next) => {
    if (!req.isAuthenticated()) {
      return res.status(401).json({ error: 'Authentication required' });
    }
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Insufficient permissions' });
    }
    next();
  };
}

// Usage
app.get('/api/profile', requireAuth, (req, res) => {
  res.json({ user: req.user });
});

app.get('/api/admin', requireRole('admin'), (req, res) => {
  res.json({ message: 'Admin only' });
});
```

## JWT-Only Mode (No Sessions)

For APIs without session storage:

```typescript
import jwt from 'jsonwebtoken';

// Login returns JWT
app.post('/api/auth/login', (req, res, next) => {
  passport.authenticate('local', { session: false }, (err, user, info) => {
    if (err) return next(err);
    if (!user) return res.status(401).json({ error: info?.message });

    const accessToken = jwt.sign(
      { sub: user.id, role: user.role },
      process.env.JWT_SECRET!,
      { expiresIn: '15m' },
    );

    const refreshToken = jwt.sign(
      { sub: user.id, type: 'refresh' },
      process.env.JWT_REFRESH_SECRET!,
      { expiresIn: '7d' },
    );

    // Store refresh token hash in DB
    // ...

    res.json({ accessToken, refreshToken });
  })(req, res, next);
});

// Protected route using JWT strategy
app.get('/api/protected',
  passport.authenticate('jwt', { session: false }),
  (req, res) => {
    res.json({ data: 'protected' });
  },
);
```

## API Key Strategy

```typescript
import { Strategy as CustomStrategy } from 'passport-custom';
import crypto from 'crypto';

passport.use('api-key', new CustomStrategy(async (req, done) => {
  const apiKey = req.headers['x-api-key'] as string;
  if (!apiKey) return done(null, false);

  const keyHash = crypto.createHash('sha256').update(apiKey).digest('hex');
  const keyRecord = await prisma.apiKey.findUnique({
    where: { hash: keyHash },
    include: { user: true },
  });

  if (!keyRecord || (keyRecord.expiresAt && keyRecord.expiresAt < new Date())) {
    return done(null, false);
  }

  // Update last used
  await prisma.apiKey.update({
    where: { id: keyRecord.id },
    data: { lastUsedAt: new Date() },
  });

  return done(null, keyRecord.user);
}));

// Usage
app.get('/api/data',
  passport.authenticate('api-key', { session: false }),
  handler,
);
```

## Multiple Strategies

```typescript
// Try JWT first, then session, then API key
function flexibleAuth(req, res, next) {
  passport.authenticate(['jwt', 'session', 'api-key'], { session: false }, (err, user) => {
    if (err) return next(err);
    if (!user) return res.status(401).json({ error: 'Unauthorized' });
    req.user = user;
    next();
  })(req, res, next);
}
```

## Fastify Integration

```typescript
import fastify from 'fastify';
import fastifyPassport from '@fastify/passport';
import fastifySecureSession from '@fastify/secure-session';

const app = fastify();

await app.register(fastifySecureSession, {
  key: Buffer.from(process.env.SESSION_KEY!, 'hex'),
  cookie: { path: '/', httpOnly: true, secure: true },
});

await app.register(fastifyPassport.initialize());
await app.register(fastifyPassport.secureSession());

// Same strategy configuration applies
fastifyPassport.use('local', localStrategy);

app.post('/login', {
  preValidation: fastifyPassport.authenticate('local'),
}, async (req, reply) => {
  return { user: req.user };
});
```

## Session Stores

| Store | Package | Best For |
|-------|---------|----------|
| Redis | `connect-redis` | Production, distributed |
| PostgreSQL | `connect-pg-simple` | Already using PostgreSQL |
| MongoDB | `connect-mongo` | Already using MongoDB |
| Memory | (default) | Development only |
| SQLite | `better-sqlite3-session-store` | Small apps |

## TypeScript Types

```typescript
// Extend Express types
declare global {
  namespace Express {
    interface User {
      id: string;
      email: string;
      name: string | null;
      role: string;
    }
  }
}
```

## Common Issues

| Issue | Solution |
|-------|----------|
| `req.user` is undefined | Check `passport.initialize()` and `passport.session()` middleware order |
| Session not persisting | Check session store config, cookie settings |
| CORS + cookies not working | `credentials: 'include'` on client, `cors({ credentials: true, origin: '...' })` on server |
| OAuth callback mismatch | Ensure callback URL matches provider console exactly |
| Multiple deserialize calls | Use session store (Redis) to cache, avoid DB per request |
| `serializeUser` not called | Ensure you call `done(null, user)` in strategy, not `done(null, false)` |
