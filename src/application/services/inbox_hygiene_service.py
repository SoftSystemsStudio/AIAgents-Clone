"""
Inbox Hygiene Service - High-level orchestration.

Provides the main interface for inbox cleanup operations,
consumed by API endpoints, CLI, and schedulers.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from src.domain.cleanup_policy import CleanupPolicy
from src.domain.metrics import CleanupRun, CleanupReport
from src.infrastructure.gmail_client import GmailClient
from src.infrastructure.gmail_persistence import GmailCleanupRepository
from src.infrastructure.gmail_observability import GmailCleanupObservability
# TODO: Create these use cases in src/application/use_cases/gmail_cleanup.py
# from src.application.use_cases.gmail_cleanup import (
#     AnalyzeInboxUseCase,
#     DryRunCleanupUseCase,
#     ExecuteCleanupUseCase,
#     GenerateSummaryReportUseCase,
# )


class InboxHygieneService:
    """
    Main service for inbox hygiene operations.
    
    Orchestrates use cases, handles errors, and provides
    a clean interface for API/CLI/scheduler consumption.
    """
    
    def __init__(
        self,
        gmail_client: GmailClient,
        repository: Optional[GmailCleanupRepository] = None,
        observability: Optional[GmailCleanupObservability] = None,
    ):
        """
        Initialize service with Gmail client.
        
        Args:
            gmail_client: Configured GmailClient instance
            repository: Optional persistence layer
            observability: Optional observability layer
        """
        self.gmail = gmail_client
        self.repository = repository
        self.observability = observability
        
        # Initialize use cases with optional dependencies
        # TODO: Create these use cases in src/application/use_cases/gmail_cleanup.py
        # self.analyze_use_case = AnalyzeInboxUseCase(gmail_client, observability)
        # self.dry_run_use_case = DryRunCleanupUseCase(gmail_client, observability)
        # self.execute_use_case = ExecuteCleanupUseCase(gmail_client, repository, observability)
        # self.report_use_case = GenerateSummaryReportUseCase()
    
    def analyze_inbox(
        self,
        user_id: str,
        policy: Optional[CleanupPolicy] = None,
        max_threads: int = 100,
    ) -> Dict[str, Any]:
        """
        Analyze inbox and return recommendations.
        
        Args:
            user_id: User identifier
            policy: Cleanup policy (uses default if not provided)
            max_threads: Maximum threads to analyze
            
        Returns:
            Analysis with recommendations
        """
        if policy is None:
            policy = CleanupPolicy.create_default_policy(user_id)
        
        try:
            return self.analyze_use_case.execute(
                user_id=user_id,
                policy=policy,
                max_threads=max_threads,
            )
        except Exception as e:
            return {
                "error": str(e),
                "user_id": user_id,
                "analyzed_at": datetime.utcnow().isoformat(),
            }
    
    def preview_cleanup(
        self,
        user_id: str,
        policy: Optional[CleanupPolicy] = None,
        max_threads: int = 100,
    ) -> Dict[str, Any]:
        """
        Preview what cleanup would do without executing.
        
        Args:
            user_id: User identifier
            policy: Cleanup policy (uses default if not provided)
            max_threads: Maximum threads to process
            
        Returns:
            Dry run results
        """
        if policy is None:
            policy = CleanupPolicy.create_default_policy(user_id)
        
        try:
            run = self.dry_run_use_case.execute(
                user_id=user_id,
                policy=policy,
                max_threads=max_threads,
            )
            return run.get_summary()
        except Exception as e:
            return {
                "error": str(e),
                "user_id": user_id,
            }
    
    def execute_cleanup(
        self,
        user_id: str,
        policy: Optional[CleanupPolicy] = None,
        max_threads: int = 100,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute cleanup and return results.
        
        Args:
            user_id: User identifier
            policy: Cleanup policy (uses default if not provided)
            max_threads: Maximum threads to process
            dry_run: If True, preview only
            
        Returns:
            Cleanup results
        """
        if policy is None:
            policy = CleanupPolicy.create_default_policy(user_id)
        
        try:
            run = self.execute_use_case.execute(
                user_id=user_id,
                policy=policy,
                max_threads=max_threads,
                dry_run=dry_run,
            )
            return run.get_summary()
        except Exception as e:
            return {
                "error": str(e),
                "user_id": user_id,
            }
    
    def generate_report(self, cleanup_run: CleanupRun) -> str:
        """
        Generate human-readable report.
        
        Args:
            cleanup_run: CleanupRun to report on
            
        Returns:
            Formatted text report
        """
        return self.report_use_case.execute(cleanup_run)
    
    def get_mailbox_health_score(self, user_id: str) -> float:
        """
        Calculate mailbox health score (0-100).
        
        Args:
            user_id: User identifier
            
        Returns:
            Health score (higher is better)
        """
        try:
            analysis = self.analyze_inbox(user_id, max_threads=100)
            return analysis.get('health_score', 50.0)
        except Exception:
            return 50.0  # Default neutral score
    
    def quick_cleanup(
        self,
        user_id: str,
        auto_archive_promotions: bool = True,
        auto_archive_social: bool = True,
        old_threshold_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Quick cleanup with sensible defaults.
        
        Convenience method for common cleanup scenario:
        - Archive old promotions and social emails
        - Generate report
        
        Args:
            user_id: User identifier
            auto_archive_promotions: Archive old promotional emails
            auto_archive_social: Archive old social emails
            old_threshold_days: Age threshold for archiving
            
        Returns:
            Cleanup results
        """
        # Create quick cleanup policy
        policy = CleanupPolicy(
            id=f"quick_{user_id}",
            user_id=user_id,
            name="Quick Cleanup",
            description="Archive old promotional and social emails",
            auto_archive_promotions=auto_archive_promotions,
            auto_archive_social=auto_archive_social,
            old_threshold_days=old_threshold_days,
        )
        
        return self.execute_cleanup(
            user_id=user_id,
            policy=policy,
            max_threads=200,
        )
