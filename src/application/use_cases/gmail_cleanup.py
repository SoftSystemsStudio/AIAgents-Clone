"""
Gmail Cleanup Use Cases - Application layer business workflows.

Implements the core business logic for inbox cleanup operations,
orchestrating domain entities and infrastructure services.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict

from src.domain.email_thread import MailboxSnapshot, EmailThread, EmailMessage
from src.domain.cleanup_policy import CleanupPolicy, CleanupAction
from src.domain.metrics import (
    CleanupRun,
    CleanupStatus,
    CleanupAction as CleanupActionRecord,
    ActionStatus,
    MailboxStats,
)
from src.infrastructure.gmail_client import GmailClient


class AnalyzeInboxUseCase:
    """
    Analyze user's inbox and generate recommendations.
    
    Creates a mailbox snapshot and applies cleanup policy to
    identify potential actions without executing them.
    """
    
    def __init__(self, gmail_client: GmailClient):
        self.gmail = gmail_client
    
    def execute(
        self,
        user_id: str,
        policy: CleanupPolicy,
        max_threads: int = 100,
    ) -> Dict[str, Any]:
        """
        Analyze inbox and return recommendations.
        
        Args:
            user_id: User identifier
            policy: Cleanup policy to apply
            max_threads: Maximum threads to analyze
            
        Returns:
            Analysis with recommendations
        """
        # Fetch threads from Gmail
        threads = self.gmail.list_threads(query='', max_results=max_threads)
        
        # Create mailbox snapshot
        snapshot = MailboxSnapshot.from_threads(user_id, threads)
        
        # Generate mailbox stats
        stats = MailboxStats.from_snapshot(snapshot)
        
        # Analyze each thread for potential actions
        recommendations = []
        total_actions = 0
        actions_by_type = {}
        
        for thread in threads:
            analysis = policy.analyze_thread(thread)
            if analysis['total_actions'] > 0:
                recommendations.append(analysis)
                total_actions += analysis['total_actions']
                
                # Count actions by type
                for msg in analysis['messages']:
                    for action_type, _ in msg['actions']:
                        actions_by_type[action_type] = actions_by_type.get(action_type, 0) + 1
        
        return {
            "user_id": user_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "snapshot": {
                "total_threads": len(threads),
                "total_messages": snapshot.message_count,
                "size_mb": snapshot.size_mb,
                "stats": stats.get_health_score(),
            },
            "policy": {
                "id": policy.id,
                "name": policy.name,
            },
            "recommendations": {
                "total_threads_affected": len(recommendations),
                "total_actions": total_actions,
                "actions_by_type": actions_by_type,
                "threads": recommendations[:10],  # Limit for display
            },
            "health_score": stats.get_health_score(),
        }


class DryRunCleanupUseCase:
    """
    Preview cleanup actions without executing them.
    
    Creates a detailed plan showing exactly what would happen
    if the cleanup were executed.
    """
    
    def __init__(self, gmail_client: GmailClient):
        self.gmail = gmail_client
    
    def execute(
        self,
        user_id: str,
        policy: CleanupPolicy,
        max_threads: int = 100,
    ) -> CleanupRun:
        """
        Generate dry run cleanup plan.
        
        Args:
            user_id: User identifier
            policy: Cleanup policy to apply
            max_threads: Maximum threads to process
            
        Returns:
            CleanupRun with status DRY_RUN
        """
        # Fetch threads and create snapshot
        threads = self.gmail.list_threads(query='', max_results=max_threads)
        before_snapshot = MailboxSnapshot.from_threads(user_id, threads)
        
        # Create cleanup run
        run = CleanupRun(
            id=f"dry_run_{user_id}_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            policy_id=policy.id,
            policy_name=policy.name,
            status=CleanupStatus.DRY_RUN,
            before_snapshot=before_snapshot,
        )
        
        # Generate actions for each thread
        for thread in threads:
            for message in thread.messages:
                actions = policy.get_actions_for_message(message)
                for action_type, params in actions:
                    run.actions.append(CleanupActionRecord(
                        message_id=message.id,
                        action_type=action_type.value,
                        action_params=params,
                        status=ActionStatus.PENDING,
                        message_subject=message.subject,
                        message_from=str(message.from_address),
                        message_date=message.date,
                    ))
        
        return run


class ExecuteCleanupUseCase:
    """
    Execute cleanup actions and track results.
    
    Applies cleanup policy, executes actions, captures metrics,
    and creates audit trail.
    """
    
    def __init__(self, gmail_client: GmailClient):
        self.gmail = gmail_client
    
    def execute(
        self,
        user_id: str,
        policy: CleanupPolicy,
        max_threads: int = 100,
        dry_run: bool = False,
    ) -> CleanupRun:
        """
        Execute cleanup run.
        
        Args:
            user_id: User identifier
            policy: Cleanup policy to apply
            max_threads: Maximum threads to process
            dry_run: If True, don't actually execute actions
            
        Returns:
            CleanupRun with complete results
        """
        # Fetch threads and create before snapshot
        threads = self.gmail.list_threads(query='', max_results=max_threads)
        before_snapshot = MailboxSnapshot.from_threads(user_id, threads)
        
        # Create cleanup run
        run = CleanupRun(
            id=f"run_{user_id}_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            policy_id=policy.id,
            policy_name=policy.name,
            status=CleanupStatus.IN_PROGRESS,
            before_snapshot=before_snapshot,
            started_at=datetime.utcnow(),
        )
        
        try:
            # Process each thread
            for thread in threads:
                for message in thread.messages:
                    actions = policy.get_actions_for_message(message)
                    
                    for action_type, params in actions:
                        action_record = CleanupActionRecord(
                            message_id=message.id,
                            action_type=action_type.value,
                            action_params=params,
                            message_subject=message.subject,
                            message_from=str(message.from_address),
                            message_date=message.date,
                        )
                        
                        # Execute action if not dry run
                        if not dry_run:
                            try:
                                self._execute_action(message.id, action_type, params)
                                action_record.status = ActionStatus.SUCCESS
                                action_record.executed_at = datetime.utcnow()
                            except Exception as e:
                                action_record.status = ActionStatus.FAILED
                                action_record.error_message = str(e)
                        else:
                            action_record.status = ActionStatus.SKIPPED
                        
                        run.actions.append(action_record)
            
            # Capture after snapshot if not dry run
            if not dry_run:
                threads_after = self.gmail.list_threads(query='', max_results=max_threads)
                run.after_snapshot = MailboxSnapshot.from_threads(user_id, threads_after)
            
            run.status = CleanupStatus.COMPLETED
            
        except Exception as e:
            run.status = CleanupStatus.FAILED
            run.error_message = str(e)
        finally:
            run.completed_at = datetime.utcnow()
        
        return run
    
    def _execute_action(
        self,
        message_id: str,
        action: CleanupAction,
        params: dict,
    ) -> None:
        """Execute a single cleanup action."""
        if action == CleanupAction.DELETE:
            self.gmail.trash_message(message_id)
        elif action == CleanupAction.ARCHIVE:
            self.gmail.archive_message(message_id)
        elif action == CleanupAction.MARK_READ:
            self.gmail.mark_read(message_id)
        elif action == CleanupAction.MARK_UNREAD:
            self.gmail.mark_unread(message_id)
        elif action == CleanupAction.STAR:
            self.gmail.star_message(message_id)
        elif action == CleanupAction.UNSTAR:
            self.gmail.unstar_message(message_id)
        elif action == CleanupAction.APPLY_LABEL:
            label = params.get('label')
            if label:
                self.gmail.modify_labels(message_id, add_labels=[label])
        elif action == CleanupAction.REMOVE_LABEL:
            label = params.get('label')
            if label:
                self.gmail.modify_labels(message_id, remove_labels=[label])
        # SKIP action does nothing


class GenerateSummaryReportUseCase:
    """
    Generate human-readable summary report of cleanup run.
    
    Formats cleanup results for presentation to users.
    """
    
    def execute(self, cleanup_run: CleanupRun) -> str:
        """
        Generate summary report.
        
        Args:
            cleanup_run: CleanupRun to summarize
            
        Returns:
            Formatted text summary
        """
        summary = cleanup_run.get_summary()
        
        report = f"""
        📊 Gmail Cleanup Summary
        ========================
        
        Run ID: {summary['run_id']}
        Status: {summary['status']}
        Policy: {summary['policy']}
        Started: {summary['started_at']}
        Duration: {summary.get('duration_seconds', 0):.1f}s
        
        📧 Actions Taken:
        - Total: {summary['actions']['total']}
        - Successful: {summary['actions']['successful']}
        - Failed: {summary['actions']['failed']}
        - Skipped: {summary['actions']['skipped']}
        
        📈 Outcomes:
        - Emails Deleted: {summary['outcomes']['emails_deleted']}
        - Emails Archived: {summary['outcomes']['emails_archived']}
        - Emails Labeled: {summary['outcomes']['emails_labeled']}
        """
        
        if 'storage_freed_mb' in summary:
            report += f"\n💾 Storage Freed: {summary['storage_freed_mb']:.2f} MB\n"
        
        if summary.get('error'):
            report += f"\n⚠️ Error: {summary['error']}\n"
        
        return report.strip()
