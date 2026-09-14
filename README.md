# TPGamesPlus_BE

Backend API for the TPGamesPlus digital game items catalog: JWT auth, paginated/filterable product listing, product detail, and a purchase flow that returns a receipt.

Stack: Django 5 + Django REST Framework, PostgreSQL, `djangorestframework-simplejwt`, `drf-spectacular` (docs), `django-filter`.

## Requirements

- Python 3.12+
- Docker Desktop (for PostgreSQL) — or a PostgreSQL instance you point the env vars at instead

## Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
Copy-Item .env.example .env
# edit .env if you need different DB credentials/ports

# 4. Start PostgreSQL
docker compose up -d db

# 5. Apply migrations
python manage.py migrate

# 6. Seed a demo user for login/grading
python manage.py create_demo_user --username demo --password demoPass123!

# 7. Run the server
python manage.py runserver
```

`items.csv` (in `data/items.csv`) is imported automatically the first time the server starts (see [Design decisions](#design-decisions--assumptions)) — there's no separate manual import step required. To re-run it explicitly (e.g. after editing the CSV):

```powershell
python manage.py import_products --file data/items.csv
```

The API is served at `http://127.0.0.1:8000/`.

## Running tests

```powershell
pytest -v
```

## API endpoints

All endpoints except login/refresh/docs require `Authorization: Bearer <access_token>`.

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/login/` | body `{"username", "password"}` → `{access, refresh}` |
| POST | `/api/auth/refresh/` | body `{"refresh"}` → `{access}` |
| GET | `/api/products/` | `?page=&page_size=&location=JO\|SA` (page_size default 10, max 50) |
| GET | `/api/products/{id}/` | product detail |
| POST | `/api/orders/` | body `{"product": <id>}` → creates an order, returns a receipt |
| GET | `/api/orders/{id}/` | re-fetch a receipt (only your own orders; 404 otherwise) |
| GET | `/api/docs/` | Swagger UI (public) |
| GET | `/api/schema/` | raw OpenAPI schema (public) |

### Example requests (curl)

```bash
# Login
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demoPass123!"}'

# List products (JO only, page 2)
curl "http://127.0.0.1:8000/api/products/?location=JO&page=2" \
  -H "Authorization: Bearer <access_token>"

# Product detail
curl http://127.0.0.1:8000/api/products/1/ \
  -H "Authorization: Bearer <access_token>"

# Buy a product
curl -X POST http://127.0.0.1:8000/api/orders/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"product": 1}'

# Re-fetch a receipt
curl http://127.0.0.1:8000/api/orders/1/ \
  -H "Authorization: Bearer <access_token>"
```

Error responses are normalized to:

```json
{"error": {"code": 400, "message": "product: Invalid pk \"9999\" - object does not exist."}}
```

## Design decisions & assumptions

- **PostgreSQL** was chosen over SQLite/MySQL for relational integrity between orders and products (`PROTECT` FKs), solid transactional guarantees for the purchase write path, and it's free/open-source and one of the assignment's suggested options.
- **Quantity is always 1** — the assignment states "only one product per request," so `Order` has no quantity field; buying twice creates two separate orders.
- **No public signup** — the assignment only asks to "validate credentials," so users are seeded via `create_demo_user`, not a registration endpoint.
- **Price has no currency field** — the source CSV doesn't include one; it's stored as a plain `Decimal`.
- **`external_id`** (the CSV's `id` column) is a unique field on `Product`, separate from the Django PK, so `import_products` can safely re-run (`update_or_create`) without duplicating rows.
- **CSV import runs automatically on server startup** (`CatalogConfig.ready()`), guarded so it only fires once per real server process — it skips non-server management commands (`migrate`/`test`/`shell`/`check`/pytest) and the dev autoreloader's parent watcher process, so it isn't triggered twice or run against an unmigrated DB.
- **Product reads are served from an in-process map** (`catalog/store.py`: `{id: json_string}` + a location index), rebuilt at startup and after every re-import, instead of hitting the DB (or a cache framework/Redis) on every request. This was chosen over Redis to avoid extra infrastructure for now; the trade-off is the map is per-process, so it isn't shared across multiple worker processes without adding a shared cache later.
- **JWT lifetimes**: access tokens expire after 30 minutes, refresh tokens after 1 day (`SIMPLE_JWT` in `core/settings.py`).
- **Product list `page_size` is capped at 50** (`core/pagination.py`) so a caller can't request an unbounded result set.
- **Login is rate-limited** (`AnonRateThrottle`, 5/min) as basic brute-force protection, since credentials are the only gate into the API.
