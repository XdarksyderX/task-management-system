# Task Management System

Task management system with Django, WebSockets, and RSA JWT authentication.

## Initial Setup

### 1. Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# --- Django ---
DJANGO_SECRET_KEY=changeme-super-secret
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=*

# --- Database ---
POSTGRES_DB=tasks
POSTGRES_USER=tasks_user
POSTGRES_PASSWORD=tasks_pass
POSTGRES_HOST=db
POSTGRES_PORT=5432


# --- Redis ---
REDIS_HOST=redis
REDIS_PORT=6379

# --- Django Admin
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin123

# --- Celery ---
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# JWT Configuration
JWT_ISSUER=http://web:8000/
JWT_JWKS_URL=http://web:8000/.well-known/jwks.json

# Analytics
ANALYTICS_REDIS_URL=redis://redis:6379/2
ANALYTICS_DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

#Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_ENABLED=1
```

### 2. Generate RSA Keys for JWT

**IMPORTANT**: Before running Docker Compose, you must generate the RSA keys for JWT authentication:

```bash
# From the project root
cd django_backend
./scripts/keygen.sh
```

This command will create the files:
- `config/keys/jwt_private_key.pem` - Private key for signing tokens
- `config/keys/jwt_public_key.pem` - Public key for verifying tokens

**Note**: RSA keys are critical for security. Ensure:
- Do not upload them to the repository (they are in `.gitignore`)
- Generate new keys for each environment (development, production)
- Keep the private key secure

### 3. Run the System

```bash
# Build and start all services
docker compose up --build

# Or in the background
docker compose up -d --build
```

## Seed Data

To populate the database with sample data, run the seed command:

```bash
# Run from the web container
docker compose exec web python manage.py seed

# Or using the script directly
docker compose exec web bash scripts/seed.sh
```

### Created Data

The seed script creates:
- **1 admin user**: `admin` / `admin123`
- **25 regular users**: with random names and password `password123`
- **12 teams**: one per department (Engineering, Product, Design, etc.)
- **17 tags**: frontend, backend, database, api, etc.
- **8 task templates**: Bug Fix, Feature Implementation, etc.
- **100 tasks**: with random states, priorities, and assignments
- **Comments**: on approximately 60% of tasks

### Sample Users

After running the seed, you'll see a list of sample users like:

```
Sample users created:
- alicesmith0 (password123)
- bobsmith1 (password123)
- charliesmith2 (password123)
- dianajohnson3 (password123)
- evewilliams4 (password123)
```

All regular users use the password `password123`.

### Customization

You can customize the amount of data generated:

```bash
# Create 50 users and 200 tasks
docker compose exec web python manage.py seed --users 50 --tasks 200
```

## Services

The system includes the following services:

- **web** (port 8000): Main Django server
- **worker**: Celery worker for background tasks
- **beat**: Celery scheduler for periodic tasks
- **db**: PostgreSQL database
- **redis**: Cache and message broker

## Important Endpoints

- `http://localhost:8000/` - Home page
- `http://localhost:8000/admin/` - Admin panel
- `http://localhost:8000/.well-known/jwks.json` - JWKS for JWT verification
- `http://localhost:8000/api/auth/login/` - Login API

## Development

### Run Tests

```bash
# Full tests
docker compose exec web python manage.py test

# Specific tests
docker compose exec web python manage.py test apps.tasks.tests
docker compose exec web python manage.py test apps.common.tests
```

### Logs

```bash
# View logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f web
docker compose logs -f websocket
```

### Regenerate RSA Keys

If you need to regenerate the keys (for example, for a new environment):

```bash
cd django_backend
rm -f config/keys/jwt_*.pem
./scripts/keygen.sh
```

Then restart the services:

```bash
docker compose restart
```
