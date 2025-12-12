# OAuth2/OIDC + JWT Authentication Guide

This document explains the changes added to this project to:

1. Demonstrate **OAuth2/OIDC login using Google**
2. Issue the service’s **own JWT** after login
3. Enforce **JWT validation** on selected endpoints in both:
   - the **in-memory version** (`main.py`)
   - the **database-backed version** (`main_db.py`)

---

## 1. Summary of Changes

### 1.1 New / Updated Dependencies (`requirements.txt`)

These libraries were added to support OAuth2/OIDC and JWT:

```txt
# Auth / OAuth2 / JWT
authlib==1.3.1                 # Google OAuth2/OIDC client
python-jose[cryptography]==3.3.0   # JWT encode/decode
itsdangerous>=2.1.0            # Required by SessionMiddleware
httpx                           # HTTP client used by authlib
python-dotenv==1.0.1           # Load .env file (already used in project)
```

Install all dependencies with:

```bash
pip install -r requirements.txt
```

### 1.2 Environment Variables (`.env` and `.env.example`)

The following variables were added to `.env.example`:

```env
# OAuth2 / JWT settings (fill in your own values)
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
# For local dev, callback URL should match what you configure in Google console,
# e.g. http://localhost:8000/auth/callback
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# JWT signing key for service-issued tokens
JWT_SECRET_KEY=change-me-in-real-env
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Session secret used by Starlette's SessionMiddleware
SESSION_SECRET_KEY=change-me-session-secret
```

**Local setup:**

1. Copy `.env.example` to `.env`.
2. Fill in:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`
   - `JWT_SECRET_KEY` (long random string)
   - `SESSION_SECRET_KEY` (long random string)

> **Important:** Do not commit `.env` to Git. Only commit `.env.example`.

### 1.3 New Authentication Module: `auth.py`

A new module `auth.py` was added. It contains:

- Environment loading via `python-dotenv`
- Google OAuth2/OIDC client configuration with `authlib`
- JWT creation and validation using `python-jose`
- FastAPI routes:
  - `GET /auth/login` – start Google login
  - `GET /auth/callback` – handle callback, issue service JWT
- A dependency `require_jwt` to protect endpoints

**Key responsibilities:**

Load `.env` to ensure OAuth and JWT settings are available:

```python
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
```

Read configuration:

```python
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
```

Register Google OAuth client:

```python
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID or "missing-client-id",
    client_secret=GOOGLE_CLIENT_SECRET or "missing-client-secret",
    server_metadata_url="[https://accounts.google.com/.well-known/openid-configuration](https://accounts.google.com/.well-known/openid-configuration)",
    client_kwargs={"scope": "openid email profile"},
)
```

JWT helpers:

- `create_access_token(data, expires_delta=None)`
- `decode_access_token(token)`
- `require_jwt(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer))`

`require_jwt` is used as a FastAPI dependency for protected endpoints:

```python
current_user: dict = Depends(require_jwt)
```

OAuth2/OIDC routes:

- **`GET /auth/login`**
  Redirects to Google’s OAuth2/OIDC login page.

- **`GET /auth/callback`**
  Exchanges authorization code for tokens, retrieves user info, then issues a service JWT and returns a JSON payload, for example:

```json
{
  "access_token": "<service_jwt_here>",
  "token_type": "bearer",
  "expires_in_minutes": 60,
  "provider_user": {
    "sub": "google-sub-id",
    "email": "user@example.com"
  }
}
```

### 1.4 In-Memory Version (`main.py`)

The in-memory API is updated to use the new auth module.

Imports:

```python
from fastapi import FastAPI, HTTPException, Response, Depends
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router, require_jwt
```

Add middleware and include auth router:

```python
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "dev-session-secret"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)  # exposes /auth/login and /auth/callback
```

Protect selected endpoints with `require_jwt`
For example, `POST /users` and `DELETE /users/{user_id}`:

```python
@app.post("/users", response_model=UserRead, status_code=201, tags=["users"])
def create_user(
    payload: UserCreate,
    response: Response,
    current_user: dict = Depends(require_jwt),
):
    ...

@app.delete("/users/{user_id}", status_code=204, tags=["users"])
def delete_user(
    user_id: UUID,
    current_user: dict = Depends(require_jwt),
):
    ...
```

Run in-memory version:

```python
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
```

### 1.5 Database-Backed Version (`main_db.py`)

The DB-backed version is similarly updated.

Imports:

```python
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router, require_jwt
```

Add middleware and include auth router:

```python
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "dev-session-secret"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
```

Protect DB-backed user endpoints:

```python
@app.post("/users", response_model=UserRead, status_code=201, tags=["users"])
def create_user(
    payload: UserCreate,
    response: JSONResponse,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_jwt),
):
    ...

@app.delete("/users/{user_id}", status_code=204, tags=["users"])
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_jwt),
):
    ...
```

Run DB-backed version:

```python
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_db:app",
        host="127.0.0.1",
        port=8000,  # or another port if needed
        reload=True,
    )
```

> **Note:** This version requires a reachable database (MySQL, Cloud SQL, or another configured backend).

---

## 2. Google OAuth2/OIDC Setup

To use Google as the OAuth2/OIDC provider:

1. Go to **Google Cloud Console** → select or create a project.
2. Navigate to **APIs & Services** → **OAuth consent screen**:
   - Choose **External** for user type.
   - Add your Google account as a test user.
3. Go to **APIs & Services** → **Credentials**:
   - Click **Create Credentials** → **OAuth client ID**.
   - Application type: **Web application**.
   - Under **Authorized redirect URIs**, add:
     ```text
     http://localhost:8000/auth/callback
     ```
   - Save, then copy:
     - **Client ID** → `GOOGLE_CLIENT_ID` in `.env`
     - **Client Secret** → `GOOGLE_CLIENT_SECRET` in `.env`
4. Set:
   ```env
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
   ```
   *This must match the redirect URI configured in Google Cloud Console exactly.*

---

## 3. Running and Testing – In-Memory Version (`main.py`)

### 3.1 Install Dependencies

```bash
pip install -r requirements.txt
```

### 3.2 Start the Service

From the project root:

```bash
python main.py
```

**Expected:**
- Server runs on `http://127.0.0.1:8000`
- OpenAPI docs at `http://localhost:8000/docs`

### 3.3 Perform OAuth2/OIDC Login and Get JWT

1. In your browser, open:
   ```text
   http://localhost:8000/auth/login
   ```
2. You should be redirected to Google’s login page.
3. After logging in and granting consent, Google redirects back to:
   ```text
   http://localhost:8000/auth/callback?code=...&state=...
   ```
4. The `/auth/callback` endpoint returns JSON. Example:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "expires_in_minutes": 60,
     "provider_user": {
       "sub": "1234567890",
       "email": "your-email@example.com"
     }
   }
   ```
5. **Copy the `access_token` value.** This is the service-issued JWT.

### 3.4 Test Protected Endpoints with JWT (In-Memory)

Open Swagger UI:
`http://localhost:8000/docs`

#### Test 1 – Without JWT (should be rejected)
1. Expand `POST /users` under the `users` tag.
2. Click **Try it out**.
3. Provide a valid JSON body, for example:
   ```json
   {
     "name": "MemUser",
     "email": "memuser@example.com",
     "phone": "+11234567890",
     "membership_tier": "FREE",
     "password": "StrongPass123!"
   }
   ```
4. Do not set any Authorization header. Click **Execute**.

**Expected result:**
- **HTTP 401 Unauthorized**
- Response body similar to:
  ```json
  {"detail": "Missing Authorization: Bearer token"}
  ```

#### Test 2 – With JWT (should be allowed)
1. Click the **Authorize** button in the top-right of Swagger.
2. In the value field, type:
   ```text
   Bearer <access_token>
   ```
   Example:
   ```text
   Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
3. Click **Authorize** → **Close**.
4. Call `POST /users` again with the same body.

**Expected result:**
- **HTTP 201 Created**
- Response body with the created user (stored in memory).

Similarly for `DELETE /users/{user_id}`:
- Without JWT → **401**
- With valid JWT → **204** (user deleted), or **404** if not found.

---

## 4. Running and Testing – Database Version (`main_db.py`)

This version needs a working database (e.g., MySQL) reachable with the connection details in `.env`.

### 4.1 Ensure Database Is Running

Configure variables like:

```env
CATALOG_DB_HOST=...
CATALOG_DB_PORT=3306
CATALOG_DB_USER=...
CATALOG_DB_NAME=user_profile_db
DB_PASSWORD_SECRET=...
```

Make sure the database is up and accepting connections from your machine.

### 4.2 Start the DB-Backed Service

```bash
python main_db.py
```

If the DB connection is correct, the service will start on:
`http://127.0.0.1:8000`

Swagger UI is at:
`http://localhost:8000/docs`

### 4.3 OAuth2 Login and JWT (Same as In-Memory)
1. Browser → `http://localhost:8000/auth/login`
2. Log in with Google → redirected back to `/auth/callback`
3. Copy `access_token` from the JSON response.

### 4.4 Test Protected Endpoints (DB Version)
1. Again, go to: `http://localhost:8000/docs`
2. Click **Authorize**, enter:
   ```text
   Bearer <access_token>
   ```
3. Call `POST /users` with a valid body.

**Expected:**
- Without JWT → **401**
- With JWT → **201**, and the new user is stored in the database.

Use `GET /users` or direct DB queries to verify the data.

---

## 5. What to Highlight in a Report

- **Authentication:**
  Google OAuth2/OIDC is used for user authentication (`/auth/login` → `/auth/callback`).

- **Token issuing:**
  The service uses `python-jose` with `HS256` and `JWT_SECRET_KEY` to issue its own JWT in `/auth/callback`.

- **Authorization:**
  Both the in-memory (`main.py`) and DB-backed (`main_db.py`) implementations protect selected endpoints (e.g., `POST /users`, `DELETE /users/{user_id}`) using `Depends(require_jwt)`.

- **Behavior:**
  - Requests **without** `Authorization: Bearer <token>` → **401 Unauthorized**.
  - Requests **with** a valid JWT obtained via the OAuth2 flow → allowed and processed normally.

This fully demonstrates OAuth2/OIDC login with Google, custom JWT issuing, and JWT-based authorization on microservice endpoints in both versions of the service.