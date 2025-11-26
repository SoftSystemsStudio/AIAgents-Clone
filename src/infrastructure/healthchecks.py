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
