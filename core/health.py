"""
Health check endpoints for monitoring and load balancers.
"""

from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import neomodel


def health_check(request):
    """
    Basic health check endpoint.
    Returns 200 if the application is running.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "ez_ram",
    })


def readiness_check(request):
    """
    Readiness check endpoint.
    Verifies that the application can handle requests.
    Checks database connections.
    """
    checks = {
        "status": "ready",
        "checks": {}
    }
    
    # Check PostgreSQL connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["checks"]["postgres"] = "ok"
    except Exception as e:
        checks["status"] = "not_ready"
        checks["checks"]["postgres"] = f"error: {str(e)}"
    
    # Check Neo4j connection
    try:
        neomodel.db.cypher_query("RETURN 1")
        checks["checks"]["neo4j"] = "ok"
    except Exception as e:
        checks["status"] = "not_ready"
        checks["checks"]["neo4j"] = f"error: {str(e)}"
    
    status_code = 200 if checks["status"] == "ready" else 503
    return JsonResponse(checks, status=status_code)


def liveness_check(request):
    """
    Liveness check endpoint.
    Returns 200 if the application process is alive.
    This is a simple check that doesn't verify dependencies.
    """
    return JsonResponse({
        "status": "alive",
        "debug": settings.DEBUG,
    })

