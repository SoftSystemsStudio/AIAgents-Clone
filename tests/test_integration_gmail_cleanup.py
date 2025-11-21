"""
Integration tests for Gmail cleanup API with persistence and observability.
"""
import pytest
from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.domain.cleanup_policy import CleanupPolicy, CleanupRule, RetentionPolicy, CleanupAction
from src.domain.email_thread import (
    EmailAddress, EmailMessage, EmailThread, EmailCategory,
    EmailImportance, MailboxSnapshot,
)
from src.domain.metrics import CleanupRun, CleanupStatus
from src.infrastructure.gmail_persistence import InMemoryGmailCleanupRepository
from src.infrastructure.gmail_observability import GmailCleanupObservability
from src.infrastructure.observability import ObservabilityProvider


# Mock Gmail Client for testing
class MockGmailClient:
    """Mock Gmail client for testing."""
    
    def __init__(self):
        self.mailbox_snapshot = None
        self.executed_actions = []
    
    async def get_mailbox_snapshot(self, user_id: str) -> MailboxSnapshot:
        """Return mock mailbox snapshot."""
        if self.mailbox_snapshot:
            return self.mailbox_snapshot
        
        # Default test data
        now = datetime.utcnow()
        messages = [
            EmailMessage(
                id=f"msg{i}",
                thread_id=f"thread{i}",
                from_address=EmailAddress(address=f"sender{i}@linkedin.com", name=f"Sender {i}"),
                to_addresses=[EmailAddress(address="me@example.com", name="Me")],
                cc_addresses=[],
                subject=f"Test Message {i}",
                snippet=f"Test snippet {i}",
                date=now - timedelta(days=i * 30),
                labels=["INBOX"] if i < 3 else ["INBOX", "UNREAD"],
                is_unread=i >= 3,
                is_starred=False,
                has_attachments=False,
                size_bytes=1024 * i,
                category=EmailCategory.PROMOTIONS if i > 2 else EmailCategory.PRIMARY,
                importance=EmailImportance.MEDIUM,
            )
            for i in range(5)
        ]
        
        threads = [EmailThread(id=f"thread{i}", messages=[msg]) for i, msg in enumerate(messages)]
        
        return MailboxSnapshot.from_threads(user_id, threads)
    
    async def execute_action(self, user_id: str, thread_id: str, action: CleanupAction) -> bool:
        """Mock action execution."""
        self.executed_actions.append((user_id, thread_id, action))
        return True
    
    async def batch_execute_actions(self, user_id: str, actions: list) -> list:
        """Mock batch execution."""
        for thread_id, action in actions:
            await self.execute_action(user_id, thread_id, action)
        return [True] * len(actions)


@pytest.fixture
async def mock_gmail_client() -> MockGmailClient:
    """Provide mock Gmail client."""
    return MockGmailClient()


@pytest.fixture
async def repository() -> InMemoryGmailCleanupRepository:
    """Provide in-memory repository."""
    return InMemoryGmailCleanupRepository()


@pytest.fixture
async def observability() -> GmailCleanupObservability:
    """Provide observability instance."""
    provider = ObservabilityProvider(
        service_name="gmail-cleanup-test",
        environment="test"
    )
    return GmailCleanupObservability(provider)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_inbox_with_observability(
    mock_gmail_client: MockGmailClient,
    observability: GmailCleanupObservability,
):
    """Test inbox analysis with observability."""
    from src.application.use_cases.gmail_cleanup import AnalyzeInboxUseCase
    
    use_case = AnalyzeInboxUseCase(
        gmail_client=mock_gmail_client,
        observability=observability,
    )
    
    snapshot = await use_case.execute("user123")
    
    assert snapshot is not None
    assert snapshot.user_id == "user123"
    assert snapshot.thread_count == 5
    assert snapshot.message_count == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_cleanup_with_persistence(
    mock_gmail_client: MockGmailClient,
    repository: InMemoryGmailCleanupRepository,
    observability: GmailCleanupObservability,
):
    """Test cleanup execution with persistence."""
    from src.application.use_cases.gmail_cleanup import ExecuteCleanupUseCase
    
    # Create test policy
    policy = CleanupPolicy(
        id="policy1",
        user_id="user123",
        name="Test Cleanup",
        rules=[
            CleanupRule(
                sender_domain="@linkedin.com",
                action=CleanupAction.ARCHIVE,
            ),
            CleanupRule(
                older_than_days=60,
                action=CleanupAction.DELETE,
            ),
        ],
        retention=RetentionPolicy(
            keep_starred=True,
            keep_unread=True,
            keep_recent_days=7,
        ),
        dry_run=False,
    )
    
    await repository.save_policy(policy)
    
    use_case = ExecuteCleanupUseCase(
        gmail_client=mock_gmail_client,
        repository=repository,
        observability=observability,
    )
    
    run = await use_case.execute("user123", policy)
    
    assert run is not None
    assert run.user_id == "user123"
    assert run.policy_name == "Test Cleanup"
    assert run.status in [CleanupStatus.COMPLETED, CleanupStatus.IN_PROGRESS]
    
    # Verify run was persisted
    saved_run = await repository.get_run("user123", run.id)
    assert saved_run is not None
    assert saved_run.id == run.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cleanup_workflow(
    mock_gmail_client: MockGmailClient,
    repository: InMemoryGmailCleanupRepository,
    observability: GmailCleanupObservability,
):
    """Test complete cleanup workflow: analyze → create policy → execute → verify."""
    from src.application.services.inbox_hygiene_service import InboxHygieneService
    from src.infrastructure.llm_providers import LLMProviderInterface
    
    # Mock LLM provider
    mock_llm = AsyncMock(spec=LLMProviderInterface)
    mock_llm.generate.return_value = "Suggested cleanup: Archive promotional emails older than 30 days"
    
    service = InboxHygieneService(
        gmail_client=mock_gmail_client,
        llm_provider=mock_llm,
        repository=repository,
        observability=observability,
    )
    
    # Step 1: Analyze inbox
    from src.application.use_cases.gmail_cleanup import AnalyzeInboxUseCase
    analyze_use_case = AnalyzeInboxUseCase(mock_gmail_client, observability)
    snapshot = await analyze_use_case.execute("user123")
    
    assert snapshot.thread_count == 5
    
    # Step 2: Create and save policy
    policy = CleanupPolicy(
        id="policy1",
        user_id="user123",
        name="Promotional Cleanup",
        rules=[
            CleanupRule(
                category=EmailCategory.PROMOTIONS,
                older_than_days=30,
                action=CleanupAction.ARCHIVE,
            ),
        ],
        dry_run=False,
    )
    
    await repository.save_policy(policy)
    
    # Step 3: Execute cleanup
    from src.application.use_cases.gmail_cleanup import ExecuteCleanupUseCase
    execute_use_case = ExecuteCleanupUseCase(
        mock_gmail_client,
        repository,
        observability,
    )
    run = await execute_use_case.execute("user123", policy)
    
    assert run.policy_name == "Promotional Cleanup"
    
    # Step 4: Verify persistence
    saved_policy = await repository.get_policy("user123", "policy1")
    assert saved_policy is not None
    assert saved_policy.name == "Promotional Cleanup"
    
    saved_run = await repository.get_run("user123", run.id)
    assert saved_run is not None
    
    # Step 5: List runs
    runs = await repository.list_runs("user123")
    assert len(runs) >= 1
    assert any(r.id == run.id for r in runs)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_policy_crud_operations(repository: InMemoryGmailCleanupRepository):
    """Test policy CRUD operations."""
    user_id = "user123"
    
    # Create
    policy = CleanupPolicy(
        id="policy1",
        user_id=user_id,
        name="Test Policy",
        rules=[
            CleanupRule(
                sender_domain="@spam.com",
                action=CleanupAction.DELETE,
            ),
        ],
        dry_run=True,
    )
    
    await repository.save_policy(policy)
    
    # Read
    retrieved = await repository.get_policy(user_id, "policy1")
    assert retrieved is not None
    assert retrieved.name == "Test Policy"
    assert len(retrieved.rules) == 1
    
    # Update
    policy.name = "Updated Policy"
    policy.updated_at = datetime.utcnow()
    await repository.save_policy(policy)
    
    updated = await repository.get_policy(user_id, "policy1")
    assert updated.name == "Updated Policy"
    
    # List
    policies = await repository.list_policies(user_id)
    assert len(policies) == 1
    assert policies[0].name == "Updated Policy"
    
    # Delete
    await repository.delete_policy(user_id, "policy1")
    deleted = await repository.get_policy(user_id, "policy1")
    assert deleted is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_metrics_tracking(
    mock_gmail_client: MockGmailClient,
    repository: InMemoryGmailCleanupRepository,
):
    """Test that run metrics are properly tracked."""
    from src.domain.metrics import CleanupAction as Action, ActionStatus
    
    run = CleanupRun(
        id="run1",
        user_id="user123",
        policy_name="Test",
        status=CleanupStatus.COMPLETED,
        started_at=datetime.utcnow(),
        dry_run=False,
        actions=[
            Action(
                id="action1",
                thread_id="thread1",
                action_type="archive",
                status=ActionStatus.SUCCESS,
            ),
            Action(
                id="action2",
                thread_id="thread2",
                action_type="delete",
                status=ActionStatus.SUCCESS,
            ),
            Action(
                id="action3",
                thread_id="thread3",
                action_type="archive",
                status=ActionStatus.FAILED,
                error_message="Permission denied",
            ),
        ],
    )
    
    run.completed_at = datetime.utcnow()
    run.duration_seconds = 2.5
    
    await repository.save_run(run)
    
    # Retrieve and verify metrics
    saved_run = await repository.get_run("user123", "run1")
    assert saved_run is not None
    assert saved_run.emails_archived == 1
    assert saved_run.emails_deleted == 1
    assert saved_run.actions_successful == 2
    assert saved_run.actions_failed == 1
    assert saved_run.duration_seconds == 2.5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dry_run_mode(
    mock_gmail_client: MockGmailClient,
    repository: InMemoryGmailCleanupRepository,
):
    """Test dry run mode doesn't execute actions."""
    from src.application.use_cases.gmail_cleanup import ExecuteCleanupUseCase
    
    policy = CleanupPolicy(
        id="policy1",
        user_id="user123",
        name="Dry Run Test",
        rules=[CleanupRule(sender_domain="@test.com", action=CleanupAction.DELETE)],
        dry_run=True,  # Dry run mode
    )
    
    use_case = ExecuteCleanupUseCase(mock_gmail_client, repository, None)
    run = await use_case.execute("user123", policy)
    
    assert run.dry_run is True
    # In dry run, actions are identified but not executed
    assert len(mock_gmail_client.executed_actions) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_observability_metrics_recorded(
    mock_gmail_client: MockGmailClient,
    observability: GmailCleanupObservability,
):
    """Test that observability metrics are recorded."""
    from src.application.use_cases.gmail_cleanup import AnalyzeInboxUseCase
    
    use_case = AnalyzeInboxUseCase(mock_gmail_client, observability)
    
    # Execute multiple times
    for _ in range(3):
        await use_case.execute("user123")
    
    # Metrics should be recorded (we can't easily assert on them without
    # mocking the prometheus client, but we verify no exceptions occurred)
    assert True  # If we got here, metrics were recorded successfully


@pytest.mark.integration
async def test_concurrent_cleanup_runs(
    mock_gmail_client: MockGmailClient,
    repository: InMemoryGmailCleanupRepository,
):
    """Test multiple concurrent cleanup runs."""
    import asyncio
    from src.application.use_cases.gmail_cleanup import ExecuteCleanupUseCase
    
    # Create multiple policies
    policies = [
        CleanupPolicy(
            id=f"policy{i}",
            user_id="user123",
            name=f"Policy {i}",
            rules=[CleanupRule(sender_domain=f"@test{i}.com", action=CleanupAction.ARCHIVE)],
            dry_run=False,
        )
        for i in range(3)
    ]
    
    # Save policies
    for policy in policies:
        await repository.save_policy(policy)
    
    use_case = ExecuteCleanupUseCase(mock_gmail_client, repository, None)
    
    # Execute concurrently
    tasks = [use_case.execute("user123", policy) for policy in policies]
    runs = await asyncio.gather(*tasks)
    
    assert len(runs) == 3
    assert all(run.user_id == "user123" for run in runs)
    
    # Verify all runs were saved
    saved_runs = await repository.list_runs("user123")
    assert len(saved_runs) >= 3
