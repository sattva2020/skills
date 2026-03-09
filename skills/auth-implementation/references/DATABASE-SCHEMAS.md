# Database Schemas for Authentication

Complete database schema patterns for auth systems.

## Core Tables

Every auth system needs these tables. Adapt to your ORM/database.

### PostgreSQL (Raw SQL)

```sql
-- Users table
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),            -- NULL for OAuth-only users
  name          VARCHAR(255),
  role          VARCHAR(50) DEFAULT 'user',
  email_verified BOOLEAN DEFAULT FALSE,
  image         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- Sessions table (for session-based auth)
CREATE TABLE sessions (
  id         VARCHAR(255) PRIMARY KEY,   -- Session ID (random, hashed)
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- OAuth accounts (link users to providers)
CREATE TABLE accounts (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider            VARCHAR(50) NOT NULL,     -- 'google', 'github', etc.
  provider_account_id VARCHAR(255) NOT NULL,    -- Provider's user ID
  access_token        TEXT,
  refresh_token       TEXT,
  token_expires_at    TIMESTAMPTZ,
  scope               TEXT,
  id_token            TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(provider, provider_account_id)
);

CREATE INDEX idx_accounts_user_id ON accounts(user_id);

-- Verification tokens (email verification, password reset)
CREATE TABLE verification_tokens (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  identifier VARCHAR(255) NOT NULL,     -- Email or user ID
  token      VARCHAR(255) NOT NULL,     -- Hashed token
  type       VARCHAR(50) NOT NULL,      -- 'email_verify', 'password_reset'
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_verification_tokens ON verification_tokens(token);
CREATE INDEX idx_verification_identifier ON verification_tokens(identifier, type);
```

### MySQL

```sql
CREATE TABLE users (
  id            CHAR(36) PRIMARY KEY,
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  name          VARCHAR(255),
  role          VARCHAR(50) DEFAULT 'user',
  email_verified BOOLEAN DEFAULT FALSE,
  image         TEXT,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
  id         VARCHAR(255) PRIMARY KEY,
  user_id    CHAR(36) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  ip_address VARCHAR(45),
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id),
  INDEX idx_expires (expires_at)
);

CREATE TABLE accounts (
  id                  CHAR(36) PRIMARY KEY,
  user_id             CHAR(36) NOT NULL,
  provider            VARCHAR(50) NOT NULL,
  provider_account_id VARCHAR(255) NOT NULL,
  access_token        TEXT,
  refresh_token       TEXT,
  token_expires_at    TIMESTAMP NULL,
  scope               TEXT,
  id_token            TEXT,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uq_provider_account (provider, provider_account_id),
  INDEX idx_user_id (user_id)
);
```

### Prisma Schema

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql" // or "mysql", "sqlite"
  url      = env("DATABASE_URL")
}

model User {
  id            String    @id @default(cuid())
  email         String    @unique
  passwordHash  String?   @map("password_hash")
  name          String?
  role          String    @default("user")
  emailVerified Boolean   @default(false) @map("email_verified")
  image         String?
  sessions      Session[]
  accounts      Account[]
  refreshTokens RefreshToken[]
  apiKeys       ApiKey[]
  createdAt     DateTime  @default(now()) @map("created_at")
  updatedAt     DateTime  @updatedAt @map("updated_at")

  @@map("users")
}

model Session {
  id        String   @id @default(cuid())
  userId    String   @map("user_id")
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  expiresAt DateTime @map("expires_at")
  ipAddress String?  @map("ip_address")
  userAgent String?  @map("user_agent")
  createdAt DateTime @default(now()) @map("created_at")

  @@index([userId])
  @@index([expiresAt])
  @@map("sessions")
}

model Account {
  id                String    @id @default(cuid())
  userId            String    @map("user_id")
  user              User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  provider          String
  providerAccountId String    @map("provider_account_id")
  accessToken       String?   @map("access_token")
  refreshToken      String?   @map("refresh_token")
  tokenExpiresAt    DateTime? @map("token_expires_at")
  scope             String?
  idToken           String?   @map("id_token")
  createdAt         DateTime  @default(now()) @map("created_at")

  @@unique([provider, providerAccountId])
  @@index([userId])
  @@map("accounts")
}

model VerificationToken {
  id         String   @id @default(cuid())
  identifier String
  token      String
  type       String   // "email_verify" | "password_reset"
  expiresAt  DateTime @map("expires_at")
  createdAt  DateTime @default(now()) @map("created_at")

  @@index([token])
  @@index([identifier, type])
  @@map("verification_tokens")
}
```

### Drizzle Schema (PostgreSQL)

```typescript
import { pgTable, text, timestamp, boolean, uuid, unique, index } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  passwordHash: text('password_hash'),
  name: text('name'),
  role: text('role').default('user').notNull(),
  emailVerified: boolean('email_verified').default(false).notNull(),
  image: text('image'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
});

export const sessions = pgTable('sessions', {
  id: text('id').primaryKey(),
  userId: uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
  ipAddress: text('ip_address'),
  userAgent: text('user_agent'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
}, (table) => [
  index('idx_sessions_user_id').on(table.userId),
]);

export const accounts = pgTable('accounts', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  provider: text('provider').notNull(),
  providerAccountId: text('provider_account_id').notNull(),
  accessToken: text('access_token'),
  refreshToken: text('refresh_token'),
  tokenExpiresAt: timestamp('token_expires_at', { withTimezone: true }),
  scope: text('scope'),
  idToken: text('id_token'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
}, (table) => [
  unique().on(table.provider, table.providerAccountId),
  index('idx_accounts_user_id').on(table.userId),
]);
```

## Password Hashing

### Algorithm Comparison

| Algorithm | Recommendation | Notes |
|-----------|---------------|-------|
| argon2id | Best choice | Winner of PHC, memory-hard |
| bcrypt | Good | Widely supported, cost factor 10-12 |
| scrypt | Good | Memory-hard, used by Lucia |
| PBKDF2 | Acceptable | NIST approved, high iteration count |
| SHA-256/SHA-512 | NEVER | Not designed for passwords |
| MD5 | NEVER | Broken, trivially cracked |

### argon2id (Recommended)

```typescript
// Node.js — @node-rs/argon2 (native, fast)
import { hash, verify } from '@node-rs/argon2';

const passwordHash = await hash(password, {
  memoryCost: 19456,  // 19 MiB (OWASP minimum)
  timeCost: 2,        // 2 iterations
  outputLen: 32,      // 32 bytes output
  parallelism: 1,     // 1 thread
});

const isValid = await verify(passwordHash, password);
```

```python
# Python — argon2-cffi
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
)

password_hash = ph.hash(password)
is_valid = ph.verify(password_hash, password)  # Raises on failure
```

### bcrypt

```typescript
// Node.js — bcryptjs (pure JS) or bcrypt (native)
import bcrypt from 'bcryptjs';

const passwordHash = await bcrypt.hash(password, 12); // cost factor 12
const isValid = await bcrypt.compare(password, passwordHash);
```

```python
# Python — bcrypt
import bcrypt

password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
is_valid = bcrypt.checkpw(password.encode(), password_hash)
```

```go
// Go — golang.org/x/crypto/bcrypt
import "golang.org/x/crypto/bcrypt"

hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
err = bcrypt.CompareHashAndPassword(hash, []byte(password))
```

## Refresh Token Table

For JWT-based auth with token rotation:

```sql
CREATE TABLE refresh_tokens (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash of token
  family     UUID NOT NULL,                 -- Token family for rotation detection
  expires_at TIMESTAMPTZ NOT NULL,
  revoked    BOOLEAN DEFAULT FALSE,
  replaced_by UUID REFERENCES refresh_tokens(id), -- Points to next token in chain
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rt_user ON refresh_tokens(user_id);
CREATE INDEX idx_rt_family ON refresh_tokens(family);
CREATE INDEX idx_rt_hash ON refresh_tokens(token_hash);
```

### Prisma

```prisma
model RefreshToken {
  id         String    @id @default(cuid())
  userId     String    @map("user_id")
  user       User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  tokenHash  String    @unique @map("token_hash")
  family     String    // UUID — token rotation family
  expiresAt  DateTime  @map("expires_at")
  revoked    Boolean   @default(false)
  ipAddress  String?   @map("ip_address")
  userAgent  String?   @map("user_agent")
  createdAt  DateTime  @default(now()) @map("created_at")

  @@index([userId])
  @@index([family])
  @@map("refresh_tokens")
}
```

## API Key Table

Store only the hash. Show the full key once on creation.

```sql
CREATE TABLE api_keys (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name       VARCHAR(255) NOT NULL,          -- User-friendly name
  prefix     VARCHAR(10) NOT NULL,           -- First 8 chars for identification
  key_hash   VARCHAR(64) NOT NULL UNIQUE,    -- SHA-256 hash
  scopes     TEXT[],                          -- ['read', 'write']
  expires_at TIMESTAMPTZ,                    -- NULL = never expires
  last_used  TIMESTAMPTZ,
  revoked    BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(prefix);
```

### API Key Generation

```typescript
import crypto from 'crypto';

function generateApiKey(prefix: string = 'sk') {
  const key = `${prefix}_${crypto.randomBytes(32).toString('base64url')}`;
  const keyHash = crypto.createHash('sha256').update(key).digest('hex');
  const keyPrefix = key.substring(0, prefix.length + 9); // "sk_abc12345"

  return { key, keyHash, keyPrefix };
}

// Store keyHash and keyPrefix in DB
// Return key to user ONCE — never store or show again
```

### API Key Verification

```typescript
async function verifyApiKey(key: string) {
  const keyHash = crypto.createHash('sha256').update(key).digest('hex');
  const record = await prisma.apiKey.findUnique({ where: { keyHash } });

  if (!record || record.revoked) return null;
  if (record.expiresAt && record.expiresAt < new Date()) return null;

  // Update last used
  await prisma.apiKey.update({
    where: { id: record.id },
    data: { lastUsed: new Date() },
  });

  return record;
}
```

## Audit Log Table

Track auth events for security monitoring.

```sql
CREATE TABLE auth_audit_log (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
  action     VARCHAR(50) NOT NULL,   -- 'login', 'logout', 'password_change', 'mfa_enable'
  status     VARCHAR(20) NOT NULL,   -- 'success', 'failure'
  ip_address INET,
  user_agent TEXT,
  metadata   JSONB,                  -- Additional context
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON auth_audit_log(user_id);
CREATE INDEX idx_audit_action ON auth_audit_log(action);
CREATE INDEX idx_audit_created ON auth_audit_log(created_at);
```

### Logging Helper

```typescript
async function logAuthEvent(
  userId: string | null,
  action: string,
  status: 'success' | 'failure',
  req: Request,
  metadata?: Record<string, unknown>,
) {
  await prisma.authAuditLog.create({
    data: {
      userId,
      action,
      status,
      ipAddress: req.headers.get('x-forwarded-for') || req.socket?.remoteAddress,
      userAgent: req.headers.get('user-agent'),
      metadata: metadata ?? undefined,
    },
  });
}

// Usage
await logAuthEvent(user.id, 'login', 'success', req);
await logAuthEvent(null, 'login', 'failure', req, { email, reason: 'invalid_password' });
```

## Multi-Tenant Schema

For SaaS with organizations/teams:

```sql
CREATE TABLE organizations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       VARCHAR(255) NOT NULL,
  slug       VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE memberships (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  role            VARCHAR(50) NOT NULL DEFAULT 'member', -- 'owner', 'admin', 'member'
  created_at      TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(user_id, organization_id)
);

CREATE INDEX idx_memberships_user ON memberships(user_id);
CREATE INDEX idx_memberships_org ON memberships(organization_id);
```

## Session Cleanup

Periodically remove expired sessions:

```sql
-- Run via cron job or scheduled task
DELETE FROM sessions WHERE expires_at < NOW();
DELETE FROM refresh_tokens WHERE expires_at < NOW();
DELETE FROM verification_tokens WHERE expires_at < NOW();
```

```typescript
// Node.js cron
import cron from 'node-cron';

cron.schedule('0 */6 * * *', async () => { // Every 6 hours
  const result = await prisma.session.deleteMany({
    where: { expiresAt: { lt: new Date() } },
  });
  console.log(`Cleaned ${result.count} expired sessions`);
});
```
