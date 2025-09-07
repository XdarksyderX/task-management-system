import os
import json
import logging
import uuid
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort, g
from flask_cors import CORS
from sqlalchemy import select, func, text, Date, cast
from redis import Redis
from rq import Queue
from init_db import init_db
from jwt_auth import jwt_required
from events import analytics_events


def create_app():
    app = Flask(__name__)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    def serialize_row_mappings(row_mappings):
        """Convert SQLAlchemy RowMapping objects to JSON-serializable dictionaries"""
        if not row_mappings:
            return []
        return [dict(row) for row in row_mappings]

    CORS(
        app,
        origins=[
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://web:8000",
            "http://tms_web:8000",
        ],
        supports_credentials=True,
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        expose_headers=["Authorization", "Content-Type"],
        max_age=86400,
    )

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
            logger.info(
                "Request: %s %s - Remote Address: %s - User Agent: %s",
                request.method,
                request.url,
                request.remote_addr,
                request.headers.get("User-Agent"),
            )
            logger.info("Request Headers: %s", dict(request.headers))
            logger.info("Request Path: %s, Args: %s", request.path, request.args)

            if request.is_json:
                try:
                    json_data = request.get_json(silent=True)
                    if json_data:
                        logger.info("Request Body: %s", json_data)
                except Exception as json_error:
                    logger.warning("Failed to parse JSON body: %s", str(json_error))
            elif request.data:
                logger.info(
                    "Request Data: %s", request.data.decode("utf-8", errors="replace")
                )
        except Exception as e:
            logger.error(f"Error logging request info: {str (e )}", exc_info=True)

    @app.after_request
    def log_response_info(response):
        logger.info(
            "Response: %s %s - Status: %s",
            request.method,
            request.url,
            response.status_code,
        )
        return response

    @app.before_request
    def normalize_path():
        if request.path != "/" and request.path.endswith("/"):
            from flask import redirect

            return redirect(request.path.rstrip("/"), code=301)

    @app.errorhandler(400)
    def bad_request(error):
        logger.error(
            "400 Error: %s %s - Remote Address: %s - Headers: %s - Data: %s",
            request.method,
            request.url,
            request.remote_addr,
            dict(request.headers),
            (
                request.data.decode("utf-8", errors="replace")
                if request.data
                else "No data"
            ),
        )
        return (
            jsonify(
                {
                    "error": "BadRequest",
                    "message": "Bad Request - The request could not be understood by the server",
                    "status_code": 400,
                    "hint": "Check your request format, headers, and authentication token",
                }
            ),
            400,
        )

    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(
            "401 Error: %s %s - Remote Address: %s",
            request.method,
            request.url,
            request.remote_addr,
        )
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "message": "Authentication is required to access this resource. Please provide a valid JWT token.",
                    "status_code": 401,
                    "hint": "Include 'Authorization: Bearer <token>' header in your request",
                }
            ),
            401,
        )

    @app.errorhandler(404)
    def not_found(error):
        logger.warning(
            "404 Error: %s %s - Remote Address: %s",
            request.method,
            request.url,
            request.remote_addr,
        )
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": f"The requested endpoint '{request .path }' was not found on this analytics server.",
                    "status_code": 404,
                    "available_endpoints": [
                        "/api/v1/analytics/healthz",
                        "/api/v1/analytics/dashboard",
                        "/api/v1/analytics/tasks/distribution",
                        "/api/v1/analytics/user/<user_id>/stats",
                        "/api/v1/analytics/team/<team_id>/performance",
                        "/api/v1/reports",
                        "/api/v1/reports/generate",
                        "/api/v1/reports/<job_id>",
                        "/api/v1/reports/<report_id>/download",
                    ],
                }
            ),
            404,
        )

    @app.errorhandler(Exception)
    def handle_error(error):
        status_code = getattr(error, "code", 500)
        error_name = error.__class__.__name__

        if hasattr(error, "code") and int(error.code) < 500:

            status_code = int(error.code)

        logger.error(
            "%s Error (%s): %s %s - Remote Address: %s - Error: %s - Request Headers: %s",
            status_code,
            error_name,
            request.method,
            request.url,
            request.remote_addr,
            str(error),
            dict(request.headers),
        )

        error_messages = {
            400: "Bad Request - The request could not be understood by the server",
            403: "Forbidden - You don't have permission to access this resource",
            405: "Method Not Allowed - The HTTP method is not supported for this endpoint",
            422: "Unprocessable Entity - The request data is invalid",
            500: "Internal Server Error - Something went wrong on our end",
        }

        debug_info = {
            "error": error_name if status_code < 500 else "Internal Server Error",
            "message": error_messages.get(status_code, str(error)),
            "status_code": status_code,
            "timestamp": (
                logger.handlers[0]
                .format(
                    logger.makeRecord(logger.name, logging.INFO, "", 0, "", (), None)
                )
                .split(" - ")[0]
                if logger.handlers
                else None
            ),
        }

        if os.getenv("FLASK_ENV") == "development" or os.getenv("DEBUG") == "true":
            debug_info["debug"] = {
                "error_type": error_name,
                "original_error": str(error),
                "request_method": request.method,
                "request_path": request.path,
            }

        return jsonify(debug_info), status_code

    @app.get("/api/v1/analytics/healthz")
    def healthz():
        return jsonify({"ok": True})

    @app.get("/api/v1/analytics/test")
    def test():
        return jsonify(
            {
                "message": "Test endpoint working",
                "method": request.method,
                "path": request.path,
                "headers": dict(request.headers),
            }
        )

    @app.get("/api/v1/analytics/debug")
    @jwt_required
    def debug():
        return jsonify(
            {
                "user_id": g.user_id,
                "is_staff": g.is_staff,
                "scopes": g.scopes,
                "method": request.method,
                "path": request.path,
                "headers": dict(request.headers),
            }
        )

    @app.get("/api/v1/analytics/dashboard")
    @jwt_required
    def dashboard():
        start_time = time.time()
        try:
            logger.info(
                f"Dashboard request for user_id: {g .user_id }, is_staff: {g .is_staff }"
            )

            analytics_events.publish_dashboard_viewed(
                user_id=g.user_id,
                metadata={
                    "is_staff": g.is_staff,
                    "user_agent": request.headers.get("User-Agent"),
                    "ip_address": request.remote_addr,
                },
            )

            with Session() as s:
                total = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(Task.is_archived == False)
                )
                done = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(Task.is_archived == False, Task.status == "done")
                )
                in_prog = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(Task.is_archived == False, Task.status == "in_progress")
                )
                blocked = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(Task.is_archived == False, Task.status == "blocked")
                )
                hours_done = s.scalar(
                    select(func.coalesce(func.sum(Task.actual_hours), 0)).where(
                        Task.is_archived == False, Task.status == "done"
                    )
                )

                by_priority = (
                    s.execute(
                        select(Task.priority, func.count().label("c"))
                        .where(Task.is_archived == False)
                        .group_by(Task.priority)
                        .order_by(Task.priority)
                    )
                    .mappings()
                    .all()
                )

                last30_done = (
                    s.execute(
                        select(
                            cast(func.date_trunc("day", Task.updated_at), Date).label(
                                "day"
                            ),
                            func.count().label("c"),
                        )
                        .where(
                            Task.status == "done",
                            Task.updated_at >= func.now() - text("interval '30 days'"),
                        )
                        .group_by(text("day"))
                        .order_by(text("day"))
                    )
                    .mappings()
                    .all()
                )

            logger.info(f"Dashboard query successful - total: {total }, done: {done }")

            result = {
                "summary": {
                    "total_tasks": total,
                    "done_tasks": done,
                    "in_progress_tasks": in_prog,
                    "blocked_tasks": blocked,
                    "total_hours_done": float(hours_done or 0),
                },
                "by_priority": serialize_row_mappings(by_priority),
                "last30_done": serialize_row_mappings(last30_done),
            }

            execution_time = (time.time() - start_time) * 1000
            analytics_events.publish_analytics_query(
                user_id=g.user_id,
                endpoint="/api/v1/analytics/dashboard",
                query_type="dashboard_summary",
                execution_time_ms=execution_time,
                metadata={"total_tasks": total, "query_complexity": "medium"},
            )

            logger.info("Dashboard response prepared successfully")
            return jsonify(result)

        except Exception as e:

            analytics_events.publish_error_occurred(
                user_id=g.user_id,
                error_type=type(e).__name__,
                endpoint="/api/v1/analytics/dashboard",
                error_message=str(e),
                metadata={
                    "is_staff": g.is_staff,
                    "execution_time_ms": (time.time() - start_time) * 1000,
                },
            )
            logger.error(
                f"Dashboard error: {type (e ).__name__ }: {str (e )}", exc_info=True
            )
            raise

    @app.get("/api/v1/analytics/tasks/distribution")
    @jwt_required
    def tasks_distribution():
        start_time = time.time()
        try:

            analytics_events.publish_task_distribution_viewed(
                user_id=g.user_id,
                metadata={
                    "is_staff": g.is_staff,
                    "user_agent": request.headers.get("User-Agent"),
                    "ip_address": request.remote_addr,
                },
            )

            with Session() as s:
                by_status = (
                    s.execute(
                        select(Task.status, func.count().label("c"))
                        .where(Task.is_archived == False)
                        .group_by(Task.status)
                        .order_by(Task.status)
                    )
                    .mappings()
                    .all()
                )

                top_tags = (
                    s.execute(
                        select(Tag.name.label("tag"), func.count().label("c"))
                        .select_from(TaskTag)
                        .join(Tag, Tag.id == TaskTag.tag_id)
                        .join(Task, Task.id == TaskTag.task_id)
                        .where(Task.is_archived == False)
                        .group_by(Tag.name)
                        .order_by(text("c DESC"))
                        .limit(20)
                    )
                    .mappings()
                    .all()
                )

            result = {
                "by_status": serialize_row_mappings(by_status),
                "top_tags": serialize_row_mappings(top_tags),
            }

            execution_time = (time.time() - start_time) * 1000
            analytics_events.publish_analytics_query(
                user_id=g.user_id,
                endpoint="/api/v1/analytics/tasks/distribution",
                query_type="task_distribution",
                execution_time_ms=execution_time,
                metadata={"status_count": len(by_status), "tags_count": len(top_tags)},
            )

            return jsonify(result)

        except Exception as e:
            analytics_events.publish_error_occurred(
                user_id=g.user_id,
                error_type=type(e).__name__,
                endpoint="/api/v1/analytics/tasks/distribution",
                error_message=str(e),
                metadata={"execution_time_ms": (time.time() - start_time) * 1000},
            )
            logger.error(
                f"Tasks distribution error: {type (e ).__name__ }: {str (e )}",
                exc_info=True,
            )
            raise

    @app.get("/api/v1/analytics/user/<int:user_id>/stats")
    @jwt_required
    def user_stats(user_id: int):
        start_time = time.time()
        try:

            analytics_events.publish_user_stats_accessed(
                requesting_user_id=g.user_id,
                target_user_id=user_id,
                metadata={
                    "is_staff": g.is_staff,
                    "is_self": g.user_id == user_id,
                    "user_agent": request.headers.get("User-Agent"),
                    "ip_address": request.remote_addr,
                },
            )

            with Session() as s:
                created = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(Task.created_by_id == user_id)
                )
                assigned = s.scalar(
                    select(func.count())
                    .select_from(TaskAssignment)
                    .where(TaskAssignment.user_id == user_id)
                )
                comments = s.scalar(
                    select(func.count())
                    .select_from(Comment)
                    .where(Comment.author_id == user_id)
                )
                hours_done = s.scalar(
                    select(func.coalesce(func.sum(Task.actual_hours), 0))
                    .select_from(Task)
                    .join(TaskAssignment, TaskAssignment.task_id == Task.id)
                    .where(TaskAssignment.user_id == user_id, Task.status == "done")
                )
                velocity = (
                    s.execute(
                        select(
                            cast(func.date_trunc("week", Task.updated_at), Date).label(
                                "week"
                            ),
                            func.count().label("done"),
                        )
                        .join(TaskAssignment, TaskAssignment.task_id == Task.id)
                        .where(TaskAssignment.user_id == user_id, Task.status == "done")
                        .group_by(text("week"))
                        .order_by(text("week DESC"))
                        .limit(12)
                    )
                    .mappings()
                    .all()
                )

            result = {
                "user_id": user_id,
                "summary": {
                    "created": created,
                    "assigned": assigned,
                    "comments": comments,
                    "hours_done": float(hours_done or 0),
                },
                "velocity": serialize_row_mappings(velocity),
            }

            execution_time = (time.time() - start_time) * 1000
            analytics_events.publish_analytics_query(
                user_id=g.user_id,
                endpoint=f"/api/v1/analytics/user/{user_id }/stats",
                query_type="user_stats",
                execution_time_ms=execution_time,
                metadata={
                    "target_user_id": user_id,
                    "created_count": created,
                    "assigned_count": assigned,
                },
            )

            return jsonify(result)

        except Exception as e:
            analytics_events.publish_error_occurred(
                user_id=g.user_id,
                error_type=type(e).__name__,
                endpoint=f"/api/v1/analytics/user/{user_id }/stats",
                error_message=str(e),
                metadata={
                    "target_user_id": user_id,
                    "execution_time_ms": (time.time() - start_time) * 1000,
                },
            )
            logger.error(
                f"User stats error: {type (e ).__name__ }: {str (e )}", exc_info=True
            )
            raise

    @app.get("/api/v1/analytics/team/<int:team_id>/performance")
    @jwt_required
    def team_performance(team_id: int):
        start_time = time.time()
        try:

            analytics_events.publish_team_performance_accessed(
                user_id=g.user_id,
                team_id=team_id,
                metadata={
                    "is_staff": g.is_staff,
                    "user_agent": request.headers.get("User-Agent"),
                    "ip_address": request.remote_addr,
                },
            )

            with Session() as s:
                if not g.is_staff:
                    if TeamMembers is not None:
                        is_member = s.scalar(
                            select(func.count())
                            .select_from(TeamMembers)
                            .where(
                                TeamMembers.team_id == team_id,
                                TeamMembers.user_id == g.user_id,
                            )
                        )
                    else:
                        is_member = s.scalar(
                            select(func.count())
                            .select_from(Team)
                            .join(User, text("1=1"))
                            .where(
                                text("users_team.id = :tid AND users_user.id = :uid")
                            )
                            .params(tid=team_id, uid=g.user_id)
                        )
                    if not is_member:
                        abort(403)

                total = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(Task.assigned_team_id == team_id, Task.is_archived == False)
                )
                done = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(
                        Task.assigned_team_id == team_id,
                        Task.status == "done",
                        Task.is_archived == False,
                    )
                )
                blocked = s.scalar(
                    select(func.count())
                    .select_from(Task)
                    .where(
                        Task.assigned_team_id == team_id,
                        Task.status == "blocked",
                        Task.is_archived == False,
                    )
                )
                throughput = (
                    s.execute(
                        select(
                            cast(func.date_trunc("week", Task.updated_at), Date).label(
                                "week"
                            ),
                            func.count().label("done"),
                        )
                        .where(Task.assigned_team_id == team_id, Task.status == "done")
                        .group_by(text("week"))
                        .order_by(text("week DESC"))
                        .limit(12)
                    )
                    .mappings()
                    .all()
                )
                leadtime = s.scalar(
                    select(
                        func.avg(
                            func.extract("epoch", Task.updated_at - Task.created_at)
                        )
                    ).where(Task.assigned_team_id == team_id, Task.status == "done")
                )

            result = {
                "team_id": team_id,
                "metrics": {"total": total, "done": done, "blocked": blocked},
                "throughput": serialize_row_mappings(throughput),
                "lead_time_hours_avg": float(leadtime) / 3600.0 if leadtime else 0.0,
            }

            execution_time = (time.time() - start_time) * 1000
            analytics_events.publish_analytics_query(
                user_id=g.user_id,
                endpoint=f"/api/v1/analytics/team/{team_id }/performance",
                query_type="team_performance",
                execution_time_ms=execution_time,
                metadata={"team_id": team_id, "total_tasks": total, "done_tasks": done},
            )

            return jsonify(result)

        except Exception as e:
            analytics_events.publish_error_occurred(
                user_id=g.user_id,
                error_type=type(e).__name__,
                endpoint=f"/api/v1/analytics/team/{team_id }/performance",
                error_message=str(e),
                metadata={
                    "team_id": team_id,
                    "execution_time_ms": (time.time() - start_time) * 1000,
                },
            )
            logger.error(
                f"Team performance error: {type (e ).__name__ }: {str (e )}",
                exc_info=True,
            )
            raise

    @app.route("/api/v1/reports/generate", methods=["POST", "OPTIONS"])
    def reports_generate():

        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200

        if request.method == "POST":
            start_time = time.time()
            try:

                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return (
                        jsonify(
                            {
                                "error": "Unauthorized",
                                "message": "Authentication is required to access this resource. Please provide a valid JWT token.",
                                "status_code": 401,
                                "hint": "Include 'Authorization: Bearer <token>' header in your request",
                            }
                        ),
                        401,
                    )

                try:
                    token = auth_header.split(" ")[1]

                    from jwt_auth import _decode_rs256

                    claims = _decode_rs256(token)

                    g.user_id = claims.get("user_id") or claims.get("sub")
                    g.is_staff = bool(
                        claims.get("is_staff") or claims.get("staff", False)
                    )
                    g.scopes = claims.get("scope") or claims.get("scopes") or []

                    if not g.user_id:
                        raise Exception("No user_id in token")

                except Exception as e:
                    logger.error(f"JWT verification failed: {str (e )}")
                    return (
                        jsonify(
                            {
                                "error": "Unauthorized",
                                "message": "Invalid or expired JWT token.",
                                "status_code": 401,
                            }
                        ),
                        401,
                    )

                data = request.get_json(silent=True) or {}
                report_type = data.get("type", "unknown")

                data["user_id"] = g.user_id
                job_id = f"report_{g .user_id }_{uuid .uuid4 ()}"
                job = q.enqueue(
                    "tasks.report_job",
                    json.dumps(data),
                    db_url,
                    reports_dir,
                    job_timeout=600,
                    job_id=job_id,
                )

                analytics_events.publish_report_generated(
                    user_id=g.user_id,
                    report_type=report_type,
                    job_id=job.id,
                    metadata={
                        "is_staff": g.is_staff,
                        "request_data": data,
                        "user_agent": request.headers.get("User-Agent"),
                        "ip_address": request.remote_addr,
                        "generation_time_ms": (time.time() - start_time) * 1000,
                    },
                )

                return jsonify({"job_id": job.id}), 202

            except Exception as e:

                analytics_events.publish_error_occurred(
                    user_id=getattr(g, "user_id", None),
                    error_type=type(e).__name__,
                    endpoint="/api/v1/reports/generate",
                    error_message=str(e),
                    metadata={"execution_time_ms": (time.time() - start_time) * 1000},
                )
                logger.error(
                    f"Report generation error: {type (e ).__name__ }: {str (e )}",
                    exc_info=True,
                )
                raise

    @app.get("/api/v1/reports")
    @jwt_required
    def list_reports():
        """List all reports/jobs for the current user"""
        try:

            jobs = []
            user_prefix = f"report_{g .user_id }_"

            def process_job(job):
                """Process a single job and return job data if it belongs to current user"""
                try:

                    if not job.id.startswith(user_prefix):
                        return None

                    job_data = {
                        "job_id": job.id,
                        "status": job.get_status(),
                        "created_at": (
                            job.created_at.isoformat() if job.created_at else None
                        ),
                        "started_at": (
                            job.started_at.isoformat() if job.started_at else None
                        ),
                        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                        "result": job.result if job.result else None,
                        "exc_info": (
                            str(job.exc_info)
                            if hasattr(job, "exc_info") and job.exc_info
                            else None
                        ),
                    }
                    return job_data
                except Exception as job_error:
                    logger.warning(
                        f"Error processing job {job .id }: {str (job_error )}"
                    )
                    return None

            from rq.registry import (
                StartedJobRegistry,
                FinishedJobRegistry,
                FailedJobRegistry,
            )

            for job in q.jobs:
                job_data = process_job(job)
                if job_data:
                    jobs.append(job_data)

            started_registry = StartedJobRegistry(queue=q)
            for job_id in started_registry.get_job_ids():
                if job_id.startswith(user_prefix):
                    try:
                        job = q.fetch_job(job_id)
                        if job:
                            job_data = process_job(job)
                            if job_data and not any(
                                j["job_id"] == job.id for j in jobs
                            ):
                                jobs.append(job_data)
                    except Exception as job_error:
                        logger.warning(
                            f"Error processing started job {job_id }: {str (job_error )}"
                        )
                        continue

            finished_registry = FinishedJobRegistry(queue=q)
            for job_id in finished_registry.get_job_ids():
                if job_id.startswith(user_prefix):
                    try:
                        job = q.fetch_job(job_id)
                        if job:
                            job_data = process_job(job)
                            if job_data and not any(
                                j["job_id"] == job.id for j in jobs
                            ):
                                jobs.append(job_data)
                    except Exception as job_error:
                        logger.warning(
                            f"Error processing finished job {job_id }: {str (job_error )}"
                        )
                        continue

            failed_registry = FailedJobRegistry(queue=q)
            for job_id in failed_registry.get_job_ids():
                if job_id.startswith(user_prefix):
                    try:
                        job = q.fetch_job(job_id)
                        if job:
                            job_data = process_job(job)
                            if job_data and not any(
                                j["job_id"] == job.id for j in jobs
                            ):
                                jobs.append(job_data)
                    except Exception as job_error:
                        logger.warning(
                            f"Error processing failed job {job_id }: {str (job_error )}"
                        )
                        continue

            jobs.sort(key=lambda x: x["created_at"] or "", reverse=True)

            logger.info(f"Found {len (jobs )} jobs for user {g .user_id }")

            return jsonify({"jobs": jobs, "total": len(jobs)})

        except Exception as e:
            logger.error(f"Error listing reports: {str (e )}", exc_info=True)
            return jsonify({"error": "Error fetching reports", "message": str(e)}), 500

    @app.get("/api/v1/reports/<job_id>")
    @jwt_required
    def reports_status(job_id):

        user_prefix = f"report_{g .user_id }_"
        if not job_id.startswith(user_prefix):
            abort(403)

        job = q.fetch_job(job_id)
        if not job:
            abort(404)
        return jsonify(
            {
                "job_id": job_id,
                "status": job.get_status(),
                "result": job.result if job.result else None,
            }
        )

    @app.get("/api/v1/reports/<report_id>/download")
    @jwt_required
    def reports_download(report_id):
        start_time = time.time()
        try:

            path = os.path.join(reports_dir, f"{report_id }.csv")
            if not os.path.exists(path):
                abort(404)

            analytics_events.publish_report_downloaded(
                user_id=g.user_id,
                report_id=report_id,
                metadata={
                    "is_staff": g.is_staff,
                    "file_path": path,
                    "user_agent": request.headers.get("User-Agent"),
                    "ip_address": request.remote_addr,
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            )

            return send_file(
                path,
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"report_{report_id }.csv",
            )

        except Exception as e:
            analytics_events.publish_error_occurred(
                user_id=g.user_id,
                error_type=type(e).__name__,
                endpoint=f"/api/v1/reports/{report_id }/download",
                error_message=str(e),
                metadata={
                    "report_id": report_id,
                    "execution_time_ms": (time.time() - start_time) * 1000,
                },
            )
            logger.error(
                f"Report download error: {type (e ).__name__ }: {str (e )}",
                exc_info=True,
            )
            raise

    return app
