# StockPilot Deployment Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Vercel Deployment](#vercel-deployment)
  - [vercel.json Explanation](#verceljson-explanation)
  - [Deploy via Vercel CLI](#deploy-via-vercel-cli)
  - [Deploy via Vercel Dashboard](#deploy-via-vercel-dashboard)
- [CI/CD Notes](#cicd-notes)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying StockPilot, ensure you have the following installed and configured:

- **Python 3.12+** — the runtime used for the FastAPI backend
- **pip** — Python package manager (bundled with Python 3.12)
- **Git** — version control for pushing code to your repository
- **Vercel CLI** (optional) — install globally via `npm i -g vercel` for CLI-based deployments
- **A Vercel account** — sign up at [vercel.com](https://vercel.com) if you don't have one
- **A GitHub / GitLab / Bitbucket account** — for connecting your repository to Vercel's dashboard

### Python Dependencies

All dependencies are listed in `requirements.txt`. Install them locally with:

```bash
pip install -r requirements.txt
```

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/stockpilot.git
cd stockpilot
```

### 2. Create a Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # macOS / Linux
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your editor of choice (see [Environment Variables](#environment-variables) below for all required keys).

### 5. Run the Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs are at:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### 6. Run Tests

```bash
pytest -v
```

For async test support, ensure `pytest-asyncio` and `httpx` are installed (both are in `requirements.txt`).

---

## Environment Variables

Configure the following environment variables in your `.env` file (local) or in the Vercel project settings (production):

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | ✅ | Secret key for JWT token signing. Use a long random string. | `a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5` |
| `DATABASE_URL` | ✅ | Database connection string. Use PostgreSQL for production. | `postgresql+asyncpg://user:pass@host:5432/stockpilot` |
| `ENVIRONMENT` | ❌ | Deployment environment (`development`, `staging`, `production`). Defaults to `development`. | `production` |
| `ALLOWED_ORIGINS` | ❌ | Comma-separated list of allowed CORS origins. | `https://stockpilot.vercel.app,https://yourdomain.com` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | JWT access token expiration in minutes. Defaults to `30`. | `60` |
| `LOG_LEVEL` | ❌ | Logging level. Defaults to `INFO`. | `DEBUG` |

### Setting Environment Variables on Vercel

**Via CLI:**

```bash
vercel env add SECRET_KEY production
vercel env add DATABASE_URL production
```

**Via Dashboard:**

1. Go to your project on [vercel.com](https://vercel.com)
2. Navigate to **Settings → Environment Variables**
3. Add each variable with the appropriate scope (Production, Preview, Development)

> **⚠️ Important:** Never commit your `.env` file to version control. Ensure `.env` is listed in `.gitignore`.

---

## Vercel Deployment

### vercel.json Explanation

The `vercel.json` file configures how Vercel builds and routes your FastAPI application:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ]
}
```

**Breakdown:**

| Key | Purpose |
|---|---|
| `version` | Vercel platform version. Always use `2`. |
| `builds[0].src` | Entry point for the Python application. Must point to the file containing the FastAPI `app` instance. |
| `builds[0].use` | Specifies the Vercel Python runtime builder (`@vercel/python`). This builder reads `requirements.txt` automatically. |
| `routes[0]` | Routes requests to `/static/*` directly to the static files directory, bypassing the Python handler for better performance. |
| `routes[1]` | Catch-all route that sends every other request to `main.py` (the FastAPI app). |

### Deploy via Vercel CLI

#### First-Time Setup

```bash
# Install Vercel CLI globally
npm i -g vercel

# Login to your Vercel account
vercel login

# Link your project (run from the project root)
vercel link
```

#### Deploy to Preview

```bash
vercel
```

This creates a preview deployment with a unique URL (e.g., `stockpilot-abc123.vercel.app`).

#### Deploy to Production

```bash
vercel --prod
```

This deploys to your production domain.

#### Useful CLI Commands

```bash
# View deployment logs
vercel logs <deployment-url>

# List all deployments
vercel ls

# Pull environment variables locally
vercel env pull .env.local

# Inspect a deployment
vercel inspect <deployment-url>
```

### Deploy via Vercel Dashboard

1. **Import Project:**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Select your Git provider (GitHub, GitLab, Bitbucket)
   - Choose the `stockpilot` repository

2. **Configure Project:**
   - **Framework Preset:** Select `Other`
   - **Root Directory:** Leave as `.` (or set if your code is in a subdirectory)
   - **Build Command:** Leave empty (the `@vercel/python` builder handles this)
   - **Output Directory:** Leave empty

3. **Set Environment Variables:**
   - Add all required environment variables (see [Environment Variables](#environment-variables))
   - Set the scope to **Production** (and optionally **Preview**)

4. **Deploy:**
   - Click **Deploy**
   - Vercel will build and deploy your application automatically

5. **Automatic Deployments:**
   - Every push to `main` triggers a production deployment
   - Every push to other branches triggers a preview deployment
   - Pull requests get automatic preview deployments with unique URLs

---

## CI/CD Notes

### GitHub Actions Integration

Vercel integrates natively with GitHub. Once connected, deployments are automatic. However, you may want to run tests before deploying. Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run linting
        run: |
          pip install ruff
          ruff check .

      - name: Run tests
        env:
          SECRET_KEY: test-secret-key-for-ci
          DATABASE_URL: sqlite+aiosqlite:///./test.db
          ENVIRONMENT: development
        run: |
          pytest -v --tb=short
```

### Branch Strategy

| Branch | Vercel Environment | Purpose |
|---|---|---|
| `main` | Production | Live production deployment |
| `develop` | Preview | Integration testing |
| Feature branches | Preview | Per-feature preview URLs |

### Protecting Production Deployments

1. In Vercel Dashboard → **Settings → Git**
2. Enable **Production Branch Protection**
3. Require status checks (CI tests) to pass before deploying

---

## Troubleshooting

### Static Files Not Loading (404 on `/static/*`)

**Symptom:** CSS, JS, or image files return 404 in production.

**Cause:** Vercel's serverless functions don't serve static files the same way a traditional server does. The `routes` configuration in `vercel.json` must explicitly handle static file paths.

**Fix:**

1. Ensure your `vercel.json` has the static route **before** the catch-all route:

   ```json
   {
     "routes": [
       { "src": "/static/(.*)", "dest": "/static/$1" },
       { "src": "/(.*)", "dest": "main.py" }
     ]
   }
   ```

2. If using FastAPI's `StaticFiles` mount, ensure the directory exists and is included in the deployment:

   ```python
   from fastapi.staticfiles import StaticFiles
   app.mount("/static", StaticFiles(directory="static"), name="static")
   ```

3. Verify the `static/` directory is **not** listed in `.vercelignore`.

### SQLite Persistence Issues

**Symptom:** Data disappears between requests or after redeployment.

**Cause:** Vercel serverless functions run in ephemeral containers. The filesystem is read-only (except `/tmp`), and any files written to `/tmp` are lost when the container is recycled (typically after a few minutes of inactivity).

**Fix:**

- **Do NOT use SQLite in production on Vercel.** SQLite requires a persistent, writable filesystem that Vercel does not provide.
- Use a managed PostgreSQL database instead:
  - [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) (built-in)
  - [Neon](https://neon.tech) (serverless PostgreSQL, generous free tier)
  - [Supabase](https://supabase.com) (PostgreSQL with extras)
  - [Railway](https://railway.app) (managed PostgreSQL)
- Update your `DATABASE_URL` environment variable:

  ```
  DATABASE_URL=postgresql+asyncpg://user:password@host:5432/stockpilot
  ```

- SQLite is perfectly fine for **local development** and **testing**.

### Import Errors on Vercel

**Symptom:** Deployment fails with `ModuleNotFoundError` or `ImportError`.

**Common Causes and Fixes:**

1. **Missing dependency in `requirements.txt`:**

   ```
   ModuleNotFoundError: No module named 'pydantic_settings'
   ```

   **Fix:** Ensure the package is listed in `requirements.txt`. Remember that PyPI names differ from import names:

   | PyPI Package | Python Import |
   |---|---|
   | `pydantic-settings` | `pydantic_settings` |
   | `python-jose[cryptography]` | `jose` |
   | `python-multipart` | `multipart` |
   | `python-dotenv` | `dotenv` |

2. **Incorrect import paths:**

   ```
   ModuleNotFoundError: No module named 'app.models'
   ```

   **Fix:** Verify your import paths match the actual file structure. For flat project structures (no `app/` package), use direct imports:

   ```python
   # Correct (flat structure)
   from models.user import User
   from database import get_db

   # Wrong (assumes app/ package that doesn't exist)
   from app.models.user import User
   from app.database import get_db
   ```

3. **Missing `__init__.py` files:**

   **Fix:** Ensure every Python package directory has an `__init__.py` file:

   ```
   models/__init__.py
   routes/__init__.py
   services/__init__.py
   ```

4. **Circular imports:**

   ```
   ImportError: cannot import name 'User' from partially initialized module 'models.user'
   ```

   **Fix:** Restructure imports to avoid circular dependencies. Models should never import from routes or services. Use dependency injection and type hints with `TYPE_CHECKING`:

   ```python
   from __future__ import annotations
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from models.user import User
   ```

### Cold Start Latency

**Symptom:** First request after inactivity takes 3–10 seconds.

**Cause:** Vercel serverless functions have cold starts. The Python runtime and all dependencies must be loaded on the first invocation.

**Mitigation:**

- Minimize the number of dependencies in `requirements.txt`
- Use lazy imports for heavy libraries (load them inside functions, not at module level)
- Consider Vercel's [Fluid Compute](https://vercel.com/docs/functions/fluid-compute) for reduced cold starts
- Set up a cron job or health check to ping your API periodically and keep the function warm:

  ```bash
  # Example: ping every 5 minutes
  curl -s https://stockpilot.vercel.app/health > /dev/null
  ```

### CORS Errors

**Symptom:** Browser console shows `Access-Control-Allow-Origin` errors.

**Fix:**

1. Ensure `ALLOWED_ORIGINS` environment variable is set with your frontend domain(s)
2. Verify `CORSMiddleware` is configured in `main.py`:

   ```python
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=settings.allowed_origins,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. Never use `allow_origins=["*"]` in production — always specify exact origins.

### Build Timeout

**Symptom:** Deployment fails with a timeout during the build step.

**Fix:**

- Vercel's free tier has a 45-second build timeout. If your dependencies take too long to install:
  - Remove unused packages from `requirements.txt`
  - Pin exact versions to avoid resolver overhead: `fastapi==0.115.0` instead of `fastapi>=0.100`
  - Upgrade to Vercel Pro for extended build times (up to 5 minutes)

### Checking Deployment Logs

**Via CLI:**

```bash
vercel logs https://your-deployment-url.vercel.app
```

**Via Dashboard:**

1. Go to your project on Vercel
2. Click on the deployment
3. Navigate to **Functions** tab
4. Click on a function invocation to see logs

**In your FastAPI code**, use Python's `logging` module (not `print()`):

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Processing request for user %s", user_id)
```

---

## Production Checklist

Before deploying to production, verify the following:

- [ ] `SECRET_KEY` is set to a strong, unique random value (at least 32 characters)
- [ ] `DATABASE_URL` points to a managed PostgreSQL instance (not SQLite)
- [ ] `ENVIRONMENT` is set to `production`
- [ ] `ALLOWED_ORIGINS` contains only your actual frontend domain(s)
- [ ] All tests pass (`pytest -v`)
- [ ] `.env` file is in `.gitignore`
- [ ] No hardcoded secrets in source code
- [ ] CORS is configured with explicit origins (not `*`)
- [ ] Passwords are hashed with bcrypt (never stored in plain text)
- [ ] Rate limiting is configured for authentication endpoints
- [ ] Database migrations are applied (if using Alembic)