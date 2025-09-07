# API Documentation

*Last updated: September 7, 2025*

## Django Backend API

### Authentication Endpoints
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - User login with JWT token
- `POST /api/auth/refresh/` - Refresh JWT access token
- `POST /api/auth/logout/` - Logout and blacklist token

### User Management
- `GET /api/users/` - List all users
- `POST /api/users/` - Create new user
- `GET /api/users/{id}/` - Get user details
- `PUT /api/users/{id}/` - Update user
- `DELETE /api/users/{id}/` - Delete user

### Team Management
- `GET /api/teams/` - List all teams
- `POST /api/teams/` - Create new team
- `GET /api/teams/{id}/` - Get team details
- `PUT /api/teams/{id}/` - Update team
- `DELETE /api/teams/{id}/` - Delete team

### Task Management
- `GET /api/tasks/` - List all tasks
- `POST /api/tasks/` - Create new task
- `GET /api/tasks/{id}/` - Get task details
- `PUT /api/tasks/{id}/` - Update task
- `DELETE /api/tasks/{id}/` - Delete task

### Tags
- `GET /api/tags/` - List all tags
- `POST /api/tags/` - Create new tag
- `GET /api/tags/{id}/` - Get tag details
- `PUT /api/tags/{id}/` - Update tag
- `DELETE /api/tags/{id}/` - Delete tag

### Task Templates
- `GET /api/task-templates/` - List task templates
- `POST /api/task-templates/` - Create task template
- `GET /api/task-templates/{id}/` - Get template details
- `PUT /api/task-templates/{id}/` - Update template
- `DELETE /api/task-templates/{id}/` - Delete template

### JWT Public Keys
- `GET /.well-known/jwks.json` - JWKS endpoint for JWT verification
- `GET /api/auth/public-key/` - Get JWT public key

## Flask Analytics API

### Health & Debug
- `GET /api/v1/analytics/healthz` - Health check endpoint
- `GET /api/v1/analytics/test` - Test endpoint
- `GET /api/v1/analytics/debug` - Debug info (requires JWT)

### Analytics Dashboard
- `GET /api/v1/analytics/dashboard` - Main dashboard metrics (total tasks, done tasks, hours, priority distribution, last 30 days activity)

### Task Analytics
- `GET /api/v1/analytics/tasks/distribution` - Task distribution by status and top tags

### User Analytics
- `GET /api/v1/analytics/user/{user_id}/stats` - User statistics (created tasks, assigned tasks, comments, hours done, velocity chart data)

### Team Analytics
- `GET /api/v1/analytics/team/{team_id}/performance` - Team performance metrics (total tasks, done tasks, throughput, lead time)

### Reports
- `GET /api/v1/reports` - List all reports/jobs for the authenticated user
- `POST /api/v1/reports/generate` - Generate analytics report (async job, supports preflight OPTIONS)
- `GET /api/v1/reports/{job_id}` - Check report generation status
- `GET /api/v1/reports/{report_id}/download` - Download generated report