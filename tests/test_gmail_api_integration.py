"""
Gmail API Integration Tests

These tests use the real Gmail API client to validate end-to-end functionality.
They require valid Gmail credentials (credentials.json) to run.

Setup:
1. Get OAuth credentials from Google Cloud Console
2. Place credentials.json in project root
3. Run: pytest tests/test_gmail_api_integration.py -v -m integration

Tests are skipped by default (require manual credentials setup).
"""
import pytest
import os
from datetime import datetime, timedelta
from typing import List

from src.domain.cleanup_policy import CleanupPolicy
from src.domain.cleanup_rule_builder import (
    CleanupRuleBuilder,
    archive_old_promotions,
)
from src.domain.email_thread import EmailCategory, EmailMessage
from src.application.use_cases.gmail_cleanup import (
    ExecuteCleanupUseCase,
    AnalyzeInboxUseCase,
)
from src.infrastructure.gmail_persistence import InMemoryGmailCleanupRepository


# Mark all tests as integration tests
pytestmark = pytest.mark.integration


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def credentials_available():
    """Check if Gmail credentials are available."""
    return os.path.exists('credentials.json')


@pytest.fixture
def gmail_client(credentials_available):
    """
    Provide real Gmail client.
    
    Skip tests if credentials not available.
    """
    if not credentials_available:
        pytest.skip("Gmail credentials.json not found")
    
    from src.infrastructure.gmail_client import GmailClient
    
    try:
        client = GmailClient()
        return client
    except Exception as e:
        pytest.skip(f"Failed to initialize Gmail client: {e}")


@pytest.fixture
def repository():
    """Provide in-memory repository for testing."""
    return InMemoryGmailCleanupRepository()


@pytest.fixture
def sample_policy():
    """Provide a safe test policy (archive only, no delete)."""
    return CleanupPolicy(
        id="test-policy",
        user_id="me",
        name="Test Policy",
        description="Safe testing policy (archive only)",
        cleanup_rules=[
            CleanupRuleBuilder()
                .category(EmailCategory.PROMOTIONS)
                .older_than_days(90)
                .archive()
                .with_priority(10)
                .build(),
        ],
    )


# ============================================================================
# Basic API Tests
# ============================================================================

@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_gmail_authentication(gmail_client):
    """
    Verify Gmail client can authenticate.
    
    This test ensures:
    - OAuth credentials are valid
    - Token is refreshed if needed
    - API connection is established
    """
    assert gmail_client.service is not None
    print("\n✅ Gmail authentication successful")


@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_list_recent_threads(gmail_client):
    """
    Test fetching recent threads from Gmail.
    
    Validates:
    - API queries work
    - Thread data is parsed correctly
    - Domain entities are created
    """
    threads = gmail_client.list_threads(
        query="",
        max_results=5,
    )
    
    assert isinstance(threads, list)
    print(f"\n📬 Fetched {len(threads)} recent threads")
    
    if threads:
        thread = threads[0]
        print(f"  Sample thread ID: {thread.id}")
        print(f"  Messages in thread: {len(thread.messages)}")
        print(f"  First message subject: {thread.messages[0].subject}")
        
        # Verify domain entity structure
        assert hasattr(thread, 'id')
        assert hasattr(thread, 'messages')
        assert len(thread.messages) > 0
        
        msg = thread.messages[0]
        assert hasattr(msg, 'id')
        assert hasattr(msg, 'subject')
        assert hasattr(msg, 'from_address')
        assert hasattr(msg, 'date')


@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_category_detection(gmail_client):
    """
    Test email category detection.
    
    Validates that Gmail's category labels are parsed correctly.
    """
    # Get some messages from different categories
    threads = gmail_client.list_threads(max_results=10)
    
    categories_found = set()
    for thread in threads:
        for msg in thread.messages:
            categories_found.add(msg.category.value)
    
    print(f"\n📂 Categories found: {categories_found}")
    
    # Should find at least one categorized message
    assert len(categories_found) > 0


# ============================================================================
# Workflow Tests with Real API
# ============================================================================

@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_analyze_inbox_with_real_api(gmail_client, sample_policy):
    """
    Test inbox analysis with real Gmail data.
    
    This is a READ-ONLY operation, safe to run.
    """
    use_case = AnalyzeInboxUseCase(gmail_client, None)
    
    analysis = use_case.execute(
        user_id="me",
        policy=sample_policy,
        max_threads=10,
    )
    
    # Verify analysis structure
    assert "user_id" in analysis
    assert "snapshot" in analysis
    assert "recommendations" in analysis
    assert "health_score" in analysis
    
    # Display results
    print(f"\n📊 Inbox Analysis (10 threads):")
    print(f"  Total threads: {analysis['snapshot']['total_threads']}")
    print(f"  Total messages: {analysis['snapshot']['total_messages']}")
    print(f"  Size: {analysis['snapshot']['size_mb']:.2f} MB")
    print(f"  Health score: {analysis['health_score']:.1f}%")
    
    if analysis['recommendations']['total_actions'] > 0:
        print(f"\n💡 Recommendations:")
        print(f"  Threads affected: {analysis['recommendations']['total_threads_affected']}")
        print(f"  Total actions: {analysis['recommendations']['total_actions']}")
        print(f"  Actions by type: {analysis['recommendations']['actions_by_type']}")


@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_dry_run_with_real_api(gmail_client, repository, sample_policy):
    """
    Test dry-run mode with real Gmail data.
    
    This is SAFE - it only reads data and plans actions, doesn't execute.
    """
    use_case = ExecuteCleanupUseCase(gmail_client, repository, None)
    
    run = use_case.execute(
        user_id="me",
        policy=sample_policy,
        max_threads=10,
        dry_run=True,
    )
    
    # Verify dry-run execution
    assert run.status.value == "dry_run"
    assert run.before_snapshot is not None
    assert run.before_snapshot.thread_count <= 10
    
    # Display plan
    print(f"\n📋 Dry-Run Results:")
    print(f"  Run ID: {run.id}")
    print(f"  Status: {run.status.value}")
    print(f"  Threads scanned: {run.before_snapshot.thread_count}")
    print(f"  Messages scanned: {run.before_snapshot.message_count}")
    print(f"  Actions planned: {len(run.actions)}")
    
    if run.actions:
        action_types = {}
        for action in run.actions:
            action_types[action.action_type] = action_types.get(action.action_type, 0) + 1
        
        print(f"\n  Action breakdown:")
        for action_type, count in action_types.items():
            print(f"    {action_type}: {count}")
        
        print(f"\n  Sample actions:")
        for action in run.actions[:3]:
            print(f"    - {action.action_type}: {action.message_subject[:50]}...")


# ============================================================================
# Safety Tests
# ============================================================================

@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_starred_messages_protected_with_real_api(gmail_client, repository):
    """
    Verify starred messages are protected with real Gmail data.
    
    Tests the safety guardrails with actual Gmail messages.
    """
    # Create aggressive policy that would match everything
    aggressive_policy = CleanupPolicy(
        id="aggressive-test",
        user_id="me",
        name="Aggressive Test",
        description="Test safety with aggressive policy",
        cleanup_rules=[
            CleanupRuleBuilder()
                .older_than_days(0)  # Match everything
                .archive()
                .build(),
        ],
    )
    
    use_case = ExecuteCleanupUseCase(gmail_client, repository, None)
    
    run = use_case.execute(
        user_id="me",
        policy=aggressive_policy,
        max_threads=20,
        dry_run=True,
    )
    
    # Check if any starred/important messages in the scanned threads
    starred_count = 0
    important_count = 0
    
    threads = gmail_client.list_threads(max_results=20)
    for thread in threads:
        for msg in thread.messages:
            if msg.is_starred:
                starred_count += 1
            if "IMPORTANT" in msg.labels:
                important_count += 1
    
    print(f"\n🛡️ Safety Validation:")
    print(f"  Starred messages found: {starred_count}")
    print(f"  Important messages found: {important_count}")
    print(f"  Actions planned: {len(run.actions)}")
    
    # Verify no starred/important messages in actions
    for action in run.actions:
        # Try to find the message
        for thread in threads:
            for msg in thread.messages:
                if msg.id == action.message_id:
                    assert not msg.is_starred, f"Starred message {msg.id} should be protected"
                    assert "IMPORTANT" not in msg.labels, f"Important message {msg.id} should be protected"
    
    print("  ✅ All starred/important messages protected")


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_invalid_message_id_handling(gmail_client):
    """
    Test error handling for invalid message IDs.
    
    Validates that API errors are caught and reported properly.
    """
    with pytest.raises(Exception) as exc_info:
        gmail_client.get_message("invalid_message_id_12345")
    
    error_message = str(exc_info.value)
    print(f"\n❌ Expected error: {error_message}")
    assert "Failed to get message" in error_message


@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_empty_query_handling(gmail_client):
    """
    Test handling of queries that return no results.
    
    Should return empty list, not error.
    """
    # Query for messages that shouldn't exist
    messages = gmail_client.list_messages(
        query="from:nonexistent@fakefakedomain12345.com",
        max_results=10,
    )
    
    assert isinstance(messages, list)
    assert len(messages) == 0
    print("\n✅ Empty query handled correctly")


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
@pytest.mark.slow
def test_pagination_performance(gmail_client):
    """
    Test pagination with larger result sets.
    
    Validates that pagination works correctly and efficiently.
    """
    import time
    
    start_time = time.time()
    
    # Fetch 50 threads (will require pagination)
    threads = gmail_client.list_threads(max_results=50)
    
    elapsed = time.time() - start_time
    
    print(f"\n⚡ Performance Test:")
    print(f"  Threads fetched: {len(threads)}")
    print(f"  Time elapsed: {elapsed:.2f}s")
    print(f"  Average per thread: {elapsed/max(len(threads), 1):.3f}s")
    
    # Should complete in reasonable time (adjust threshold as needed)
    assert elapsed < 60, "Pagination too slow"
    assert len(threads) <= 50


# ============================================================================
# Documentation Test
# ============================================================================

@pytest.mark.skipif(
    not os.path.exists('credentials.json'),
    reason="Gmail credentials required"
)
def test_integration_documentation():
    """
    Document the integration test process.
    
    This test serves as living documentation for API integration.
    """
    doc = """
    
    ═══════════════════════════════════════════════════════════════
    GMAIL API INTEGRATION - SETUP GUIDE
    ═══════════════════════════════════════════════════════════════
    
    PREREQUISITES
    ─────────────────────────────────────────────────────────────
    1. Google Cloud Project with Gmail API enabled
    2. OAuth 2.0 credentials downloaded as credentials.json
    3. credentials.json in project root directory
    
    FIRST RUN (AUTHENTICATION)
    ─────────────────────────────────────────────────────────────
    When you run these tests for the first time:
    
    1. Test will prompt for authentication
    2. Copy the URL and open in browser
    3. Sign in and grant permissions
    4. Copy authorization code back to terminal
    5. token.pickle will be created for future use
    
    SUBSEQUENT RUNS
    ─────────────────────────────────────────────────────────────
    After first authentication:
    
    1. token.pickle is loaded automatically
    2. Token is refreshed if expired
    3. No manual intervention needed
    
    RUNNING TESTS
    ─────────────────────────────────────────────────────────────
    # All integration tests
    pytest tests/test_gmail_api_integration.py -v -m integration
    
    # Specific test
    pytest tests/test_gmail_api_integration.py::test_dry_run_with_real_api -v
    
    # Include slow tests
    pytest tests/test_gmail_api_integration.py -v -m "integration and slow"
    
    SAFETY NOTES
    ─────────────────────────────────────────────────────────────
    ✓ Most tests are READ-ONLY (safe to run)
    ✓ Dry-run tests don't modify your Gmail
    ✓ Starred/important messages always protected
    ✓ Test policies use archive (not delete)
    ✓ Limited to small batches (10-50 threads)
    
    TROUBLESHOOTING
    ─────────────────────────────────────────────────────────────
    Q: Tests skipped?
    A: Place credentials.json in project root
    
    Q: Authentication error?
    A: Delete token.pickle and re-authenticate
    
    Q: Quota exceeded?
    A: Gmail API has daily quotas, try again later
    
    Q: Slow performance?
    A: Gmail API requires one request per message
       Consider reducing max_results for faster tests
    
    ═══════════════════════════════════════════════════════════════
    """
    
    print(doc)
    assert True  # Documentation test always passes
