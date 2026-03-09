# Framework-Specific Auth Patterns

Route protection and auth implementation patterns for each major framework.

## Next.js App Router (14+)

### middleware.ts — Route Protection

```typescript
import { NextRequest, NextResponse } from 'next/server';

const protectedPaths = ['/dashboard', '/settings', '/api/protected'];
const authPaths = ['/login', '/register', '/forgot-password'];
const adminPaths = ['/admin'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const sessionToken = request.cookies.get('session-token')?.value;

  // Redirect unauthenticated users from protected pages
  const isProtected = protectedPaths.some(p => pathname.startsWith(p));
  if (isProtected && !sessionToken) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users from auth pages
  const isAuthPage = authPaths.some(p => pathname.startsWith(p));
  if (isAuthPage && sessionToken) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
};
```

### Server Component — Session Check

```typescript
import { auth } from '@/lib/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect('/login');

  return (
    <main>
      <h1>Welcome, {session.user.name}</h1>
    </main>
  );
}
```

### Server Action — Protected Mutation

```typescript
'use server';
import { auth } from '@/lib/auth';
import { revalidatePath } from 'next/cache';

export async function updateProfile(formData: FormData) {
  const session = await auth();
  if (!session) throw new Error('Unauthorized');

  const name = formData.get('name') as string;
  await prisma.user.update({
    where: { id: session.user.id },
    data: { name },
  });

  revalidatePath('/settings');
}
```

### Route Handler — API Protection

```typescript
// app/api/articles/route.ts
import { auth } from '@/lib/auth';
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const body = await request.json();
  const article = await prisma.article.create({
    data: { ...body, authorId: session.user.id },
  });

  return NextResponse.json(article, { status: 201 });
}
```

## Next.js Pages Router

### getServerSideProps — Page Protection

```typescript
import { GetServerSideProps } from 'next';
import { getSession } from '@/lib/auth';

export const getServerSideProps: GetServerSideProps = async (context) => {
  const session = await getSession(context.req);

  if (!session) {
    return {
      redirect: {
        destination: `/login?callbackUrl=${context.resolvedUrl}`,
        permanent: false,
      },
    };
  }

  return {
    props: { user: session.user },
  };
};
```

### API Route Protection

```typescript
// pages/api/protected.ts
import type { NextApiRequest, NextApiResponse } from 'next';
import { getSession } from '@/lib/auth';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = await getSession(req);
  if (!session) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  res.json({ data: 'protected' });
}
```

## Express / Fastify

### Express Middleware Chain

```typescript
import express from 'express';

const app = express();

// Auth middleware
function requireAuth(req, res, next) {
  if (!req.session?.userId) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  next();
}

// Role middleware
function requireRole(...roles: string[]) {
  return [
    requireAuth,
    (req, res, next) => {
      if (!roles.includes(req.user.role)) {
        return res.status(403).json({ error: 'Forbidden' });
      }
      next();
    },
  ];
}

// Resource ownership
function requireOwner(getResource) {
  return [
    requireAuth,
    async (req, res, next) => {
      const resource = await getResource(req);
      if (!resource) return res.status(404).json({ error: 'Not found' });
      if (resource.userId !== req.session.userId && req.user.role !== 'admin') {
        return res.status(403).json({ error: 'Not your resource' });
      }
      req.resource = resource;
      next();
    },
  ];
}

// Routes
app.get('/api/articles', requireAuth, listArticles);
app.post('/api/articles', requireAuth, createArticle);
app.delete('/api/articles/:id', ...requireRole('admin', 'editor'), deleteArticle);
app.get('/api/admin/users', ...requireRole('admin'), listUsers);
```

### Fastify Hooks

```typescript
import Fastify from 'fastify';

const app = Fastify();

// Auth decorator
app.decorateRequest('user', null);

app.addHook('preHandler', async (request, reply) => {
  const token = request.headers.authorization?.replace('Bearer ', '');
  if (!token) return; // Public route

  try {
    const payload = await verifyToken(token);
    request.user = payload;
  } catch {
    // Token invalid — let route decide if auth is required
  }
});

// Route-level auth
app.get('/api/protected', {
  preHandler: async (request, reply) => {
    if (!request.user) {
      reply.code(401).send({ error: 'Unauthorized' });
    }
  },
}, async (request) => {
  return { user: request.user };
});
```

## Django

### django.contrib.auth — Built-in Auth

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    # ...
]

AUTH_USER_MODEL = 'accounts.User'  # Custom user model

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Password hashers (order matters — first is used for new passwords)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
```

### Custom User Model

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, default='user')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
```

### View Protection

```python
# Function-based views
from django.contrib.auth.decorators import login_required, permission_required

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@permission_required('articles.delete_article', raise_exception=True)
def delete_article(request, pk):
    # ...
    pass

# Class-based views
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    login_url = '/login/'

class DeleteArticleView(PermissionRequiredMixin, DeleteView):
    permission_required = 'articles.delete_article'
    model = Article
```

### Django REST Framework (DRF)

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        # or 'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# views.py
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView

class ArticleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        articles = Article.objects.filter(author=request.user)
        return Response(ArticleSerializer(articles, many=True).data)

# Custom permission
from rest_framework.permissions import BasePermission

class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user or request.user.is_staff
```

### Django AllAuth (OAuth)

```bash
pip install django-allauth
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
]

MIDDLEWARE = [
    # ...
    'allauth.account.middleware.AccountMiddleware',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ['GOOGLE_CLIENT_ID'],
            'secret': os.environ['GOOGLE_CLIENT_SECRET'],
        },
        'SCOPE': ['profile', 'email'],
    },
}

ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
LOGIN_REDIRECT_URL = '/dashboard/'
```

## FastAPI

### OAuth2 Password Bearer

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"

class TokenData(BaseModel):
    user_id: str
    role: str

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role", "user")
        if user_id is None:
            raise credentials_exception
        return TokenData(user_id=user_id, role=role)
    except JWTError:
        raise credentials_exception

def require_role(*roles: str):
    async def checker(user: TokenData = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

# Routes
@app.get("/api/profile")
async def get_profile(user: TokenData = Depends(get_current_user)):
    return {"user_id": user.user_id, "role": user.role}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, admin: TokenData = Depends(require_role("admin"))):
    # ...
    pass

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    access_token = create_access_token(data={"sub": user.id, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}
```

### FastAPI with Sessions

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"])

@app.post("/login")
async def login(request: Request, credentials: LoginSchema):
    user = await authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=401)
    request.session["user_id"] = user.id
    return {"message": "Logged in"}

async def get_session_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

## Laravel

### Sanctum (SPA + API Token Auth)

```bash
composer require laravel/sanctum
php artisan vendor:publish --provider="Laravel\Sanctum\SanctumServiceProvider"
php artisan migrate
```

```php
// app/Http/Kernel.php — add to 'api' middleware group
'api' => [
    \Laravel\Sanctum\Http\Middleware\EnsureFrontendRequestsAreStateful::class,
    'throttle:api',
    \Illuminate\Routing\Middleware\SubstituteBindings::class,
],

// routes/api.php
Route::middleware('auth:sanctum')->group(function () {
    Route::get('/user', function (Request $request) {
        return $request->user();
    });

    Route::apiResource('articles', ArticleController::class);
});

// Issue token (API)
$token = $user->createToken('api-token', ['read', 'write']);
return ['token' => $token->plainTextToken];

// Check ability
if ($user->tokenCan('write')) {
    // ...
}
```

### Fortify (Headless Auth Backend)

```bash
composer require laravel/fortify
php artisan vendor:publish --provider="Laravel\Fortify\FortifyServiceProvider"
```

```php
// config/fortify.php
'features' => [
    Features::registration(),
    Features::resetPasswords(),
    Features::emailVerification(),
    Features::updateProfileInformation(),
    Features::updatePasswords(),
    Features::twoFactorAuthentication(),
],
```

### Breeze (Full Auth Scaffolding)

```bash
composer require laravel/breeze --dev
php artisan breeze:install
# Options: blade, react, vue, api
php artisan migrate
npm install && npm run dev
```

### Route Protection

```php
// Middleware
Route::get('/dashboard', function () {
    return view('dashboard');
})->middleware(['auth', 'verified']);

// Role gate
// app/Providers/AuthServiceProvider.php
Gate::define('delete-article', function (User $user, Article $article) {
    return $user->id === $article->user_id || $user->role === 'admin';
});

// In controller
if (Gate::denies('delete-article', $article)) {
    abort(403);
}

// Policy
class ArticlePolicy {
    public function delete(User $user, Article $article): bool {
        return $user->id === $article->user_id || $user->role === 'admin';
    }
}

// Controller
$this->authorize('delete', $article);
```

## Go (net/http)

### Middleware Pattern

```go
package middleware

import (
    "context"
    "net/http"
    "strings"
)

type contextKey string
const UserContextKey contextKey = "user"

type User struct {
    ID   string
    Role string
}

func AuthMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Extract token from Authorization header
        authHeader := r.Header.Get("Authorization")
        if !strings.HasPrefix(authHeader, "Bearer ") {
            http.Error(w, "Unauthorized", http.StatusUnauthorized)
            return
        }

        token := strings.TrimPrefix(authHeader, "Bearer ")
        claims, err := VerifyToken(token)
        if err != nil {
            http.Error(w, "Invalid token", http.StatusUnauthorized)
            return
        }

        user := &User{ID: claims.Subject, Role: claims.Role}
        ctx := context.WithValue(r.Context(), UserContextKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func RequireRole(roles ...string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            user, ok := r.Context().Value(UserContextKey).(*User)
            if !ok {
                http.Error(w, "Unauthorized", http.StatusUnauthorized)
                return
            }

            allowed := false
            for _, role := range roles {
                if user.Role == role {
                    allowed = true
                    break
                }
            }

            if !allowed {
                http.Error(w, "Forbidden", http.StatusForbidden)
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}

// Usage with Chi router
r := chi.NewRouter()
r.Use(AuthMiddleware)

r.Route("/api", func(r chi.Router) {
    r.Get("/articles", listArticles)
    r.With(RequireRole("admin", "editor")).Post("/articles", createArticle)
    r.With(RequireRole("admin")).Delete("/articles/{id}", deleteArticle)
})
```

### gorilla/sessions

```go
import (
    "github.com/gorilla/sessions"
    "net/http"
)

var store = sessions.NewCookieStore([]byte(os.Getenv("SESSION_SECRET")))

func init() {
    store.Options = &sessions.Options{
        Path:     "/",
        MaxAge:   86400 * 7,
        HttpOnly: true,
        Secure:   true,
        SameSite: http.SameSiteLaxMode,
    }
}

func LoginHandler(w http.ResponseWriter, r *http.Request) {
    // ... validate credentials ...

    session, _ := store.Get(r, "session")
    session.Values["user_id"] = user.ID
    session.Values["role"] = user.Role
    session.Save(r, w)

    json.NewEncoder(w).Encode(map[string]string{"message": "logged in"})
}

func SessionMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        session, _ := store.Get(r, "session")
        userID, ok := session.Values["user_id"].(string)
        if !ok || userID == "" {
            http.Error(w, "Unauthorized", http.StatusUnauthorized)
            return
        }
        ctx := context.WithValue(r.Context(), UserContextKey, &User{
            ID:   userID,
            Role: session.Values["role"].(string),
        })
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

## SvelteKit

### hooks.server.ts — Session Validation

```typescript
// src/hooks.server.ts
import type { Handle } from '@sveltejs/kit';
import { validateSession } from '$lib/server/auth';

export const handle: Handle = async ({ event, resolve }) => {
  const sessionToken = event.cookies.get('session-token');

  if (sessionToken) {
    const { user, session } = await validateSession(sessionToken);
    event.locals.user = user;
    event.locals.session = session;

    // Refresh session cookie if needed
    if (session?.fresh) {
      event.cookies.set('session-token', sessionToken, {
        path: '/',
        httpOnly: true,
        secure: true,
        sameSite: 'lax',
        maxAge: 60 * 60 * 24 * 30,
      });
    }
  } else {
    event.locals.user = null;
    event.locals.session = null;
  }

  return resolve(event);
};
```

### Page Protection (load function)

```typescript
// src/routes/dashboard/+page.server.ts
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
  if (!locals.user) {
    throw redirect(302, '/login');
  }

  return {
    user: locals.user,
  };
};
```

### Layout-Level Protection

```typescript
// src/routes/(protected)/+layout.server.ts
import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
  if (!locals.user) {
    throw redirect(302, '/login');
  }
  return { user: locals.user };
};
```

### Form Action (Server-Side)

```typescript
// src/routes/login/+page.server.ts
import type { Actions } from './$types';
import { fail, redirect } from '@sveltejs/kit';

export const actions: Actions = {
  login: async ({ request, cookies }) => {
    const data = await request.formData();
    const email = data.get('email') as string;
    const password = data.get('password') as string;

    const user = await authenticateUser(email, password);
    if (!user) {
      return fail(400, { error: 'Invalid credentials', email });
    }

    const session = await createSession(user.id);
    cookies.set('session-token', session.id, {
      path: '/',
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 30,
    });

    throw redirect(302, '/dashboard');
  },

  logout: async ({ cookies, locals }) => {
    if (locals.session) {
      await invalidateSession(locals.session.id);
    }
    cookies.delete('session-token', { path: '/' });
    throw redirect(302, '/login');
  },
};
```

### App.d.ts Types

```typescript
// src/app.d.ts
declare global {
  namespace App {
    interface Locals {
      user: {
        id: string;
        email: string;
        name: string;
        role: string;
      } | null;
      session: {
        id: string;
        expiresAt: Date;
        fresh?: boolean;
      } | null;
    }
  }
}

export {};
```

## Summary — Quick Decision Guide

| Framework | Easiest Auth Solution | Session Store |
|-----------|----------------------|---------------|
| Next.js App Router | Auth.js v5 or Better Auth | JWT cookie or DB |
| Next.js Pages Router | Auth.js v5 | JWT cookie or DB |
| Express | Passport.js + express-session | Redis |
| Fastify | @fastify/passport | Redis |
| Django | django.contrib.auth + allauth | DB (default) |
| FastAPI | python-jose + Depends() | Redis or DB |
| Laravel | Sanctum + Breeze | DB (default) |
| Go | Custom middleware + golang-jwt | Redis or cookie |
| SvelteKit | Better Auth or Lucia | DB |
| Astro | Lucia or Better Auth | DB |
