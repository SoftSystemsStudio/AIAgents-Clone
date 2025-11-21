"""
Gmail Cleanup API Endpoints.

Multi-tenant API for Gmail inbox analysis and cleanup operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.domain.customer import Customer
from src.api.auth import get_current_customer
# TODO: Import use cases when updated for multi-tenancy
# from src.application.gmail_cleanup_use_cases import (
#     AnalyzeInboxUseCase,
#     DryRunCleanupUseCase,
#     ExecuteCleanupUseCase,
# )

router = APIRouter()


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request to analyze Gmail inbox"""
    pass  # No params needed - analyzes current customer's inbox


class CleanupRuleRequest(BaseModel):
    """Cleanup rules for dry-run or execution"""
    categories_to_delete: List[str] = Field(
        default_factory=list,
        description="Email categories to delete (newsletters, promotions, social)",
        example=["newsletters", "promotions"]
    )
    older_than_days: Optional[int] = Field(
        default=90,
        description="Only delete emails older than N days",
        ge=1,
        le=3650
    )
    from_senders: Optional[List[str]] = Field(
        default=None,
        description="Specific sender emails to delete from",
        example=["noreply@example.com", "marketing@company.com"]
    )
    exclude_starred: bool = Field(
        default=True,
        description="Keep starred emails"
    )
    exclude_important: bool = Field(
        default=True,
        description="Keep important emails"
    )


class InboxAnalysisResponse(BaseModel):
    """Results of inbox analysis"""
    total_emails: int
    categories: dict  # category -> count
    largest_senders: List[dict]  # {email, count, size_mb}
    oldest_email_date: Optional[datetime]
    total_size_mb: float
    analyzed_at: datetime


class DryRunResponse(BaseModel):
    """Preview of what would be deleted"""
    emails_to_delete: int
    total_size_mb: float
    by_category: dict  # category -> count
    by_sender: dict  # sender -> count
    sample_subjects: List[str]  # First 10 subjects
    estimated_time_seconds: int


class CleanupExecutionResponse(BaseModel):
    """Results of cleanup execution"""
    cleanup_run_id: UUID
    emails_deleted: int
    size_freed_mb: float
    duration_seconds: float
    errors: List[str]
    completed_at: datetime
    quota_used: int  # Emails counted against quota
    quota_remaining: int


class CleanupHistoryResponse(BaseModel):
    """Customer's cleanup history"""
    cleanup_runs: List[dict]
    total_runs: int
    total_emails_deleted: int
    total_size_freed_mb: float


class UsageResponse(BaseModel):
    """Customer usage stats and quotas"""
    plan_tier: str
    emails_per_month_limit: int
    emails_used_this_month: int
    emails_remaining: int
    cleanups_per_day_limit: int
    cleanups_today: int
    cleanups_remaining_today: int
    is_on_trial: bool
    trial_ends_at: Optional[datetime]
    approaching_quota: bool


# Endpoints
@router.post("/analyze", response_model=InboxAnalysisResponse)
async def analyze_inbox(
    customer: Customer = Depends(get_current_customer),
    # TODO: Add use case dependencies
):
    """
    Analyze customer's Gmail inbox.
    
    Provides overview of:
    - Total email count
    - Breakdown by category (newsletters, promotions, social, etc.)
    - Largest senders
    - Oldest emails
    - Total storage used
    
    This is always free and doesn't count against quota.
    """
    # TODO: Call AnalyzeInboxUseCase with customer_id
    # analysis = await analyze_use_case.execute(customer_id=customer.id)
    
    # Mock response for now
    return InboxAnalysisResponse(
        total_emails=15420,
        categories={
            "newsletters": 8234,
            "promotions": 4122,
            "social": 2011,
            "primary": 1053,
        },
        largest_senders=[
            {"email": "noreply@linkedin.com", "count": 1234, "size_mb": 45.2},
            {"email": "news@nytimes.com", "count": 892, "size_mb": 123.4},
        ],
        oldest_email_date=datetime(2018, 1, 15),
        total_size_mb=3456.78,
        analyzed_at=datetime.utcnow(),
    )


@router.post("/cleanup/dry-run", response_model=DryRunResponse)
async def dry_run_cleanup(
    rules: CleanupRuleRequest,
    customer: Customer = Depends(get_current_customer),
    # TODO: Add use case dependencies
):
    """
    Preview cleanup results without deleting anything.
    
    Shows what would be deleted based on provided rules:
    - How many emails
    - Size to be freed
    - Breakdown by category/sender
    - Sample subjects for review
    
    This is free and doesn't count against quota.
    """
    # TODO: Call DryRunCleanupUseCase with customer_id and rules
    # preview = await dry_run_use_case.execute(
    #     customer_id=customer.id,
    #     rules=rules.dict()
    # )
    
    # Mock response
    return DryRunResponse(
        emails_to_delete=3421,
        total_size_mb=842.3,
        by_category={
            "newsletters": 2103,
            "promotions": 1318,
        },
        by_sender={
            "noreply@linkedin.com": 502,
            "news@nytimes.com": 401,
        },
        sample_subjects=[
            "Weekly Newsletter #234",
            "Flash Sale - 50% Off Everything!",
            "You have 12 new connection requests",
        ],
        estimated_time_seconds=120,
    )


@router.post("/cleanup/execute", response_model=CleanupExecutionResponse)
async def execute_cleanup(
    rules: CleanupRuleRequest,
    customer: Customer = Depends(get_current_customer),
    # TODO: Add use case and usage tracking dependencies
):
    """
    Execute Gmail cleanup - PERMANENTLY DELETE emails.
    
    ⚠️ WARNING: This will delete emails matching the rules.
    Always run dry-run first to preview.
    
    This operation:
    1. Checks customer quota
    2. Deletes matching emails
    3. Updates usage tracking
    4. Records audit log
    
    Counts against monthly email quota.
    """
    # Check quota before execution
    # TODO: Load current month's usage from database
    current_usage_count = 0  # Replace with actual
    
    if not customer.can_execute_cleanup(daily_count=current_usage_count):
        # This will be caught by quota_exceeded_handler
        quota = customer.get_quota()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily cleanup limit reached ({quota.cleanups_per_day}). Upgrade plan or try tomorrow."
        )
    
    # TODO: Execute cleanup use case
    # result = await execute_use_case.execute(
    #     customer_id=customer.id,
    #     rules=rules.dict()
    # )
    
    # TODO: Update usage tracking
    # await usage_tracker.record_cleanup(
    #     customer_id=customer.id,
    #     emails_processed=result.emails_deleted,
    #     period=datetime.utcnow().strftime("%Y-%m")
    # )
    
    # Mock response
    quota = customer.get_quota()
    emails_deleted = 3421  # Would come from actual execution
    
    return CleanupExecutionResponse(
        cleanup_run_id=UUID("12345678-1234-1234-1234-123456789abc"),
        emails_deleted=emails_deleted,
        size_freed_mb=842.3,
        duration_seconds=98.5,
        errors=[],
        completed_at=datetime.utcnow(),
        quota_used=emails_deleted,
        quota_remaining=quota.emails_per_month - emails_deleted,
    )


@router.get("/history", response_model=CleanupHistoryResponse)
async def get_cleanup_history(
    limit: int = 50,
    customer: Customer = Depends(get_current_customer),
    # TODO: Add repository dependency
):
    """
    Get customer's cleanup history.
    
    Returns past cleanup runs with:
    - Emails deleted
    - Size freed
    - Rules used
    - Timestamp
    
    Useful for tracking cleanup impact over time.
    """
    # TODO: Load from cleanup_runs table filtered by customer_id
    # runs = await cleanup_repository.get_by_customer(
    #     customer_id=customer.id,
    #     limit=limit
    # )
    
    # Mock response
    return CleanupHistoryResponse(
        cleanup_runs=[
            {
                "id": "12345678-1234-1234-1234-123456789abc",
                "executed_at": "2024-01-15T10:30:00Z",
                "emails_deleted": 3421,
                "size_freed_mb": 842.3,
                "categories": ["newsletters", "promotions"],
            }
        ],
        total_runs=1,
        total_emails_deleted=3421,
        total_size_freed_mb=842.3,
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage_stats(
    customer: Customer = Depends(get_current_customer),
    # TODO: Add usage tracking repository
):
    """
    Get customer's usage stats and quota limits.
    
    Shows:
    - Current plan tier
    - Monthly email quota (used/remaining)
    - Daily cleanup quota (used/remaining)
    - Trial status
    - Approaching quota warnings
    
    Use this to display quota meters in UI.
    """
    quota = customer.get_quota()
    
    # TODO: Load actual usage from database
    emails_used = 0  # Replace with actual monthly usage
    cleanups_today = 0  # Replace with actual daily count
    
    # Mock usage stats
    # In production, would call: UsageStats.from_usage_tracking(customer_id, period)
    
    return UsageResponse(
        plan_tier=customer.plan_tier.value,
        emails_per_month_limit=quota.emails_per_month,
        emails_used_this_month=emails_used,
        emails_remaining=quota.emails_per_month - emails_used,
        cleanups_per_day_limit=quota.cleanups_per_day,
        cleanups_today=cleanups_today,
        cleanups_remaining_today=quota.cleanups_per_day - cleanups_today,
        is_on_trial=customer.is_on_trial(),
        trial_ends_at=customer.trial_ends_at,
        approaching_quota=False,  # Would calculate: emails_used / quota > 0.8
    )


# Admin endpoints (require special permissions)
@router.post("/admin/reset-quota/{customer_id}")
async def reset_customer_quota(
    customer_id: UUID,
    current_customer: Customer = Depends(get_current_customer),
):
    """
    Admin only: Reset customer quota.
    
    Use for customer service issues or refunds.
    """
    # TODO: Check if current_customer is admin
    # TODO: Reset usage_tracking for customer
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin endpoints not yet implemented"
    )
