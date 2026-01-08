"""Health check endpoints for monitoring and Kubernetes readiness"""
from flask import Blueprint, jsonify
from sqlalchemy import text
from datetime import datetime

from app import db, get_db_type, cache

bp = Blueprint("health", __name__)


@bp.route("/health", methods=["GET"])
def health_check():
    """
    Simple health check endpoint

    Returns basic health status for load balancers and monitoring systems.
    Returns 200 OK if critical components are functioning.
    """
    db_type = get_db_type()
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {}
    }

    # Check database connectivity
    try:
        if db_type == "postgres":
            db.session.execute(text("SELECT 1"))
            status["components"]["database"] = "healthy"
        else:
            from app import mongo
            mongo.db.client.admin.command("ping")
            status["components"]["database"] = "healthy"
    except Exception as e:
        status["components"]["database"] = "unhealthy"
        status["status"] = "degraded"

    # Check Redis connectivity
    try:
        cache.set("health_check", "ok", timeout=5)
        cache.get("health_check")
        status["components"]["cache"] = "healthy"
    except Exception as e:
        status["components"]["cache"] = "unhealthy"
        status["status"] = "degraded"

    # Determine overall status
    all_healthy = all(
        component_status == "healthy"
        for component_status in status["components"].values()
    )

    if all_healthy:
        status_code = 200
        status["status"] = "healthy"
    else:
        status_code = 503
        status["status"] = "degraded"

    return jsonify(status), status_code


@bp.route("/ready", methods=["GET"])
def readiness_check():
    """
    Readiness check endpoint

    More thorough than /health, checks if the application
    is ready to handle traffic. Used by Kubernetes
    during rolling updates.

    Returns:
    - 200 OK if application is ready
    - 503 Service Unavailable if not ready
    """
    db_type = get_db_type()
    checks = {
        "ready": False,
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # Database readiness check
    try:
        if db_type == "postgres":
            result = db.session.execute(text("SELECT 1")).scalar()
            if result == 1:
                checks["database"] = "pass"
            else:
                checks["database"] = "fail"
        else:
            from app import mongo
            mongo.db.client.admin.command("ping")
            checks["database"] = "pass"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Cache readiness check
    try:
        cache.set("ready_check", "ok", timeout=5)
        cache.get("ready_check")
        checks["cache"] = "pass"
    except Exception as e:
        checks["cache"] = f"error: {str(e)}"

    # Check if migrations are applied (optional, can be enhanced)
    try:
        if db_type == "postgres":
            from alembic.config import main as alembic_cfg
            from alembic.script import ScriptDirectory

            config = alembic_cfg.Config()
            config.set_main_option("sqlalchemy.url", app.config.get("SQLALCHEMY_DATABASE_URI"))
            script = ScriptDirectory.from_config(config)

            # Check if alembic_version table exists and has a head
            try:
                from app import db
                engine = db.engine
                from sqlalchemy import inspect

                inspector = inspect(engine)
                has_alembic = inspector.has_table("alembic_version")
                checks["migrations"] = "pass" if has_alembic else "skip"
            except Exception:
                checks["migrations"] = "skip"
        else:
            checks["migrations"] = "skip"
    except Exception as e:
        checks["migrations"] = f"error: {str(e)}"

    # Determine overall readiness
    all_pass = all(
        check_status in ["pass", "skip"]
        for check_status in checks["checks"].values()
    )

    if all_pass:
        checks["ready"] = True
        status_code = 200
    else:
        checks["ready"] = False
        status_code = 503

    return jsonify(checks), status_code


@bp.route("/metrics", methods=["GET"])
def metrics():
    """
    Simple metrics endpoint

    Returns basic application metrics for monitoring dashboards.
    This is a lightweight alternative to Prometheus integration.
    """
    from app.repositories import item_repo, type_repo, location_repo, user_repo

    try:
        # Item counts
        item_stats = item_repo.get_stats()

        # Type count
        types_count = len(type_repo.list_types())

        # Location count
        locations_count = len(list(location_repo.list_locations()))

        # User count (basic)
        users_count = user_repo.count_all()

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "application": "item-manage-system",
            "version": "1.0.0",
            "counts": {
                "total_items": item_stats["total"],
                "items_with_photo": item_stats["with_photo"],
                "items_with_location": item_stats["with_location"],
                "items_with_type": item_stats["with_type"],
                "types": types_count,
                "locations": locations_count,
                "users": users_count,
            }
        }

        return jsonify(metrics), 200
    except Exception as e:
        from app.utils.error_handler import log_error
        log_error(f"Failed to gather metrics: {str(e)}")
        return jsonify({"error": "Metrics unavailable"}), 500
