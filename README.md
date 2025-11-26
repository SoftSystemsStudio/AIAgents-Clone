# AIAgents

[![CI/CD](https://github.com/SoftSystemsStudio/AIAgents/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/SoftSystemsStudio/AIAgents/actions)
[![codecov](https://codecov.io/gh/SoftSystemsStudio/AIAgents/branch/main/graph/badge.svg)](https://codecov.io/gh/SoftSystemsStudio/AIAgents)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-grade modular AI agents platform built with clean architecture principles. Optimized for reliability, observability, and maintainability.

## 🎯 Philosophy

This platform prioritizes:
- **Clean Architecture**: Domain-driven design with clear separation of concerns
- **Production Readiness**: Comprehensive observability, error handling, and testing
- **Modularity**: Swap LLM providers, vector stores, and message queues without changing business logic
- **Type Safety**: Full Pydantic validation and mypy type checking
- **Testability**: Dependency injection and interface-based design

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           Presentation Layer                │
│         (API, CLI, WebSocket)               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         Application Layer                   │
│  • Use Cases                                │
│  • Orchestration                            │
│  • Workflow Management                      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           Domain Layer                      │
│  • Business Logic (Agents, Tools)           │
│  • Domain Models                            │
│  • Service Interfaces                       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│       Infrastructure Layer                  │
│  • LLM Providers (OpenAI, Anthropic)        │
│  • Vector Stores (Qdrant, Chroma)           │
│  • Message Queues (Redis)                   │
│  • Observability (Logs, Traces, Metrics)    │
└─────────────────────────────────────────────┘
```

### Core Components

- **Domain Models**: `Agent`, `Message`, `Tool`, `ExecutionResult`
- **Orchestrator**: Manages agent execution loops, tool calling, and iteration limits
- **Infrastructure Adapters**: Pluggable implementations for external services
- **Observability**: Structured logging, distributed tracing, and Prometheus metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for local services)
- API keys for LLM providers (OpenAI, Anthropic)

### Installation

```bash
# Clone repository
git clone https://github.com/SoftSystemsStudio/AIAgents.git
cd AIAgents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install-dev

# Copy environment template
cp .env.example .env
# Edit .env and add your API keys

# Start infrastructure services
make docker-up

### Run the API with Docker Compose

When you prefer containers, use the built-in image and compose targets:

```bash
# Build the API image (installs dependencies)
docker compose build api

# Bring up the API alongside Postgres, Redis, and Qdrant
cp .env.example .env  # ensure secrets are present
docker compose up api postgres redis qdrant

# API will be available at http://localhost:8000
# Override service hosts for containers by uncommenting the container-friendly
# values at the bottom of .env.example before copying it.
```
```

### Simple Agent Example

```python
from examples.simple_agent import create_simple_agent
import asyncio

async def main():
    agent = create_simple_agent()
    result = await agent.run("What are the latest AI trends?")
    print(result.output)

asyncio.run(main())
```

### Gmail Cleanup Agent

Automate your inbox management with AI:

```bash
# Interactive agent (example)
python examples/gmail_cleanup_agent.py

# CLI for scheduled runs (production)
python scripts/run_gmail_cleanup.py --user-id=default --quick

# Or use Makefile commands
make gmail-analyze   # Analyze inbox
make gmail-preview   # Preview cleanup
make gmail-cleanup   # Execute cleanup

# API endpoints (RESTful)
curl -X POST http://localhost:8000/gmail/cleanup/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "max_threads": 100}'
```

**Features:**
- ✅ Analyze inbox and get health score
- ✅ Preview cleanup actions before executing  
- ✅ Archive old promotional/social emails
- ✅ Delete emails by sender or keyword
- ✅ Full audit trail of all actions
- ✅ RESTful API + CLI + Scheduler support

📖 **[Gmail Setup Guide](docs/GMAIL_SETUP.md)** | **[Architecture Details](docs/GMAIL_CLEANUP_ARCHITECTURE.md)**

## 📚 Documentation & assets

- **Guides & Playbooks:** See `docs/guides/` for deployment, quickstart, and enablement guides (moved here to keep the repo root tidy).
- **Free-tier stack blueprint:** `docs/guides/FREE_STACK_ENABLEMENT.md` outlines recommended providers (Vercel, Render, Supabase, Upstash, Sentry) and environment variables already supported in this repo.
- **Full-stack rollout checklist:** `docs/guides/FULL_STACK_ROLLOUT_CHECKLIST.md` gives the step-by-step to exercise every secret in `.env` and stand up the FastAPI + Next.js stack on free tiers.
- **Marketing site:** Static pages live in `website/` (`index.html`, `solutions.html`, `pricing.html`, `platform.html`). Run `./build.sh` to package them into `build/` for deployment.
- **Live demo telemetry:** The landing page consumes `/api/v1/demo/stream` (SSE) with a polling fallback for recent demo events. Keep this endpoint available in production for the on-page activity feed.
- **Production readiness gaps:** See `docs/PRODUCTION_READINESS_GAPS.md` for the prioritized backlog to reach a multi-page, live-agent experience.
- **Marketing site:** Static pages and configuration templates live in `website/`; `build.sh` copies these into `build/` for deployments.

## 📦 Project Structure

```
AIAgents/
├── src/
│   ├── domain/              # Business logic & abstractions
│   │   ├── models.py        # Core entities (Agent, Message, Tool)
│   │   ├── interfaces.py    # Service interfaces
│   │   └── exceptions.py    # Domain exceptions
│   │
│   ├── application/         # Use cases & orchestration
│   │   ├── orchestrator.py  # Agent execution engine
│   │   └── use_cases.py     # Business workflows
│   │
│   ├── infrastructure/      # External integrations
│   │   ├── llm_providers.py # OpenAI, Anthropic adapters
│   │   ├── vector_stores.py # Qdrant, Chroma adapters
│   │   ├── message_queue.py # Redis pub/sub
│   │   ├── repositories.py  # Data access
│   │   └── observability.py # Logging, tracing, metrics
│   │
│   └── config.py            # Configuration management
│
├── tests/
│   ├── conftest.py          # Test fixtures
│   ├── test_domain_models.py
│   ├── test_repositories.py
│   └── mock_tools.py
│
├── docs/                    # Additional documentation
├── .github/                 # CI/CD workflows
├── pyproject.toml           # Project metadata & dependencies
├── Makefile                 # Development commands
└── docker-compose.yml       # Local infrastructure
```

## 🔧 Configuration

Configuration is managed through environment variables and `.env` files:

```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_USE_HTTPS=false

# Optional
QDRANT_API_KEY=
QDRANT_TIMEOUT_SECONDS=10

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Observability
LOG_LEVEL=INFO
ENABLE_TRACING=true
ENABLE_METRICS=true
METRICS_PORT=9090
```

See `.env.example` for complete configuration options.

## 🧪 Testing

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_domain_models.py -v
```

## 📊 Observability

### Structured Logging

All logs are JSON-formatted with context:

```json
{
  "event": "agent_execution_started",
  "level": "info",
  "timestamp": "2024-01-15T10:30:00Z",
  "agent_id": "uuid-here",
  "agent_name": "research_assistant",
  "user_input": "..."
}
```

### Distributed Tracing

Integrated with OpenTelemetry for distributed tracing:

```python
with observability.start_span("agent_execution") as span:
    span.set_attribute("agent_id", str(agent.id))
    result = await orchestrator.execute_agent(agent, user_input)
```

### Metrics

Prometheus metrics exposed on `:9090/metrics`:

- `agent_execution_duration_seconds` - Execution time histogram
- `agent_execution_total` - Counter by status
- `llm_tokens_total` - Token usage by model
- `llm_cost_usd_total` - Cost tracking
- `tool_invocation_total` - Tool usage counter

## 🛡️ Error Handling & Guardrails

### Built-in Safeguards

- **Timeouts**: Configurable per-agent execution timeouts
- **Iteration Limits**: Prevent infinite loops in agent reasoning
- **Rate Limiting**: Token and request rate limits
- **Permission System**: Capability-based tool access control
- **Validation**: Comprehensive input validation with Pydantic

### Error Recovery

- **Automatic Retries**: Exponential backoff for transient failures
- **Graceful Degradation**: Fallback strategies for service failures
- **Detailed Error Messages**: Actionable error information

## 🔌 Extending the Platform

### Adding a New LLM Provider

```python
from src.domain.interfaces import ILLMProvider
from src.domain.models import Message

class CustomLLMProvider(ILLMProvider):
    async def generate_completion(
        self, messages: List[Message], model: str, **kwargs
    ) -> Message:
        # Your implementation
        pass
```

### Creating Custom Tools

```python
from src.domain.models import Tool, ToolParameter, AgentCapability

# Define tool
calculator = Tool(
    name="calculate",
    description="Perform mathematical calculations",
    parameters=[
        ToolParameter(name="expression", type="string", description="Math expression", required=True)
    ],
    handler_module="my_tools",
    handler_function="calculate_handler",
)

# Register tool
tool_registry.register_tool(calculator)

# Implement handler
def calculate_handler(expression: str) -> dict:
    result = eval(expression)  # In production, use safe parser
    return {"result": result}
```

## 📝 Development

```bash
# Format code
make format

# Lint
make lint

# Type check
make type-check

# Install pre-commit hooks
pre-commit install

# Run all checks
make format lint type-check test
```

## ⚠️ TODOs & Known Risks

### High Priority
- [ ] Implement persistent storage (PostgreSQL) for production
- [ ] Add request/response caching to reduce costs
- [ ] Implement dead letter queue for failed tasks
- [ ] Add circuit breaker pattern for external services
- [ ] Implement agent checkpointing for long-running tasks

### Risks & Mitigations
1. **LLM Provider Reliability**: Mitigated with retry logic and exponential backoff
2. **Cost Management**: Token counting, rate limits, and cost tracking
3. **Security**: Input validation, capability system, no eval of untrusted code
4. **Memory Leaks**: Timeout enforcement and memory limits per execution
5. **Message Queue Persistence**: Redis is in-memory; consider persistent queue for critical workflows

### Performance Considerations
- Vector store performance degrades with large collections (monitor and shard)
- LLM latency can be 2-10s per call (consider streaming for UX)
- Tool execution is synchronous (parallel execution coming)

## 📚 Additional Resources

- [Architecture Decision Records](docs/architecture.md)
- [Tool Development Guide](docs/tools.md)
- [Deployment Guide](docs/deployment.md)
- [API Reference](docs/api.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run all checks (`make format lint type-check test`)
5. Commit with clear messages
6. Push and create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [Pydantic](https://docs.pydantic.dev/) for data validation
- [structlog](https://www.structlog.org/) for structured logging
- [OpenTelemetry](https://opentelemetry.io/) for observability
- [Qdrant](https://qdrant.tech/) for vector search

---

**Maintainer**: AI Platform Team  
**Status**: Alpha - Production patterns, active development