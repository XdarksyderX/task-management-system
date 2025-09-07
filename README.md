# Task Management System

A full-stack, containerized task management platform built with **Django**, **PostgreSQL**, **Redis**, **Celery**, and **Docker**, including a basic server-rendered frontend and real-time features.

This project was developed as part of a technical assessment. It implements the **mandatory Part A requirements** and several **Part B features** such as Kafka event streaming, a Flask-based analytics microservice, and real-time task comments via WebSockets.

---

## 🚀 Features Implemented

### Core (Part A - Mandatory)
- **Dockerized infrastructure** with `docker-compose` for all services:
  - PostgreSQL 15+
  - Redis 7+ (cache + Celery broker)
  - Django application server
  - Celery worker
  - Celery beat (scheduled tasks)
  - Flower (Celery monitoring)
- **User authentication & management**:
  - JWT authentication (RS256 with JWKS endpoint)
  - Login / logout / refresh token
  - User profile & user list (paginated)
- **Task management**:
  - CRUD operations for tasks
  - Soft delete (archive/unarchive tasks)
  - Filtering by status & priority
  - Task assignment to multiple users
  - Tags system for tasks
  - Task history tracking (status changes, comments, overdue updates)
- **Comments system** (linked to tasks)
- **Celery background tasks**:
  - Email notifications on task events
  - Daily task summary per user
  - Automatic overdue task detection and status update
  - Weekly cleanup of archived tasks > 30 days
- **Server-side rendered frontend** with Django templates:
  - Login page
  - Task list page
  - Task creation form
  - Task detail view with comments
- **PostgreSQL optimizations**:
  - `JSONField` for flexible metadata
  - DB indexes on frequently queried fields
  - Unique constraints on relations
  - Model validations & signals

### Extended (Part B - Extra)
- **Kafka event streaming**:
  - Topics: `task-events`, `user-activities`, `system-notifications`, `analytics-events`
  - Event producers for task lifecycle & user activity
  - Event consumers for search indexing, notifications, and analytics
- **Flask analytics microservice**:
  - Basic endpoints for dashboard, user/team stats, and task distribution
  - Separate Docker container
  - Connected to PostgreSQL & Redis
- **Real-time comments** with Django Channels & WebSockets:
  - Live updates on new/edit/delete comments in the task detail page

---

## 🛠 Tech Stack

**Backend**
- **Django 5** with **Django REST Framework** for API development.
- **Django Channels** for WebSocket-based real-time features (task comments, live updates).

**Frontend**
- Server-Side Rendering (SSR) with Django Templates.
- Minimal **vanilla JavaScript** for dynamic interactions.

**Database & Storage**
- **PostgreSQL 15** as the primary relational database.
- **JSONField** usage for flexible metadata storage.

**Caching & Message Broker**
- **Redis 7** for caching, Celery message broker, and analytics queue storage.

**Asynchronous & Scheduled Tasks**
- **Celery** for background job processing.
- **Celery Beat** for periodic task scheduling.
- **Flower** for Celery monitoring and task tracking.

**Event Streaming & Processing**
- **Apache Kafka** with **Zookeeper** for event-driven architecture.
- Multiple Kafka consumers for:
  - Activity feed generation
  - Search indexing
  - Audit logging
  - Notifications
  - Analytics data aggregation

**Analytics Service**
- Separate **Flask** microservice for analytics and reporting.
- Integrated with Kafka, PostgreSQL, and Redis.

**Containerization & Orchestration**
- **Docker** multi-container setup with **Docker Compose**.
- Health checks and dependency management for all services.
- Volume persistence for database, Kafka, and other stateful services.

**Monitoring & Tooling**
- **Flower** (Celery task monitoring).
- **Kafka UI (Kafbat)** for Kafka cluster inspection.

---

## 📂 Project Structure

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

````

---

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/XdarksyderX/task-management-system
cd task-management-system
````

### 2. Environment variables

Copy the sample environment file and update values as needed:

```bash
cp .env.sample .env
```

**Required variables include**:

* PostgreSQL & Redis connection details
* Django secret key & debug mode
* JWT private/public keys for RS256
* Kafka broker URLs
* Email backend configuration

Generate RSA keys for JWT:

```bash
bash django_backend/scripts/keygen.sh
```

### 3. Start the services

```bash
docker compose up --build
```

On first run, this will:

* Build all images
* Apply database migrations

### 4. (Optional) Seed initial data

To populate the database with sample data (users, teams, tags, sample tasks), run:

```bash
docker compose exec web python manage.py seed
```

### 5. Access the application

* Django app: [http://localhost:8000](http://localhost:8000)
* Admin panel: [http://localhost:8000/admin/](http://localhost:8000/admin/)
* Flower (Celery monitoring): [http://localhost:5555](http://localhost:5555)
* Kafbat (Kafka UI for cluster inspection): [http://localhost:8080](http://localhost:8080)

---

## 📜 API Endpoints

See [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md) for a complete list.

Some key endpoints:

```
POST   /api/auth/login/
POST   /api/auth/logout/
GET    /api/users/me/
GET    /api/tasks/
POST   /api/tasks/
POST   /api/tasks/{id}/assign/
POST   /api/tasks/{id}/comments/
```

---

## 🧪 Running Tests

### Quick Test Commands

```bash
# Test individual apps (recommended)
docker compose exec web bash /app/scripts/test.sh apps.common.tests   # RSA JWT tests
docker compose exec web bash /app/scripts/test.sh apps.users.tests    # User & auth tests  
docker compose exec web bash /app/scripts/test.sh apps.tasks.tests    # Task management tests

# Test specific modules
docker compose exec web bash /app/scripts/test.sh apps.common.tests.test_rsa_jwt
```

### Alternative Commands

```bash
# Using Django's test command directly
docker compose exec web python manage.py test apps.common.tests --settings=config.test_settings
docker compose exec web python manage.py test apps.users.tests --settings=config.test_settings  
docker compose exec web python manage.py test apps.tasks.tests --settings=config.test_settings
```

**Note**: The test configuration uses SQLite in-memory database, HS256 JWT (instead of RSA), and memory-based event publishing for faster, isolated testing.

---

## 📚 Additional Documentation

* **[DECISIONS.md](./DECISIONS.md)** – Implemented features, trade-offs, technical choices.
* **[ARCHITECTURE.md](./ARCHITECTURE.md)** – System architecture and component interactions.
* **[API\_DOCUMENTATION.md](./API_DOCUMENTATION.md)** – API reference and example requests.
---

## 📄 License

This project is for demonstration purposes as part of a technical assessment.
