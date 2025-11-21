"""
Gmail Cleanup API - Multi-tenant SaaS wrapper.

This module provides a FastAPI-based REST API for the Gmail cleanup solution.
Supports multiple customers with:
- JWT authentication
- Usage quotas per plan tier
- Rate limiting
- Audit logging
"""

from src.api.main import app
from src.api.auth import (
    get_current_customer,
    require_paid_plan,
    require_feature,
    create_access_token,
)

__all__ = [
    "app",
    "get_current_customer",
    "require_paid_plan",
    "require_feature",
    "create_access_token",
]
