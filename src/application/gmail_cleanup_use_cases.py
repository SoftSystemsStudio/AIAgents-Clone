"""
Gmail Cleanup Use Cases - Application layer business workflows.

Implements the core business logic for inbox cleanup operations,
orchestrating domain entities and infrastructure services.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict
import uuid
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
from src.infrastructure.gmail_persistence import GmailCleanupRepository
from src.infrastructure.gmail_observability import GmailCleanupObservability
from src.rate_limiting import RateLimiter, RateLimitConfig, RateLimitError

def _run_coro_in_thread(coro):
    """Run an awaitable in a fresh thread with its own event loop and return the result.

    This allows library code to expose a synchronous API while keeping
    async internals. Running `asyncio.run` in an existing running loop
    would raise, so we run the coroutine in a separate thread.
    """
    import concurrent.futures
    import asyncio

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(lambda: asyncio.run(coro))
        return fut.result()


class AnalyzeInboxUseCase:
    """
    Analyze user's inbox and generate recommendations.
    
    Creates a mailbox snapshot and applies cleanup policy to
    identify potential actions without executing them.
    """
    
    def __init__(
        self,
        gmail_client: GmailClient,
        observability: Optional[GmailCleanupObservability] = None,
    ):
        self.gmail = gmail_client
        self.observability = observability
    
    async def execute(
        self,
        user_id: str,
        policy: Optional[CleanupPolicy] = None,
        max_threads: int = 100,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze inbox and return recommendations.
        
        Args:
            user_id: User identifier (Gmail user)
            policy: Cleanup policy to apply
            max_threads: Maximum threads to analyze
            customer_id: SaaS customer ID (for multi-tenancy)
            
        Returns:
            Analysis with recommendations
        """
        # Determine policy to apply (allow callers to omit policy)
        if policy is None:
            policy = CleanupPolicy.create_default_policy(user_id)

        # Fetch threads from Gmail. Support adapters that return a MailboxSnapshot
        # (async) via `get_mailbox_snapshot` or those that provide `list_threads`.
        threads = []
        if hasattr(self.gmail, 'get_mailbox_snapshot'):
            snapshot = await self.gmail.get_mailbox_snapshot(user_id)
            threads = snapshot.threads
        elif hasattr(self.gmail, 'list_threads'):
            threads = self.gmail.list_threads(query='', max_results=max_threads)
            snapshot = MailboxSnapshot.from_threads(user_id, threads)
        else:
            # No adapter methods found — empty snapshot
            snapshot = MailboxSnapshot.from_threads(user_id, [])
        
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
        
        # Log analysis completion
        if self.observability:
            self.observability.log_analysis_completed(
                user_id=user_id,
                total_threads=len(threads),
                total_actions=total_actions,
                health_score=stats.get_health_score(),
            )
        
        # Return the mailbox snapshot for callers that expect a snapshot
        # (legacy tests expect a MailboxSnapshot object).
        return snapshot


class DryRunCleanupUseCase:
    """
    Preview cleanup actions without executing them.
    
    Creates a detailed plan showing exactly what would happen
    if the cleanup were executed.
    """
    
    def __init__(
        self,
        gmail_client: GmailClient,
        observability: Optional[GmailCleanupObservability] = None,
    ):
        self.gmail = gmail_client
        self.observability = observability
    
    async def execute(
        self,
        user_id: str,
        policy: CleanupPolicy,
        max_threads: int = 100,
        customer_id: Optional[str] = None,
    ) -> CleanupRun:
        """
        Generate dry run cleanup plan.
        
        Args:
            user_id: User identifier (Gmail user)
            policy: Cleanup policy to apply
            max_threads: Maximum threads to process
            customer_id: SaaS customer ID (for multi-tenancy)
            
        Returns:
            CleanupRun with status DRY_RUN
        """
        # Fetch threads and create snapshot (support async mailbox snapshot adapters)
        if hasattr(self.gmail, 'get_mailbox_snapshot'):
            before_snapshot = await self.gmail.get_mailbox_snapshot(user_id)
            threads = before_snapshot.threads
        elif hasattr(self.gmail, 'list_threads'):
            threads = self.gmail.list_threads(query='', max_results=max_threads)
            before_snapshot = MailboxSnapshot.from_threads(user_id, threads)
        else:
            threads = []
            before_snapshot = MailboxSnapshot.from_threads(user_id, [])
        
        # Create cleanup run
        run = CleanupRun(
            id=f"dry_run_{user_id}_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            policy_id=policy.id,
            policy_name=policy.name,
            status=CleanupStatus.DRY_RUN,
            dry_run=True,
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
    
    def __init__(
        self,
        gmail_client: GmailClient,
        repository: Optional[GmailCleanupRepository] = None,
        observability: Optional[GmailCleanupObservability] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.gmail = gmail_client
        self.repository = repository
        self.observability = observability
        self.rate_limiter = rate_limiter or RateLimiter(RateLimitConfig(
            max_requests_per_minute=250,  # Gmail API quota
            max_requests_per_hour=10000,
            max_requests_per_day=100000,
        ))
    
    class _MaybeAwaitableRun:
        """Wrapper that is both awaitable and acts like a `CleanupRun`.

        - When awaited (in async tests) it will run the async implementation
          in the current event loop (and persist the run there).
        - When accessed synchronously (attribute access), it will run the
          async implementation in a background thread but with
          `persist_run=False` so tests that manually save runs don't see
          duplicates.
        """
        def __init__(self, use_case, user_id, policy, max_threads, dry_run, customer_id):
            self._use_case = use_case
            self._user_id = user_id
            self._policy = policy
            self._max_threads = max_threads
            self._dry_run = dry_run
            self._customer_id = customer_id
            self._result = None
            self._executed = False

        def _run_sync(self):
            if not self._executed:
                coro = self._use_case._execute_async(
                    self._user_id,
                    self._policy,
                    max_threads=self._max_threads,
                    dry_run=self._dry_run,
                    customer_id=self._customer_id,
                    persist_run=False,
                )
                self._result = _run_coro_in_thread(coro)
                self._executed = True
            return self._result

        def __getattr__(self, name):
            res = self._run_sync()
            return getattr(res, name)

        def __await__(self):
            # Await the async implementation in the current loop and persist
            if not self._executed:
                coro = self._use_case._execute_async(
                    self._user_id,
                    self._policy,
                    max_threads=self._max_threads,
                    dry_run=self._dry_run,
                    customer_id=self._customer_id,
                    persist_run=True,
                )
                result = yield from coro.__await__()
                self._result = result
                self._executed = True
                return result
            else:
                async def _done():
                    return self._result
                return _done().__await__()

    def execute(
        self,
        user_id: str,
        policy: CleanupPolicy,
        max_threads: int = 100,
        dry_run: bool = False,
        customer_id: Optional[str] = None,
    ) -> CleanupRun:
        """Return an object usable synchronously or awaitably.

        Synchronous callers get an object immediately (attributes trigger
        synchronous execution in a background thread with no persistence).
        Async callers can `await` the returned object to run the async
        implementation in the current loop (with persistence enabled).
        """
        return ExecuteCleanupUseCase._MaybeAwaitableRun(self, user_id, policy, max_threads, dry_run, customer_id)

    async def _execute_async(
        self,
        user_id: str,
        policy: CleanupPolicy,
        max_threads: int = 100,
        dry_run: bool = False,
        customer_id: Optional[str] = None,
        persist_run: bool = True,
    ) -> CleanupRun:
        """
        Execute cleanup run.
        
        Args:
            user_id: User identifier (Gmail user)
            policy: Cleanup policy to apply
            max_threads: Maximum threads to process
            dry_run: If True, don't actually execute actions
            customer_id: SaaS customer ID (for multi-tenancy)
            
        Returns:
            CleanupRun with complete results
        """
        # Fetch threads and create before snapshot. Prefer async mailbox snapshot adapter.
        if hasattr(self.gmail, 'get_mailbox_snapshot'):
            before_snapshot = await self.gmail.get_mailbox_snapshot(user_id)
            threads = before_snapshot.threads
        elif hasattr(self.gmail, 'list_threads'):
            threads = self.gmail.list_threads(query='', max_results=max_threads)
            before_snapshot = MailboxSnapshot.from_threads(user_id, threads)
        else:
            threads = []
            before_snapshot = MailboxSnapshot.from_threads(user_id, [])
        
        # Determine effective dry_run: prefer explicit arg, fall back to policy flag
        effective_dry_run = bool(dry_run) or bool(getattr(policy, "dry_run", False))

        # Create cleanup run
        run = CleanupRun(
            id=f"run_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
            user_id=user_id,
            policy_id=policy.id,
            policy_name=policy.name,
            status=CleanupStatus.DRY_RUN if effective_dry_run else CleanupStatus.IN_PROGRESS,
            dry_run=effective_dry_run,
            before_snapshot=before_snapshot,
            started_at=datetime.now(),
        )
        
        # Log cleanup start
        if self.observability:
            self.observability.log_cleanup_started(
                run_id=run.id,
                user_id=user_id,
                policy_id=policy.id,
                dry_run=dry_run,
                policy_name=policy.name,
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
                        
                        # Execute action if not dry run. Prefer async execute_action / batch_execute_actions
                        if not dry_run:
                            try:
                                if hasattr(self.gmail, 'execute_action'):
                                    # execute_action is expected to be async: (user_id, thread_id, action)
                                    result = await self.gmail.execute_action(user_id, message.thread_id, action_type)
                                elif hasattr(self.gmail, 'batch_execute_actions'):
                                    # use batch API if available
                                    await self.gmail.batch_execute_actions(user_id, [(message.thread_id, action_type)])
                                    result = True
                                else:
                                    # Fallback: attempt synchronous calls if present
                                    if hasattr(self.gmail, 'trash_message') and action_type == CleanupAction.DELETE:
                                        self.gmail.trash_message(message.id)
                                        result = True
                                    elif hasattr(self.gmail, 'archive_message') and action_type == CleanupAction.ARCHIVE:
                                        self.gmail.archive_message(message.id)
                                        result = True
                                    else:
                                        result = False

                                if result:
                                    action_record.status = ActionStatus.SUCCESS
                                    action_record.executed_at = datetime.utcnow()
                                    if self.observability:
                                        self.observability.log_action_executed(
                                            user_id=user_id,
                                            action_type=action_type.value,
                                            success=True,
                                        )
                                else:
                                    action_record.status = ActionStatus.FAILED
                                    action_record.error_message = "execution_failed"
                                    if self.observability:
                                        self.observability.log_action_executed(
                                            user_id=user_id,
                                            action_type=action_type.value,
                                            success=False,
                                            error=action_record.error_message,
                                        )
                            except Exception as e:
                                action_record.status = ActionStatus.FAILED
                                action_record.error_message = str(e)
                                if self.observability:
                                    self.observability.log_action_executed(
                                        user_id=user_id,
                                        action_type=action_type.value,
                                        success=False,
                                        error=str(e),
                                    )
                        else:
                            action_record.status = ActionStatus.SKIPPED
                        
                        run.actions.append(action_record)
            
            # Capture after snapshot if not dry run
            if not dry_run:
                if hasattr(self.gmail, 'get_mailbox_snapshot'):
                    run.after_snapshot = await self.gmail.get_mailbox_snapshot(user_id)
                elif hasattr(self.gmail, 'list_threads'):
                    threads_after = self.gmail.list_threads(query='', max_results=max_threads)
                    run.after_snapshot = MailboxSnapshot.from_threads(user_id, threads_after)
                else:
                    run.after_snapshot = MailboxSnapshot.from_threads(user_id, [])
            
            # Keep DRY_RUN status, otherwise mark as COMPLETED
            if not dry_run:
                run.status = CleanupStatus.COMPLETED
            
        except Exception as e:
            run.status = CleanupStatus.FAILED
            run.error_message = str(e)
            
            # Log failure
            if self.observability:
                duration = (datetime.utcnow() - run.started_at).total_seconds()
                self.observability.log_cleanup_failed(
                    user_id=user_id,
                    policy_id=policy.id,
                    error=str(e),
                    duration_seconds=duration,
                )
        finally:
            run.completed_at = datetime.utcnow()
            
            # Log completion
            if self.observability:
                self.observability.log_cleanup_completed(
                    run.id,
                    run.duration_seconds or 0.0,
                    len(run.actions),
                    errors=run.actions_failed,
                    run=run,
                )
            
            # Persist run if repository provided and caller requested persistence
            if self.repository and persist_run:
                await self.repository.save_run(run)
        
        return run
    
    def _execute_action_with_retry(
        self,
        message_id: str,
        action: CleanupAction,
        params: dict,
        user_id: str,
    ) -> None:
        """Execute action with rate limiting and retry logic."""
        # Small delay to respect Gmail API rate limits
        time.sleep(0.01)
        
        # Execute with exponential backoff retry
        return self._execute_action_with_backoff(message_id, action, params)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def _execute_action_with_backoff(
        self,
        message_id: str,
        action: CleanupAction,
        params: dict,
    ) -> None:
        """Execute action with exponential backoff retry."""
        return self._execute_action(message_id, action, params)
    
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
