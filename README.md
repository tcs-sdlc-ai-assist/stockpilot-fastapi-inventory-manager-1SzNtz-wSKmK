# StockPilot

**Inventory Management System** — A modern, full-stack inventory management application built with Python, FastAPI, and Tailwind CSS.

## Features

- **User Authentication & Authorization** — JWT-based auth with role-based access control (Admin / Staff)
- **Inventory Management** — Full CRUD operations for inventory items with categories, quantities, and pricing
- **Category Management** — Organize items into categories for easy browsing and filtering
- **Dashboard & Analytics** — Overview of stock levels, low-stock alerts, and inventory value summaries
- **Search & Filter** — Search items by name, filter by category, sort by various fields
- **Activity Logging** — Track inventory changes with a full audit trail
- **Responsive UI** — Server-rendered templates styled with Tailwind CSS for desktop and mobile
- **CSV Export** — Export inventory data for reporting and external analysis

## Tech Stack

| Layer         | Technology                          |
|---------------|-------------------------------------|
| Backend       | Python 3.12, FastAPI, Uvicorn       |
| Database      | SQLAlchemy 2.0 (async), SQLite/PostgreSQL |
| Auth          | JWT (python-jose), bcrypt           |
| Validation    | Pydantic v2                         |
| Templates     | Jinja2, Tailwind CSS                |
| Testing       | pytest, pytest-asyncio, httpx       |
| Configuration | pydantic-settings, python-dotenv    |

## Folder Structure

```
stockpilot/
├── main.py                  # FastAPI application entry point
├── config.py                # Application settings (pydantic-settings)
├── database.py              # SQLAlchemy engine, session, and Base
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── README.md                # This file
│
├── models/                  # SQLAlchemy ORM models
│   ├── __init__.py
│   ├── user.py              # User model (Admin / Staff roles)
│   ├── category.py          # Category model
│   ├── item.py              # InventoryItem model
│   └── activity_log.py      # ActivityLog model (audit trail)
│
├── schemas/                 # Pydantic request/response schemas
│   ├── __init__.py
│   ├── user.py
│   ├── category.py
│   ├── item.py
│   └── activity_log.py
│
├── routes/                  # FastAPI route handlers
│   ├── __init__.py
│   ├── auth.py              # Login, register, token refresh
│   ├── users.py             # User management (Admin only)
│   ├── categories.py        # Category CRUD
│   ├── items.py             # Inventory item CRUD
│   ├── dashboard.py         # Dashboard / analytics endpoints
│   └── activity_logs.py     # Activity log viewing
│
├── services/                # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py
│   ├── user_service.py
│   ├── category_service.py
│   ├── item_service.py
│   └── activity_log_service.py
│
├── dependencies/            # FastAPI dependency injection
│   ├── __init__.py
│   ├── auth.py              # get_current_user, require_admin
│   └── database.py          # get_db session dependency
│
├── templates/               # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── items/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── form.html
│   └── categories/
│       ├── list.html
│       └── form.html
│
├── static/                  # Static assets
│   └── css/
│       └── output.css       # Compiled Tailwind CSS
│
└── tests/                   # Test suite
    ├── __init__.py
    ├── conftest.py           # Shared fixtures (test DB, client, auth)
    ├── test_auth.py
    ├── test_users.py
    ├── test_categories.py
    ├── test_items.py
    └── test_dashboard.py
```

## Setup Instructions

### Prerequisites

- Python 3.12+
- pip (or a virtual environment manager like `uv`, `poetry`, or `venv`)

### Local Development

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd stockpilot
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your settings (see [Environment Variables](#environment-variables) below).

5. **Run the development server:**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application:**

   - Web UI: [http://localhost:8000](http://localhost:8000)
   - API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
   - API Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Vercel Deployment

1. Install the [Vercel CLI](https://vercel.com/docs/cli):

   ```bash
   npm i -g vercel
   ```

2. Create a `vercel.json` in the project root:

   ```json
   {
     "builds": [
       { "src": "main.py", "use": "@vercel/python" }
     ],
     "routes": [
       { "src": "/(.*)", "dest": "main.py" }
     ]
   }
   ```

3. Set environment variables in the Vercel dashboard (see below).

4. Deploy:

   ```bash
   vercel --prod
   ```

## Environment Variables

| Variable              | Description                                    | Default                  | Required |
|-----------------------|------------------------------------------------|--------------------------|----------|
| `DATABASE_URL`        | Database connection string                     | `sqlite+aiosqlite:///./stockpilot.db` | No  |
| `SECRET_KEY`          | JWT signing secret (use a strong random value) | —                        | **Yes**  |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime in minutes  | `30`                     | No       |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | JWT refresh token lifetime in days    | `7`                      | No       |
| `ENVIRONMENT`         | Runtime environment (`development`, `production`) | `development`         | No       |
| `CORS_ORIGINS`        | Comma-separated list of allowed CORS origins   | `http://localhost:3000`  | No       |
| `ADMIN_EMAIL`         | Default admin account email (created on first run) | `admin@stockpilot.local` | No  |
| `ADMIN_PASSWORD`      | Default admin account password                 | —                        | **Yes** (first run) |
| `LOG_LEVEL`           | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO`              | No       |

### Example `.env` file

```env
DATABASE_URL=sqlite+aiosqlite:///./stockpilot.db
SECRET_KEY=your-super-secret-key-change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
ADMIN_EMAIL=admin@stockpilot.local
ADMIN_PASSWORD=changeme123
LOG_LEVEL=INFO
```

## Usage Guide

### Admin Role

Admins have full access to all features:

| Action                  | Endpoint / UI Path         | Description                              |
|-------------------------|----------------------------|------------------------------------------|
| **Manage Users**        | `GET /api/users`           | List, create, update, and deactivate user accounts |
| **Manage Categories**   | `GET /api/categories`      | Create, edit, and delete inventory categories |
| **Manage Items**        | `GET /api/items`           | Full CRUD on all inventory items         |
| **View Dashboard**      | `GET /api/dashboard`       | Inventory summary, low-stock alerts, value totals |
| **View Activity Logs**  | `GET /api/activity-logs`   | Full audit trail of all inventory changes |
| **Export Data**         | `GET /api/items/export`    | Download inventory data as CSV           |

### Staff Role

Staff members can manage inventory but cannot manage users:

| Action                  | Endpoint / UI Path         | Description                              |
|-------------------------|----------------------------|------------------------------------------|
| **View Categories**     | `GET /api/categories`      | Browse categories (read-only)            |
| **Manage Items**        | `GET /api/items`           | Create, edit, and update inventory items |
| **View Dashboard**      | `GET /api/dashboard`       | Inventory summary and low-stock alerts   |
| **View Activity Logs**  | `GET /api/activity-logs`   | View own activity history                |

### API Authentication

All API endpoints (except login/register) require a valid JWT token:

```bash
# Login to get a token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@stockpilot.local", "password": "changeme123"}'

# Use the token in subsequent requests
curl http://localhost:8000/api/items \
  -H "Authorization: Bearer <your-access-token>"
```

## Testing

### Run the full test suite

```bash
pytest
```

### Run with verbose output

```bash
pytest -v
```

### Run a specific test file

```bash
pytest tests/test_auth.py
```

### Run with coverage report

```bash
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
```

### Test structure

- **`tests/conftest.py`** — Shared fixtures: in-memory SQLite database, async test client, authenticated user helpers
- **`tests/test_auth.py`** — Authentication flow: login, register, token refresh, invalid credentials
- **`tests/test_users.py`** — User management: CRUD, role enforcement, admin-only access
- **`tests/test_categories.py`** — Category CRUD and validation
- **`tests/test_items.py`** — Inventory item CRUD, search, filtering, low-stock detection
- **`tests/test_dashboard.py`** — Dashboard analytics and summary data

## API Documentation

Once the server is running, interactive API documentation is available at:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## License

**Private** — All rights reserved. This software is proprietary and confidential. Unauthorized copying, distribution, or modification is strictly prohibited.