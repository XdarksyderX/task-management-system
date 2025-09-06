# Architecture

## 1) System Overview

The system is composed of:

* **Django monolith** for core business logic, handling both SSR and API endpoints.
* **Analytics microservice** (Flask) for heavy aggregations and reporting, operating in read-only mode to the main database.
* **Eventing layer** with a transport-agnostic publisher, supporting Kafka, Redis, RabbitMQ (future) or an in-memory backend for testing.
* **Daphne** for real-time comments via WebSockets.

Key traits:

* **SSR-first** for main flows, API used selectively for interactive actions.
* **JWT RS256** with JWKS for secure, modular authentication across services.
* **Single container image** with role-based startup (web, worker, beat, daphne).
* **Idempotent Celery jobs** and per-domain event producers.

---

## 2) Code & Directory Layout

```
/apps
	/users
		/api/                # DRF views + serializers
		views.py             # SSR views
		templates/users/
		producer/            # domain events
	/tasks
		/api/
		views.py
		templates/tasks/
		producer/
	/common
		events/              # EventPublisher interface + factory
		kafka/               # shared Kafka config

/config                  # Django settings, urls, WSGI/ASGI
/entrypoint.sh           # case/esac for role selection via parameter
```

**Conventions:**

* `celery_tasks.py` for background jobs (avoid clashing with “tasks” domain name).
* SSR and API separated in each app.
* Producers located inside each domain app.

---

## 3) Runtime & Processes

A single container image, with the role chosen by passing a parameter to `entrypoint.sh`:

* `entrypoint.sh web` → Gunicorn (Django WSGI)
* `entrypoint.sh worker` → Celery worker
* `entrypoint.sh beat` → Celery beat scheduler
* `entrypoint.sh daphne` → Daphne ASGI for real-time comment system

**Why:** Single build artifact, consistent dependencies, simpler deployment.

---

## 4) Authentication

* Migration from **HS256** to **RS256** JWT.
* Only the authentication side holds the private key.
* Other services verify tokens via **public key** served at `.well-known/jwks.json` and `/auth/keys/public`.
* Enables secure modular services without shared secret sprawl.

---

## 5) Background Jobs (Celery)

* Tasks placed in `celery_tasks.py` within each app.
* All tasks designed to be **idempotent**.
* Capability to separate queues for long-running vs interactive jobs.
* Beat schedules stored in DB (via django-celery-beat) for visibility.

---

## 6) Analytics Microservice

* Flask-based, read-only to main Postgres DB.
* Validates JWT via JWKS.
* Handles heavy aggregations, async report generation, and caching in a separate Redis namespace.
* Offloads heavy computation from Django request path.

---

## 7) Eventing Layer

* Domain producers call the `EventPublisher` interface, not Kafka directly.
* Backends selectable via `EVENT_PUBLISHER_TYPE`: kafka, redis, rabbitmq (future), memory (tests).
* Topics separated by domain: `user-activities`, `task-events`, `analytics-events`, `system-notifications`.
* Partition key = aggregate ID (`user_id` or `task_id`) for ordering.

---

## 8) Real-Time Comments

* Implemented via **Daphne** and Django ASGI for WebSocket support.
* Integrated with authentication via JWT RS256 verification.
* Dedicated role in deployment (`entrypoint.sh daphne`).

