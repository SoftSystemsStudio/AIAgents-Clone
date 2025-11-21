"""
Gmail Cleanup API Router - HTTP endpoints for inbox hygiene.

Provides REST API for:
- Analyzing inbox
- Previewing cleanup
- Executing cleanup
- Retrieving cleanup run details
- Managing cleanup policies
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from src.domain.cleanup_policy import CleanupPolicy
from src.domain.metrics import CleanupRun
from src.infrastructure.gmail_client import GmailClient
from src.application.services.inbox_hygiene_service import InboxHygieneService


router = APIRouter(prefix="/gmail/cleanup", tags=["Gmail Cleanup"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request to analyze inbox."""
    user_id: str = Field(..., description="User identifier")
    max_threads: int = Field(100, description="Maximum threads to analyze", ge=1, le=1000)
    policy_id: Optional[str] = Field(None, description="Custom policy ID (uses default if not provided)")


class PreviewRequest(BaseModel):
    """Request to preview cleanup."""
    user_id: str = Field(..., description="User identifier")
    max_threads: int = Field(100, description="Maximum threads to process", ge=1, le=1000)
    policy_id: Optional[str] = Field(None, description="Custom policy ID (uses default if not provided)")


class ExecuteRequest(BaseModel):
    """Request to execute cleanup."""
    user_id: str = Field(..., description="User identifier")
    max_threads: int = Field(100, description="Maximum threads to process", ge=1, le=1000)
    policy_id: Optional[str] = Field(None, description="Custom policy ID (uses default if not provided)")
    dry_run: bool = Field(False, description="Preview only, don't execute")


class QuickCleanupRequest(BaseModel):
    """Request for quick cleanup with defaults."""
    user_id: str = Field(..., description="User identifier")
    auto_archive_promotions: bool = Field(True, description="Archive old promotional emails")
    auto_archive_social: bool = Field(True, description="Archive old social emails")
    old_threshold_days: int = Field(30, description="Age threshold for archiving", ge=1, le=365)


class CreatePolicyRequest(BaseModel):
    """Request to create/update cleanup policy."""
    user_id: str = Field(..., description="User identifier")
    policy_id: str = Field(..., description="Policy identifier")
    name: str = Field(..., description="Policy name")
    description: str = Field("", description="Policy description")
    auto_archive_promotions: bool = Field(False, description="Auto-archive old promotions")
    auto_archive_social: bool = Field(False, description="Auto-archive old social emails")
    old_threshold_days: int = Field(30, description="Age threshold", ge=1, le=365)


# ============================================================================
# Dependency Injection
# ============================================================================

def get_gmail_client() -> GmailClient:
    """Get Gmail client instance."""
    return GmailClient(credentials_path='credentials.json')


def get_inbox_service(
    gmail_client: GmailClient = Depends(get_gmail_client)
) -> InboxHygieneService:
    """Get inbox hygiene service."""
    return InboxHygieneService(gmail_client)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/analyze", summary="Analyze inbox and get recommendations")
async def analyze_inbox(
    request: AnalyzeRequest,
    service: InboxHygieneService = Depends(get_inbox_service),
):
    """
    Analyze inbox and return recommendations without executing any actions.
    
    Returns:
    - Mailbox statistics
    - Health score
    - Recommended actions
    - Thread summaries
    """
    try:
        result = service.analyze_inbox(
            user_id=request.user_id,
            max_threads=request.max_threads,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview", summary="Preview cleanup actions")
async def preview_cleanup(
    request: PreviewRequest,
    service: InboxHygieneService = Depends(get_inbox_service),
):
    """
    Preview what cleanup would do without executing.
    
    Returns detailed plan showing:
    - All actions that would be taken
    - Affected emails
    - Estimated impact
    """
    try:
        result = service.preview_cleanup(
            user_id=request.user_id,
            max_threads=request.max_threads,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", summary="Execute cleanup")
async def execute_cleanup(
    request: ExecuteRequest,
    service: InboxHygieneService = Depends(get_inbox_service),
):
    """
    Execute cleanup and return results.
    
    Returns:
    - Actions taken
    - Success/failure counts
    - Storage freed
    - Before/after snapshots
    """
    try:
        result = service.execute_cleanup(
            user_id=request.user_id,
            max_threads=request.max_threads,
            dry_run=request.dry_run,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick", summary="Quick cleanup with defaults")
async def quick_cleanup(
    request: QuickCleanupRequest,
    service: InboxHygieneService = Depends(get_inbox_service),
):
    """
    Quick cleanup with sensible defaults.
    
    Archives old promotional and social emails.
    """
    try:
        result = service.quick_cleanup(
            user_id=request.user_id,
            auto_archive_promotions=request.auto_archive_promotions,
            auto_archive_social=request.auto_archive_social,
            old_threshold_days=request.old_threshold_days,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/{user_id}", summary="Get mailbox health score")
async def get_health_score(
    user_id: str,
    service: InboxHygieneService = Depends(get_inbox_service),
):
    """
    Calculate mailbox health score (0-100).
    
    Higher score indicates healthier inbox:
    - Lower unread ratio
    - Fewer old emails
    - Less promotional clutter
    """
    try:
        score = service.get_mailbox_health_score(user_id)
        return {
            "user_id": user_id,
            "health_score": score,
            "calculated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/policy", summary="Create or update cleanup policy")
async def create_policy(request: CreatePolicyRequest):
    """
    Create or update a cleanup policy.
    
    Policies define rules for automatic cleanup:
    - Which emails to archive
    - Which emails to delete
    - Age thresholds
    - Category-specific rules
    """
    try:
        policy = CleanupPolicy(
            id=request.policy_id,
            user_id=request.user_id,
            name=request.name,
            description=request.description,
            auto_archive_promotions=request.auto_archive_promotions,
            auto_archive_social=request.auto_archive_social,
            old_threshold_days=request.old_threshold_days,
        )
        
        # TODO: Persist policy to database
        # For now, return the policy as confirmation
        return {
            "status": "created",
            "policy_id": policy.id,
            "name": policy.name,
            "created_at": policy.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy/{user_id}/{policy_id}", summary="Get cleanup policy")
async def get_policy(user_id: str, policy_id: str):
    """
    Retrieve a cleanup policy by ID.
    
    TODO: Implement policy retrieval from database.
    """
    # TODO: Load from database
    raise HTTPException(status_code=501, detail="Policy retrieval not yet implemented")


@router.get("/runs/{user_id}", summary="List cleanup runs for user")
async def list_runs(user_id: str, limit: int = 10):
    """
    List recent cleanup runs for a user.
    
    TODO: Implement run history retrieval from database.
    """
    # TODO: Load from database
    raise HTTPException(status_code=501, detail="Run history not yet implemented")


@router.get("/runs/{user_id}/{run_id}", summary="Get cleanup run details")
async def get_run(user_id: str, run_id: str):
    """
    Get detailed information about a specific cleanup run.
    
    Includes:
    - All actions taken
    - Success/failure status
    - Before/after snapshots
    - Execution timeline
    
    TODO: Implement run retrieval from database.
    """
    # TODO: Load from database
    raise HTTPException(status_code=501, detail="Run retrieval not yet implemented")
