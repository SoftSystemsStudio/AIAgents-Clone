"""
Lightweight service health checks for external dependencies.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


async def check_supabase_health(supabase_url: Optional[str]) -> Dict[str, Any]:
    """Perform a basic Supabase health probe using the auth health endpoint.

    Returns a structured status dictionary that won't raise, making it safe to
    call from readiness endpoints.
    """

    if not supabase_url:
        return {"status": "disabled"}

    health_url = f"{supabase_url.rstrip('/')}/auth/v1/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
            if response.status_code == 200:
                return {"status": "healthy"}
            return {
                "status": "degraded",
                "http_status": response.status_code,
                "body": response.text,
            }
    except Exception as exc:  # pragma: no cover - defensive logging only
        return {"status": "unreachable", "error": str(exc)}


async def check_redis_health(redis_client: Optional[Any]) -> Dict[str, Any]:
    """Run a Redis ping with defensive error handling."""

    if redis_client is None:
        return {"status": "disabled"}

    try:
        ping_result = await redis_client.ping()
        return {"status": "healthy" if ping_result else "degraded"}
    except Exception as exc:  # pragma: no cover - defensive logging only
        return {"status": "unreachable", "error": str(exc)}


async def check_database_health(engine: Optional[Any]) -> Dict[str, Any]:
    """Execute a lightweight database ping."""

    if engine is None:
        return {"status": "disabled"}

    try:
        from sqlalchemy import text

        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            scalar = result.scalar()
        return {"status": "healthy" if scalar == 1 else "degraded"}
    except Exception as exc:  # pragma: no cover - defensive logging only
        return {"status": "unreachable", "error": str(exc)}


async def check_qdrant_health(
    base_url: Optional[str], api_key: Optional[str] = None, timeout: float = 5.0
) -> Dict[str, Any]:
    """Check the Qdrant health endpoint defensively."""

    if not base_url:
        return {"status": "disabled"}

    headers = {"api-key": api_key} if api_key else None
    health_url = f"{base_url.rstrip('/')}/healthz"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_url, headers=headers)
            if response.status_code == 200:
                return {"status": "healthy"}
            return {"status": "degraded", "http_status": response.status_code}
    except Exception as exc:  # pragma: no cover - defensive logging only
        return {"status": "unreachable", "error": str(exc)}
