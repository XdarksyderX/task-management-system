# DECISIONS

## Part A — Core Backend & Execution Model

### A1) Project Layout & Ownership

```
.
├── DECISIONS.md
├── docker-compose.yml
├── README.md
├── django_backend
│   ├── apps
│   │   ├── common
│   │   ├── tasks
│   │   └── users
│   ├── config
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── keys
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── Dockerfile
│   ├── manage.py
│   ├── requirements.txt
│   ├── scripts
│   │   ├── entrypoint.sh
│   │   ├── keygen.sh
│   │   ├── run_tests.sh
│   │   └── seed.sh
│   └── templates
│       ├── analytics
│       ├── dashboard.html
│       └── landing.html
├── docs
│   ├── API_DOCUMENTATION.md
│   ├── ARCHITECTURE.md
│   └── ASYNC.md
├── flask_analytics
│   ├── app.py
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── events
│   │   ├── analytics_events.py
│   │   ├── base.py
│   │   ├── kafka_publisher.py
│   │   ├── memory_publisher.py
│   │   └── redis_publisher.py
│   ├── init_db.py
│   ├── jwt_auth.py
│   ├── KAFKA_DEBUG_REPORT.md
│   ├── requirements.txt
│   ├── tasks.py
│   ├── test_events.py
│   ├── test_events_simple.py
│   ├── test_kafka_debug.py
│   └── tests.py
├── kafka
│   ├── consumers.py
│   ├── Dockerfile
│   └── requirements.txt

```

**Decision:** Keep **API** isolated under `app/api/` and SSR under `app/views.py` + `app/templates/`.  
**Why:** Clear boundaries per domain; easier testing; avoids tangling DRF and template concerns.  
**Alternative:** Global `templates/` at project root → rejected (naming collisions and weak ownership).

---

### A2) Runtime Model — Single Image, Multi-Role Entrypoint

**Decision:** One container image, runtime selected via `ROLE` in a `case`-based entrypoint (`web`, `worker`, `beat`, `asgi`).  
**Why:** One build artifact, faster CI, consistent dependencies; simpler operations.  
**Alternative:** Separate images per role → rejected (duplication, drift risk).

---

### A3) Celery — Naming & Semantics

* **File name:** `celery_tasks.py` (not `tasks.py`) to avoid collisions with the business “tasks” domain.
* **Idempotent jobs:** retries are safe using guards, upserts, and unique keys.
* **Queue hygiene:** ability to separate long-running jobs from interactive ones.
* **Monitoring:** Flower is included as a service for runtime inspection of queues and tasks.

---

### A4) Security & Identity — JWT from HS256 → RS256

**Decision:** Migrate signing from **HS256 (shared secret)** to **RS256 (asymmetric)**.  
**Why:**
* Only the auth service holds the private key; other services verify with the public key.
* No secret sprawl; better modularity for microservices.
* Easier key rotation with multiple `kid` values and JWKS.

**Operational details:**
* Added **`.well-known/jwks.json`** and **`/auth/keys/public`** for public key discovery.
* Tokens carry **`kid`** so verifiers select the right key.
* `keygen.sh` script automates RSA key generation into `config/keys/`.

**Alternative:** Keep HS256 → rejected (large compromise surface if one service leaks the key).

---

### A5) Data Access & Integrity

* **N+1 control:** `select_related()` / `prefetch_related()` on hot list/detail endpoints.
* **Soft delete:** `is_archived` flag with default manager filtering out archived rows.
* **Validation layering:** serializer validation (external ingress) plus model `clean()` (internal ORM paths).
* **API envelope:** consistent `data / error / meta` structure.
* **Logging:** structured logs with actor, action, entity, and id.
* **Indexing:** DB indexes on `status`, `priority`, `due_date`, and `created_by` for performance.

---

### A6) Frontend & Real-Time Features

**Decision:** Minimal SSR frontend with Django Templates and scoped CSS/HTML per domain app.  
**Why:** Quick to implement, avoids heavy SPA overhead for the scope of this assessment.  
**Real-time:** Implemented WebSocket-based live comments using Django Channels for task detail pages.  
**Alternative:** SPA with React/Vue → rejected (overhead and divergence from mandatory SSR requirement).

---

## Part B — Extensions & Integration

### B1) Analytics Microservice (Before Kafka)

**Scope & Boundaries**
* Separate **Flask** microservice with read-only DB access and its own Redis instance for analytics caching.
* Async job execution using RQ workers for report generation.

**Auth & Trust**
* RS256 JWT verification via JWKS for secure inter-service authentication.
* No shared secrets between Django backend and analytics microservice.

**Data & Caching**
* Read-only DB credentials; optional replica usage.
* Separate Redis DB/namespace to avoid contention.

**Reporting Pipeline**
* Async jobs for heavy reports; downloadable artifacts with expiry.
* Separate queues for reports vs interactive analytics queries.

---

### B2) Eventing & Messaging (After Analytics)

**Transport-Agnostic Producers**
* Each domain app (`users`, `tasks`) has a `producer/` that calls a shared `EventPublisher` interface.
* Swappable backend: in-memory for tests, Kafka in production.

**Topics & Ordering**
* Topics per domain (`user-activities`, `task-events`, `analytics-events`, `system-notifications`).
* Partition key = entity ID to guarantee per-aggregate ordering.
* Stable, versioned payload schemas.

**Consumers Implemented**
* **Activity Feed Generator** (user activities + task events).
* **Search Index Updater** (task events).
* **Audit Log Writer** (user activities + system notifications).
* **Notification Dispatcher** (task events + system notifications to Redis).
* **Analytics Aggregator** (analytics events + task events).

---

### B3) Frontend Organization

* Templates inside each app to ensure strong domain ownership.
* Minimal vanilla JS only for UX enhancements (e.g., inline comment creation, modals).
* WebSocket integration in task detail view for real-time updates.

---

### B4) Infrastructure & Ops

* **Health checks** for all services in `docker-compose.yml` to ensure proper startup order.
* **Volume persistence** for PostgreSQL, Kafka, Zookeeper, and Celery Beat data.
* **Kafka UI (Kafbat)** service for inspecting topics and partitions.
* Automated **database migrations** and **seed data** execution on startup.

---

### B5) Further Low-Level Discipline

* Index common query predicates (status, owner, dates).
* Use explicit DRF viewsets/actions for predictability.
* Uniform exception-to-envelope error mapping.
* Preserve audit trails through domain history and soft deletes.
* Isolate test environments from development data.

---

## ✅ Features Implemented

- **Dockerized infrastructure** with health checks and startup ordering.
- **PostgreSQL 15** with Django ORM, relations, JSONField metadata, and indexes.
- **Redis 7** for caching and Celery broker.
- **JWT RS256 authentication** with JWKS endpoint and automated key generation script.
- **User management API** (login, logout, refresh, profile, user list).
- **Task management API** (CRUD, assign, archive, history, comments, tags).
- **Soft delete** for tasks with archival flag.
- **Task history tracking** for status changes and overdue updates.
- **Celery background tasks**:
  - Task event notifications via email.
  - Daily summaries per user.
  - Overdue task detection.
  - Archived task cleanup.
- **Django Templates frontend** for authentication, task list, creation, and detail.
- **Real-time comments** using Django Channels & WebSockets.
- **Kafka event streaming** with multiple consumers for search, audit, notifications, and analytics.
- **Flask analytics microservice** with RQ workers and async report generation.
- **Monitoring tools**: Flower for Celery, Kafka UI for Kafka topics.
```
