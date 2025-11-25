"""
Test fixtures and utilities.

Provides reusable fixtures for testing.
"""

import importlib.util
import inspect
from uuid import uuid4

import pytest

from src.domain.models import (
    Agent,
    AgentCapability,
    AgentStatus,
    Message,
    MessageRole,
    Tool,
    ToolParameter,
)
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger


def _is_pytest_cov_available() -> bool:
    """Return True when the pytest-cov plugin is importable.

    In sandboxed environments dependencies may be unavailable. Registering the
    coverage flags ourselves allows the suite to run without failing on
    ``--cov`` arguments that are configured in ``pyproject.toml``.
    """

    return importlib.util.find_spec("pytest_cov") is not None


def _is_pytest_asyncio_available() -> bool:
    """Return True when pytest-asyncio plugin is importable."""

    return importlib.util.find_spec("pytest_asyncio") is not None


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register no-op coverage options when pytest-cov is missing."""

    if _is_pytest_cov_available():
        return

    parser.addoption(
        "--cov",
        action="store",
        default=None,
        help="No-op placeholder when pytest-cov is unavailable.",
    )
    parser.addoption(
        "--cov-report",
        action="append",
        default=[],
        help="No-op placeholder when pytest-cov is unavailable.",
    )

    if not _is_pytest_asyncio_available():
        parser.addini(
            "asyncio_mode",
            "Mode for pytest-asyncio compatibility in environments without the plugin",
            "string",
            default="auto",
        )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip async tests when pytest-asyncio is unavailable.

    The sandbox environment may lack access to optional dependencies. Rather
    than failing collection for coroutine tests, mark them as skipped with a
    clear reason so the rest of the suite can still run.
    """

    if _is_pytest_asyncio_available():
        return

    skip_async = pytest.mark.skip(reason="pytest-asyncio not available in this environment")
    for item in items:
        # item.obj may be missing for some item types, so guard access
        test_func = getattr(item, "obj", None)
        if test_func and inspect.iscoroutinefunction(test_func):
            item.add_marker(skip_async)


@pytest.fixture
def sample_agent() -> Agent:
    """Create a sample agent for testing."""
    return Agent(
        name="test_agent",
        description="A test agent",
        system_prompt="You are a helpful test assistant.",
        model_provider="openai",
        model_name="gpt-4",
        temperature=0.7,
        max_tokens=1000,
        capabilities=[AgentCapability.WEB_SEARCH],
        allowed_tools=["search_web"],
        max_iterations=5,
        timeout_seconds=60,
    )


@pytest.fixture
def sample_message() -> Message:
    """Create a sample message for testing."""
    return Message(
        role=MessageRole.USER,
        content="Hello, how are you?",
    )


@pytest.fixture
def sample_tool() -> Tool:
    """Create a sample tool for testing."""
    return Tool(
        name="search_web",
        description="Search the web for information",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True,
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="Number of results to return",
                required=False,
                default=5,
            ),
        ],
        required_capability=AgentCapability.WEB_SEARCH,
        handler_module="tests.mock_tools",
        handler_function="mock_search_web",
    )


@pytest.fixture
def agent_repository() -> InMemoryAgentRepository:
    """Create an in-memory agent repository."""
    return InMemoryAgentRepository()


@pytest.fixture
def tool_registry() -> InMemoryToolRegistry:
    """Create an in-memory tool registry."""
    return InMemoryToolRegistry()


@pytest.fixture
def observability() -> StructuredLogger:
    """Create an observability service."""
    return StructuredLogger(log_level="DEBUG")


@pytest.fixture
async def populated_agent_repository(
    agent_repository: InMemoryAgentRepository,
    sample_agent: Agent,
) -> InMemoryAgentRepository:
    """Create a repository with a sample agent."""
    await agent_repository.save(sample_agent)
    return agent_repository


@pytest.fixture
def populated_tool_registry(
    tool_registry: InMemoryToolRegistry,
    sample_tool: Tool,
) -> InMemoryToolRegistry:
    """Create a tool registry with a sample tool."""
    tool_registry.register_tool(sample_tool)
    return tool_registry
