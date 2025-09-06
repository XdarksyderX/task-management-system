

# DECISIONS

## Part A — Core Backend & Execution Model

### A1) Project Layout & Ownership

```
/apps
  /users
    /api/            # DRF endpoints (views, serializers, urls)
    views.py         # SSR views (minimal)
    templates/users/
    producer/        # domain events (transport-agnostic)
  /tasks
    /api/
    views.py
    templates/tasks/
    producer/
  /common
    events/          # EventPublisher interface + factory
    kafka/           # shared Kafka config (when enabled)
```

**Decision:** Keep **API** isolated under `app/api/` and SSR under `app/views.py` + `app/templates/`.
**Why:** Clear boundaries per domain; easier testing; avoids tangling DRF and template concerns.
**Alternative:** Global `templates/` at project root → rejected (naming collisions and weak ownership).

---

### A2) Runtime Model — Single Image, Multi-Role Entrypoint

**Decision:** One container image, runtime selected via `ROLE` in a `case`-based entrypoint (`web`, `worker`, `beat`, `daphne`).
**Why:** One build artifact, faster CI, consistent dependencies; simpler operations.
**Alternative:** Separate images per role → rejected (duplication, drift risk).

---

### A3) Celery — Naming & Semantics

* **File name:** `celery_tasks.py` (not `tasks.py`) to avoid collisions with the business “tasks” domain.
* **Idempotent jobs:** retries are safe using guards, upserts, and unique keys.
* **Queue hygiene:** ability to separate long-running jobs from interactive ones.

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

**Alternative:** Keep HS256 → rejected (large compromise surface if one service leaks the key).

---

### A5) Data Access & Integrity

* **N+1 control:** `select_related()` / `prefetch_related()` on hot list/detail endpoints.
* **Soft delete:** `is_archived` flag with default manager filtering out archived rows.
* **Validation layering:** serializer validation (external ingress) plus model `clean()` (internal ORM paths).
* **API envelope:** consistent `data / error / meta` structure.
* **Logging:** structured logs with actor, action, entity, and id.

---

## Part B — Extensions & Integration

### B1) Analytics Microservice (Before Kafka)

#### Scope & Boundaries

**Decision:** Separate **Analytics** microservice with read-only DB access and its own cache/worker.
**Why:** Isolate heavy aggregate/report logic; enable independent scaling and deployment.

#### Auth & Trust

**Decision:** RS256 JWT allows Analytics to verify tokens via JWKS without sharing secrets.
**Why:** Zero secret distribution; safe onboarding of new services.

#### Data & Caching

* Read-only DB credentials; optional replica usage.
* Separate Redis DB/namespace to avoid contention.

#### Reporting Pipeline

* Async jobs for heavy reports; downloadable artifacts with expiry.
* Separate Celery queues for reports vs. interactive analytics.

---

### B2) Eventing & Messaging (After Analytics)

#### Transport-Agnostic Producers

**Decision:** Each domain app (`users`, `tasks`) has a `producer/` that calls a shared `EventPublisher` interface.
**Why:** Swap Kafka/RabbitMQ/Redis without changing business code; use memory backend in tests.
**Alternative:** Direct Kafka calls in app code → rejected (tight coupling, harder tests).

#### Topics & Ordering

* Topics per domain (`user-activities`, `task-events`, `analytics-events`, `system-notifications`).
* Partition key = entity ID to guarantee per-aggregate ordering.
* Stable, versioned payload schemas.

#### Rollout Plan

* Start with memory backend in tests, then enable Kafka in production.
* Add consumers gradually (notifications, analytics enrichment).

---

### B3) Frontend Organization

**Decision:** Keep templates inside each app (e.g., `users/templates/users/`, `tasks/templates/tasks/`).
**Why:** Strong domain ownership, fewer naming conflicts, easier refactors.
**Minimal JS** used only for UX wins (e.g., modal-based team creation).

---

### B4) Further Low-Level Discipline

* Index common query predicates (status, owner, dates).
* Use explicit DRF viewsets/actions for predictability.
* Uniform exception-to-envelope error mapping.
* Preserve audit trails through domain history and soft deletes.