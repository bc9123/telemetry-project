# Telemetry Platform

A production-style IoT telemetry ingestion and alerting backend built with **FastAPI**, **PostgreSQL**, **Redis**, and **Celery**.

Devices stream time-series data to the platform, which evaluates configurable alerting rules and delivers notifications via webhooks — all asynchronously and at scale.

---

## Architecture

```
Device → POST /telemetry (API key auth)
              ↓
         FastAPI API
              ↓ (Celery task)
         Worker: ingest_events
              ↓
         PostgreSQL (bulk insert)
              ↓ (Celery task)
         Worker: evaluate_rules_for_device
              ↓ (k-of-n match + advisory lock)
         Alert created
              ↓ (Celery task)
         Worker: webhook_delivery
              ↓ (circuit breaker via Redis)
         HTTP POST → subscriber endpoint
```

**Key components:**

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Task queue | Celery + Redis |
| Database | PostgreSQL (SQLAlchemy 2.0, Alembic) |
| Circuit breaker state | Redis |
| Auth | Hashed API keys (bcrypt, `prefix.secret` format) |
| Rate limiting | slowapi (per-key + per-IP fallback) |
| Structured logging | structlog |
| Testing | pytest + testcontainers |

---

## Features

### Telemetry Ingestion
Accepts batches of up to 5,000 timestamped JSON events per request. Ingestion is fire-and-forget — the API returns `202 Accepted` immediately and a Celery worker bulk-inserts the events.

### k-of-n Rule Evaluation
Rules are evaluated after every ingest. Each rule defines a sliding window of the last **N** events, and fires an alert only if at least **K** of those events breach the threshold. This prevents noisy alerting from single-point spikes.

Rules support three targeting scopes:
- `ALL` — applies to every device in the project
- `TAG` — applies to devices carrying a specific tag
- `EXPLICIT` — applies only to manually assigned devices

### Alert Deduplication with Advisory Locks
Alert creation uses **PostgreSQL advisory locks** (`pg_advisory_xact_lock`) to prevent duplicate alerts when multiple Celery workers evaluate the same device concurrently. Combined with a per-rule **cooldown window**, this ensures clean, deduplicated alert streams.

### Webhook Delivery with Circuit Breaker
Webhook notifications are delivered asynchronously. A **Redis-backed circuit breaker** tracks failures per endpoint URL — after 5 consecutive failures the circuit opens, blocking further delivery attempts for a configurable recovery timeout before entering half-open state to test recovery.

### Multi-tenant Data Model
Resources are scoped to an `Org → Project → Device` hierarchy. API keys are issued per-project and gate both write (ingestion) and read (telemetry query) access.

---

## Getting Started

### Prerequisites
- Docker + Docker Compose

### Running locally

```bash
# 1. Copy the example env file and adjust if needed
cp .env.example .env

# 2. Start all services
docker compose up --build

# 3. Run database migrations
docker compose exec api alembic upgrade head

# 4. (Optional) Seed demo data
docker compose exec api python app/scripts/seed_demo.py
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

A webhook receiver tool is included for local testing at `http://localhost:9000`.

---

## API Overview

All endpoints require an `X-API-Key` header unless noted.

### Auth flow
```
POST /orgs                          → create org
POST /orgs/{org_id}/projects        → create project
POST /projects/{project_id}/api-keys → get raw API key (shown once)
```

### Telemetry
```
POST   /telemetry                                    → ingest batch (202)
GET    /telemetry/devices/{device_id}/telemetry      → list recent events
GET    /telemetry/devices/{device_id}/telemetry/latest
GET    /telemetry/devices/{device_id}/telemetry/since?since_ts=<unix>
```

### Devices & Rules
```
POST   /projects/{project_id}/devices
GET    /projects/{project_id}/devices
POST   /projects/{project_id}/rules
GET    /projects/{project_id}/rules
PATCH  /rules/{rule_id}
POST   /rules/{rule_id}/devices     → assign devices for EXPLICIT scope
```

### Alerts & Webhooks
```
GET    /projects/{project_id}/alerts
GET    /devices/{device_id}/alerts
POST   /projects/{project_id}/webhooks
GET    /webhooks/{webhook_id}/circuit-status
POST   /webhooks/{webhook_id}/disable
GET    /projects/{project_id}/webhook-deliveries
```

---

## Example: Ingest and alert

```bash
# 1. Create org/project/device/api-key (see /docs for full flow)

# 2. Create a rule: alert if temperature > 80 in 5 of last 5 events
curl -X POST http://localhost:8000/projects/1/rules \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"High Temp","metric":"temperature","operator":">","threshold":80,"window_n":5,"required_k":5,"cooldown_seconds":300,"scope":"ALL"}'

# 3. Push telemetry
curl -X POST http://localhost:8000/telemetry \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "device_external_id": "sensor-01",
    "events": [
      {"ts": "2025-01-01T12:00:00Z", "data": {"temperature": 95.0}},
      {"ts": "2025-01-01T12:00:01Z", "data": {"temperature": 96.0}},
      {"ts": "2025-01-01T12:00:02Z", "data": {"temperature": 97.0}},
      {"ts": "2025-01-01T12:00:03Z", "data": {"temperature": 98.0}},
      {"ts": "2025-01-01T12:00:04Z", "data": {"temperature": 99.0}}
    ]
  }'
# → 202 Accepted, alert fires asynchronously, webhook delivered
```

---

## Running Tests

Tests use **testcontainers** to spin up a real PostgreSQL instance automatically — no manual setup required.

```bash
pip install -e ".[dev]"
pytest
```

Test coverage: **~81%**, including API integration tests, service unit tests, and worker task tests.

```bash
pytest --cov=app --cov-report=html   # view report at htmlcov/index.html
```

---

## Project Structure

```
app/
├── api/
│   ├── deps.py          # FastAPI dependencies (DB session, API key auth)
│   ├── rate_limits.py   # slowapi rate limit tiers
│   └── routes/          # One file per resource
├── core/
│   └── security.py      # API key generation + bcrypt verification
├── db/
│   ├── migrations/      # Alembic migration history
│   ├── models/          # SQLAlchemy ORM models
│   └── repositories/    # All DB queries isolated here
├── schemas/             # Pydantic request/response models
├── services/            # Business logic (evaluation, circuit breaker, etc.)
├── workers/
│   └── tasks/           # Celery tasks (ingest, evaluate, deliver)
└── tests/
    ├── test_api/        # HTTP endpoint tests
    ├── test_services/   # Unit tests for services
    ├── test_workers/    # Unit tests for Celery tasks
    └── test_integration/ # End-to-end alert flow tests
```
