# Task Management System

Sistema de gestión de tareas con Django, WebSockets y autenticación JWT con RSA.

## Configuración inicial

### 1. Variables de entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

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
```

### 2. Generar claves RSA para JWT

**IMPORTANTE**: Antes de ejecutar Docker Compose, debes generar las claves RSA para la autenticación JWT:

```bash
# Desde la raíz del proyecto
cd django_backend
./scripts/keygen.sh
```

Este comando creará los archivos:
- `config/keys/jwt_private_key.pem` - Clave privada para firmar tokens
- `config/keys/jwt_public_key.pem` - Clave pública para verificar tokens

**Nota**: Las claves RSA son críticas para la seguridad. Asegúrate de:
- No subirlas al repositorio (están en `.gitignore`)
- Generar nuevas claves para cada entorno (desarrollo, producción)
- Mantener la clave privada segura

### 3. Ejecutar el sistema

```bash
# Construir e iniciar todos los servicios
docker-compose up --build

# O en segundo plano
docker-compose up -d --build
```

## Servicios

El sistema incluye los siguientes servicios:

- **web** (puerto 8000): Servidor Django principal
- **websocket** (puerto 8002): Servidor WebSocket para tiempo real
- **worker**: Worker de Celery para tareas en segundo plano
- **beat**: Scheduler de Celery para tareas periódicas
- **db**: Base de datos PostgreSQL
- **redis**: Cache y broker de mensajes

## Endpoints importantes

- `http://localhost:8000/` - Página principal
- `http://localhost:8000/admin/` - Panel de administración
- `http://localhost:8000/.well-known/jwks.json` - JWKS para verificación JWT
- `http://localhost:8000/api/auth/login/` - Login API

## Desarrollo

### Ejecutar tests

```bash
# Tests completos
docker-compose exec web python manage.py test

# Tests específicos
docker-compose exec web python manage.py test apps.tasks.tests
docker-compose exec web python manage.py test apps.common.tests
```

### Logs

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f web
docker-compose logs -f websocket
```

### Regenerar claves RSA

Si necesitas regenerar las claves (por ejemplo, para un nuevo entorno):

```bash
cd django_backend
rm -f config/keys/jwt_*.pem
./scripts/keygen.sh
```

Luego reinicia los servicios:

```bash
docker-compose restart
```
