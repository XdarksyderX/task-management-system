import os
import json
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort, g
from flask_cors import CORS
from sqlalchemy import select, func, text, Date, cast
from redis import Redis
from rq import Queue
from init_db import init_db
from jwt_auth import jwt_required

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env in parent directory (project root)
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[INFO] Loaded environment from {env_path}")
    else:
        print(f"[WARNING] .env file not found at {env_path}")
except ImportError:
    print("[WARNING] python-dotenv not installed, using system environment variables")

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Helper function to convert RowMapping objects to serializable dicts
    def serialize_row_mappings(row_mappings):
        """Convert SQLAlchemy RowMapping objects to JSON-serializable dictionaries"""
        if not row_mappings:
            return []
        return [dict(row) for row in row_mappings]
    
    # Configure CORS
    CORS(app, 
         origins=[
             "http://localhost:8000",  # Django development server
             "http://127.0.0.1:8000",  # Alternative localhost
             "http://web:8000",        # Docker container name
             "http://tms_web:8000",    # Docker compose service name
             "http://localhost:3000",  # React dev server
             "http://127.0.0.1:3000",  # Alternative React dev server
         ], 
         supports_credentials=True, 
         allow_headers=['Content-Type', 'Authorization', 'Accept', 'Origin', 'X-Requested-With'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         expose_headers=['Authorization', 'Content-Type'],
         max_age=86400)

    db_url = os.environ["ANALYTICS_DATABASE_URL"]
    redis_url = os.getenv("ANALYTICS_REDIS_URL", "redis://redis:6379/0")
    reports_dir = os.getenv("REPORTS_DIR", "/reports")

    DB = init_db(db_url)
    Session = DB["Session"]
    Task = DB["Task"]
    Tag = DB["Tag"]
    TaskTag = DB["TaskTag"]
    TaskAssignment = DB["TaskAssignment"]
    Comment = DB["Comment"]
    User = DB["User"]
    Team = DB["Team"]
    TeamMembers = DB.get("users_team_members") or DB.get("TeamMembers")

    r = Redis.from_url(redis_url)
    q = Queue("reports", connection=r, default_timeout=600)

    @app.before_request
    def log_request_info():
        try:
            logger.info('Request: %s %s - Remote Address: %s - User Agent: %s', 
                       request.method, request.url, request.remote_addr, request.headers.get('User-Agent'))
            logger.info('Request Headers: %s', dict(request.headers))
            logger.info('Request Path: %s, Args: %s', request.path, request.args)
            if request.is_json and request.get_json():
                logger.info('Request Body: %s', request.get_json())
            elif request.data:
                logger.info('Request Data: %s', request.data.decode('utf-8', errors='replace'))
        except Exception as e:
            logger.error(f"Error logging request info: {str(e)}", exc_info=True)

    @app.after_request
    def log_response_info(response):
        logger.info('Response: %s %s - Status: %s', 
                   request.method, request.url, response.status_code)
        return response

    @app.before_request
    def normalize_path():
        if request.path != '/' and request.path.endswith('/'):
            from flask import redirect
            return redirect(request.path.rstrip('/'), code=301)

    # Custom error handlers
    @app.errorhandler(400)
    def bad_request(error):
        logger.error('400 Error: %s %s - Remote Address: %s - Headers: %s - Data: %s', 
                    request.method, request.url, request.remote_addr, 
                    dict(request.headers), request.data.decode('utf-8', errors='replace') if request.data else 'No data')
        return jsonify({
            "error": "BadRequest",
            "message": "Bad Request - The request could not be understood by the server",
            "status_code": 400,
            "hint": "Check your request format, headers, and authentication token"
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning('401 Error: %s %s - Remote Address: %s', 
                      request.method, request.url, request.remote_addr)
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication is required to access this resource. Please provide a valid JWT token.",
            "status_code": 401,
            "hint": "Include 'Authorization: Bearer <token>' header in your request"
        }), 401

    @app.errorhandler(404)
    def not_found(error):
        logger.warning('404 Error: %s %s - Remote Address: %s', 
                      request.method, request.url, request.remote_addr)
        return jsonify({
            "error": "Not Found",
            "message": f"The requested endpoint '{request.path}' was not found on this analytics server.",
            "status_code": 404,
            "available_endpoints": [
                "/api/v1/analytics/healthz",
                "/api/v1/analytics/dashboard", 
                "/api/v1/analytics/tasks/distribution",
                "/api/v1/analytics/user/<user_id>/stats",
                "/api/v1/analytics/team/<team_id>/performance",
                "/api/v1/reports/generate",
                "/api/v1/reports/<job_id>",
                "/api/v1/reports/<report_id>/download"
            ]
        }), 404

    @app.errorhandler(Exception)
    def handle_error(error):
        status_code = getattr(error, 'code', 500)
        error_name = error.__class__.__name__
        
        # Don't intercept HTTPExceptions unless they're server errors
        if hasattr(error, 'code') and error.code < 500:
            # Let Flask handle client errors normally
            status_code = error.code
        
        # Log the full error details
        logger.error('%s Error (%s): %s %s - Remote Address: %s - Error: %s - Request Headers: %s', 
                    status_code, error_name, request.method, request.url, 
                    request.remote_addr, str(error), dict(request.headers))

        error_messages = {
            400: "Bad Request - The request could not be understood by the server",
            403: "Forbidden - You don't have permission to access this resource", 
            405: "Method Not Allowed - The HTTP method is not supported for this endpoint",
            422: "Unprocessable Entity - The request data is invalid",
            500: "Internal Server Error - Something went wrong on our end"
        }
        
        # For debugging, include more information in non-production
        debug_info = {
            "error": error_name if status_code < 500 else "Internal Server Error",
            "message": error_messages.get(status_code, str(error)),
            "status_code": status_code,
            "timestamp": logger.handlers[0].format(logger.makeRecord(
                logger.name, logging.INFO, "", 0, "", (), None
            )).split(' - ')[0] if logger.handlers else None
        }
        
        # Add debug information for development
        if os.getenv("FLASK_ENV") == "development" or os.getenv("DEBUG") == "true":
            debug_info["debug"] = {
                "error_type": error_name,
                "original_error": str(error),
                "request_method": request.method,
                "request_path": request.path
            }
        
        return jsonify(debug_info), status_code

    @app.get("/api/v1/analytics/healthz")
    def healthz():
        return jsonify({"ok": True})

    @app.get("/api/v1/analytics/test")
    def test():
        return jsonify({
            "message": "Test endpoint working",
            "method": request.method,
            "path": request.path,
            "headers": dict(request.headers)
        })

    @app.get("/api/v1/analytics/debug")
    @jwt_required
    def debug():
        return jsonify({
            "user_id": g.user_id,
            "is_staff": g.is_staff,
            "scopes": g.scopes,
            "method": request.method,
            "path": request.path,
            "headers": dict(request.headers)
        })

    @app.get("/api/v1/analytics/dashboard")
    @jwt_required
    def dashboard():
        try:
            logger.info(f"Dashboard request for user_id: {g.user_id}, is_staff: {g.is_staff}")
            
            with Session() as s:
                total = s.scalar(select(func.count()).select_from(Task).where(Task.is_archived == False))
                done = s.scalar(select(func.count()).select_from(Task).where(Task.is_archived == False, Task.status == "done"))
                in_prog = s.scalar(select(func.count()).select_from(Task).where(Task.is_archived == False, Task.status == "in_progress"))
                blocked = s.scalar(select(func.count()).select_from(Task).where(Task.is_archived == False, Task.status == "blocked"))
                hours_done = s.scalar(select(func.coalesce(func.sum(Task.actual_hours), 0)).where(Task.is_archived == False, Task.status == "done"))

                by_priority = s.execute(
                    select(Task.priority, func.count().label("c"))
                    .where(Task.is_archived == False)
                    .group_by(Task.priority).order_by(Task.priority)
                ).mappings().all()

                last30_done = s.execute(
                    select(cast(func.date_trunc("day", Task.updated_at), Date).label("day"),
                           func.count().label("c"))
                    .where(Task.status == "done", Task.updated_at >= func.now() - text("interval '30 days'"))
                    .group_by(text("day")).order_by(text("day"))
                ).mappings().all()

            logger.info(f"Dashboard query successful - total: {total}, done: {done}")
            
            result = {
                "summary": {
                    "total_tasks": total,
                    "done_tasks": done,
                    "in_progress_tasks": in_prog,
                    "blocked_tasks": blocked,
                    "total_hours_done": float(hours_done or 0),
                },
                "by_priority": serialize_row_mappings(by_priority),
                "last30_done": serialize_row_mappings(last30_done)
            }
            
            logger.info("Dashboard response prepared successfully")
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Dashboard error: {type(e).__name__}: {str(e)}", exc_info=True)
            raise

    @app.get("/api/v1/analytics/tasks/distribution")
    @jwt_required
    def tasks_distribution():
        with Session() as s:
            by_status = s.execute(
                select(Task.status, func.count().label("c"))
                .where(Task.is_archived == False)
                .group_by(Task.status).order_by(Task.status)
            ).mappings().all()

            top_tags = s.execute(
                select(Tag.name.label("tag"), func.count().label("c"))
                .select_from(TaskTag)
                .join(Tag, Tag.id == TaskTag.tag_id)
                .join(Task, Task.id == TaskTag.task_id)
                .where(Task.is_archived == False)
                .group_by(Tag.name).order_by(text("c DESC")).limit(20)
            ).mappings().all()

        return jsonify({"by_status": serialize_row_mappings(by_status), "top_tags": serialize_row_mappings(top_tags)})

    @app.get("/api/v1/analytics/user/<int:user_id>/stats")
    @jwt_required
    def user_stats(user_id: int):
        with Session() as s:
            created = s.scalar(select(func.count()).select_from(Task).where(Task.created_by_id == user_id))
            assigned = s.scalar(select(func.count()).select_from(TaskAssignment).where(TaskAssignment.user_id == user_id))
            comments = s.scalar(select(func.count()).select_from(Comment).where(Comment.author_id == user_id))
            hours_done = s.scalar(
                select(func.coalesce(func.sum(Task.actual_hours), 0))
                .select_from(Task)
                .join(TaskAssignment, TaskAssignment.task_id == Task.id)
                .where(TaskAssignment.user_id == user_id, Task.status == "done")
            )
            velocity = s.execute(
                select(cast(func.date_trunc("week", Task.updated_at), Date).label("week"),
                       func.count().label("done"))
                .join(TaskAssignment, TaskAssignment.task_id == Task.id)
                .where(TaskAssignment.user_id == user_id, Task.status == "done")
                .group_by(text("week")).order_by(text("week DESC")).limit(12)
            ).mappings().all()

        return jsonify({
            "user_id": user_id,
            "summary": {
                "created": created,
                "assigned": assigned,
                "comments": comments,
                "hours_done": float(hours_done or 0),
            },
            "velocity": serialize_row_mappings(velocity)
        })

    @app.get("/api/v1/analytics/team/<int:team_id>/performance")
    @jwt_required
    def team_performance(team_id: int):
        with Session() as s:
            if not g.is_staff:
                if TeamMembers is not None:
                    is_member = s.scalar(
                        select(func.count())
                        .select_from(TeamMembers)
                        .where(TeamMembers.team_id == team_id, TeamMembers.user_id == g.user_id)
                    )
                else:
                    is_member = s.scalar(
                        select(func.count())
                        .select_from(Team)
                        .join(User, text("1=1"))
                        .where(text("users_team.id = :tid AND users_user.id = :uid"))
                        .params(tid=team_id, uid=g.user_id)
                    )
                if not is_member:
                    abort(403)

            total = s.scalar(select(func.count()).select_from(Task).where(Task.assigned_team_id == team_id, Task.is_archived == False))
            done = s.scalar(select(func.count()).select_from(Task).where(Task.assigned_team_id == team_id, Task.status == "done", Task.is_archived == False))
            blocked = s.scalar(select(func.count()).select_from(Task).where(Task.assigned_team_id == team_id, Task.status == "blocked", Task.is_archived == False))
            throughput = s.execute(
                select(cast(func.date_trunc("week", Task.updated_at), Date).label("week"),
                       func.count().label("done"))
                .where(Task.assigned_team_id == team_id, Task.status == "done")
                .group_by(text("week")).order_by(text("week DESC")).limit(12)
            ).mappings().all()
            leadtime = s.scalar(
                select(func.coalesce(func.avg((Task.updated_at - Task.created_at)), 0))
                .where(Task.assigned_team_id == team_id, Task.status == "done")
            )

        return jsonify({
            "team_id": team_id,
            "metrics": {"total": total, "done": done, "blocked": blocked},
            "throughput": serialize_row_mappings(throughput),
            "lead_time_hours_avg": (leadtime.total_seconds() / 3600.0) if leadtime else 0.0
        })

    # -------- Reports (RQ) --------
    @app.post("/api/v1/reports/generate")
    @jwt_required
    def reports_generate():
        data = request.get_json(silent=True) or {}
        job = q.enqueue("tasks.report_job", json.dumps(data), db_url, reports_dir, job_timeout=600)
        return jsonify({"job_id": job.id}), 202

    @app.get("/api/v1/reports/<job_id>")
    @jwt_required
    def reports_status(job_id):
        job = q.fetch_job(job_id)
        if not job:
            abort(404)
        return jsonify({"job_id": job_id, "status": job.get_status(), "result": job.result if job.result else None})

    @app.get("/api/v1/reports/<report_id>/download")
    @jwt_required
    def reports_download(report_id):
        path = os.path.join(reports_dir, f"{report_id}.csv")
        if not os.path.exists(path):
            abort(404)
        return send_file(path, mimetype="text/csv", as_attachment=True, download_name=f"report_{report_id}.csv")

    return app
