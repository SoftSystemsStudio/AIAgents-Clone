"""Supabase client initialization helpers."""
from __future__ import annotations

from typing import Optional

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - optional dependency
    Client = None  # type: ignore
    create_client = None  # type: ignore

from src.config import SupabaseConfig


def init_supabase_client(config: SupabaseConfig) -> Optional["Client"]:
    """Initialize a Supabase client when credentials are provided.

    Returns None when Supabase is not configured so callers can safely
    fall back to other providers.
    """

    if not config.supabase_url or not config.supabase_service_role_key:
        return None

    if create_client is None:  # pragma: no cover - import guard
        raise ImportError(
            "Supabase package not installed. Install with: pip install supabase"
        )

    return create_client(config.supabase_url, config.supabase_service_role_key)
