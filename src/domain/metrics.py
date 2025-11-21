"""
Metrics Domain Models - Track cleanup operations and outcomes.

Defines entities for tracking cleanup runs, their results, and metrics
for reporting and observability.
"""

from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.domain.email_thread import MailboxSnapshot


class CleanupStatus(str, Enum):
    """Status of a cleanup run."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DRY_RUN = "dry_run"


class ActionStatus(str, Enum):
    """Status of an individual action."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CleanupAction:
    """
    Record of a single action taken during cleanup.
    
    Tracks what was done, to which email, and the outcome.
    """
    message_id: str
    action_type: str  # delete, archive, mark_read, etc.
    action_params: dict = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    
    # Context for audit trail
    message_subject: Optional[str] = None
    message_from: Optional[str] = None
    message_date: Optional[datetime] = None


@dataclass
class CleanupRun:
    """
    Complete record of a cleanup operation.
    
    Tracks input snapshot, all actions taken, outcomes, and metrics.
    """
    id: str
    user_id: str
    policy_id: str
    policy_name: str
    status: CleanupStatus
    
    # Snapshots
    before_snapshot: Optional[MailboxSnapshot] = None
    after_snapshot: Optional[MailboxSnapshot] = None
    
    # Actions
    actions: List[CleanupAction] = field(default_factory=list)
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Error tracking
    error_message: Optional[str] = None
    
    # Agent context (if AI-driven)
    agent_session_id: Optional[str] = None
    agent_model: Optional[str] = None
    agent_prompts: List[dict] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate run duration."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def actions_successful(self) -> int:
        """Count successful actions."""
        return sum(1 for a in self.actions if a.status == ActionStatus.SUCCESS)
    
    @property
    def actions_failed(self) -> int:
        """Count failed actions."""
        return sum(1 for a in self.actions if a.status == ActionStatus.FAILED)
    
    @property
    def actions_skipped(self) -> int:
        """Count skipped actions."""
        return sum(1 for a in self.actions if a.status == ActionStatus.SKIPPED)
    
    @property
    def actions_by_type(self) -> Dict[str, int]:
        """Group actions by type."""
        result = {}
        for action in self.actions:
            action_type = action.action_type
            result[action_type] = result.get(action_type, 0) + 1
        return result
    
    @property
    def emails_deleted(self) -> int:
        """Count emails deleted."""
        return sum(1 for a in self.actions 
                  if a.action_type == "delete" and a.status == ActionStatus.SUCCESS)
    
    @property
    def emails_archived(self) -> int:
        """Count emails archived."""
        return sum(1 for a in self.actions 
                  if a.action_type == "archive" and a.status == ActionStatus.SUCCESS)
    
    @property
    def emails_labeled(self) -> int:
        """Count emails labeled."""
        return sum(1 for a in self.actions 
                  if a.action_type == "apply_label" and a.status == ActionStatus.SUCCESS)
    
    @property
    def storage_freed_mb(self) -> Optional[float]:
        """Calculate storage freed (requires before/after snapshots)."""
        if not self.before_snapshot or not self.after_snapshot:
            return None
        return self.before_snapshot.size_mb - self.after_snapshot.size_mb
    
    def get_summary(self) -> dict:
        """
        Get human-readable summary of cleanup run.
        
        Returns dict suitable for reporting to users.
        """
        summary = {
            "run_id": self.id,
            "status": self.status.value,
            "policy": self.policy_name,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "actions": {
                "total": len(self.actions),
                "successful": self.actions_successful,
                "failed": self.actions_failed,
                "skipped": self.actions_skipped,
                "by_type": self.actions_by_type,
            },
            "outcomes": {
                "emails_deleted": self.emails_deleted,
                "emails_archived": self.emails_archived,
                "emails_labeled": self.emails_labeled,
            },
        }
        
        if self.storage_freed_mb is not None:
            summary["storage_freed_mb"] = round(self.storage_freed_mb, 2)
        
        if self.before_snapshot and self.after_snapshot:
            summary["mailbox_changes"] = {
                "before": self.before_snapshot.summary_stats(),
                "after": self.after_snapshot.summary_stats(),
            }
        
        if self.error_message:
            summary["error"] = self.error_message
        
        return summary


@dataclass
class MailboxStats:
    """
    Aggregate statistics about a user's mailbox over time.
    
    Tracks trends and health metrics.
    """
    user_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Counts
    total_messages: int = 0
    unread_messages: int = 0
    starred_messages: int = 0
    
    # By category
    primary_messages: int = 0
    social_messages: int = 0
    promotions_messages: int = 0
    updates_messages: int = 0
    forums_messages: int = 0
    
    # Storage
    total_size_mb: float = 0.0
    
    # Age distribution
    messages_last_7_days: int = 0
    messages_last_30_days: int = 0
    messages_last_90_days: int = 0
    messages_older_than_90_days: int = 0
    
    # Engagement
    messages_with_attachments: int = 0
    average_thread_size: float = 0.0
    
    @classmethod
    def from_snapshot(cls, snapshot: MailboxSnapshot) -> 'MailboxStats':
        """Create stats from a mailbox snapshot."""
        stats_dict = snapshot.summary_stats()
        
        return cls(
            user_id=snapshot.user_id,
            timestamp=snapshot.captured_at,
            total_messages=stats_dict["total_threads"],
            unread_messages=stats_dict["unread_threads"],
            starred_messages=0,  # Would need to track in snapshot
            primary_messages=stats_dict["categories"]["primary"],
            social_messages=stats_dict["categories"]["social"],
            promotions_messages=stats_dict["categories"]["promotions"],
            updates_messages=stats_dict["categories"]["updates"],
            forums_messages=stats_dict["categories"]["forums"],
            total_size_mb=snapshot.size_mb,
            messages_with_attachments=stats_dict["threads_with_attachments"],
            average_thread_size=stats_dict["average_messages_per_thread"],
        )
    
    def get_health_score(self) -> float:
        """
        Calculate mailbox health score (0-100).
        
        Higher is better. Based on unread ratio, old emails, etc.
        """
        if self.total_messages == 0:
            return 100.0
        
        score = 100.0
        
        # Penalize high unread ratio
        unread_ratio = self.unread_messages / self.total_messages
        score -= unread_ratio * 30  # Up to -30 points
        
        # Penalize lots of old messages
        old_ratio = self.messages_older_than_90_days / self.total_messages
        score -= old_ratio * 20  # Up to -20 points
        
        # Penalize high promotional ratio
        promo_ratio = self.promotions_messages / self.total_messages
        score -= max(0, (promo_ratio - 0.2) * 30)  # Penalize if >20%
        
        return max(0.0, min(100.0, score))


@dataclass
class CleanupReport:
    """
    Periodic report summarizing cleanup activity.
    
    Aggregates multiple cleanup runs into a summary report.
    """
    user_id: str
    period_start: datetime
    period_end: datetime
    
    cleanup_runs: List[CleanupRun] = field(default_factory=list)
    
    @property
    def total_runs(self) -> int:
        """Total cleanup runs in period."""
        return len(self.cleanup_runs)
    
    @property
    def successful_runs(self) -> int:
        """Count successful runs."""
        return sum(1 for r in self.cleanup_runs if r.status == CleanupStatus.COMPLETED)
    
    @property
    def failed_runs(self) -> int:
        """Count failed runs."""
        return sum(1 for r in self.cleanup_runs if r.status == CleanupStatus.FAILED)
    
    @property
    def total_emails_processed(self) -> int:
        """Total emails affected across all runs."""
        return sum(len(r.actions) for r in self.cleanup_runs)
    
    @property
    def total_emails_deleted(self) -> int:
        """Total emails deleted across all runs."""
        return sum(r.emails_deleted for r in self.cleanup_runs)
    
    @property
    def total_emails_archived(self) -> int:
        """Total emails archived across all runs."""
        return sum(r.emails_archived for r in self.cleanup_runs)
    
    @property
    def total_storage_freed_mb(self) -> float:
        """Total storage freed across all runs."""
        return sum(r.storage_freed_mb or 0.0 for r in self.cleanup_runs)
    
    @property
    def average_duration_seconds(self) -> Optional[float]:
        """Average run duration."""
        durations = [r.duration_seconds for r in self.cleanup_runs if r.duration_seconds]
        if not durations:
            return None
        return sum(durations) / len(durations)
    
    def get_summary(self) -> dict:
        """Get human-readable report summary."""
        return {
            "user_id": self.user_id,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "runs": {
                "total": self.total_runs,
                "successful": self.successful_runs,
                "failed": self.failed_runs,
            },
            "emails": {
                "processed": self.total_emails_processed,
                "deleted": self.total_emails_deleted,
                "archived": self.total_emails_archived,
            },
            "storage_freed_mb": round(self.total_storage_freed_mb, 2),
            "average_duration_seconds": self.average_duration_seconds,
        }
