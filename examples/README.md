# Examples

This directory contains practical examples demonstrating the AI Agents platform capabilities.

## Getting Started

Before running examples, ensure you have:

1. **Installed dependencies**:
   ```bash
   make install-dev
   ```

2. **Set your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

3. **Started infrastructure** (for some examples):
   ```bash
   make docker-up
   ```

## Examples Overview

### 1. Simple Agent (`simple_agent.py`)
**Difficulty**: Beginner  
**Dependencies**: OpenAI API key only

Basic agent that answers questions without tools. Perfect for getting started.

```bash
python examples/simple_agent.py
```

**What you'll learn**:
- Creating and configuring agents
- Basic agent execution
- Viewing metrics (tokens, cost, duration)

---

### 2. Tool-Using Agent (`tool_using_agent.py`)
**Difficulty**: Intermediate  
**Dependencies**: OpenAI API key only

Agent with multiple tools for calculations, time queries, and documentation search.

```bash
python examples/tool_using_agent.py
```

**What you'll learn**:
- Creating custom tools
- Tool registration and permissions
- How agents decide when to use tools
- Chaining multiple tool calls

---

### 3. RAG Agent (`rag_agent.py`)
**Difficulty**: Intermediate  
**Dependencies**: OpenAI API key, ChromaDB

Agent using Retrieval-Augmented Generation with semantic search.

```bash
python examples/rag_agent.py
```

**What you'll learn**:
- Setting up vector databases
- Semantic search for knowledge retrieval
- Grounding LLM responses in factual data
- Building question-answering systems

**Note**: Creates `./chroma_data/` directory for persistence.

---

### 4. Multi-Agent System (`multi_agent_system.py`)
**Difficulty**: Advanced  
**Dependencies**: OpenAI API key, Redis (optional)

Multiple specialized agents collaborating on complex tasks.

```bash
# Start Redis (optional)
docker-compose up -d redis

python examples/multi_agent_system.py
```

**What you'll learn**:
- Coordinating multiple agents
- Specialized agent roles (planner, researcher, executor, reviewer)
- Workflow orchestration
- Inter-agent communication

---

### 5. Streaming Agent (`streaming_agent.py`)
**Difficulty**: Intermediate  
**Dependencies**: OpenAI API key only

Real-time token streaming for better UX in chat interfaces.

```bash
python examples/streaming_agent.py
```

**What you'll learn**:
- Streaming vs non-streaming responses
- Real-time token delivery
- Server-sent events (SSE) pattern
- When to use streaming mode

**Features**:
- Side-by-side comparison of streaming vs non-streaming
- Live token display
- Performance metrics
- API integration examples

---

### 6. Streaming Client (`streaming_client.py`)
**Difficulty**: Beginner  
**Dependencies**: API server running

Interactive client for testing the streaming API endpoint.

```bash
# Terminal 1: Start API server
python src/api/rest.py

# Terminal 2: Run client
python examples/streaming_client.py

# Or with existing agent
python examples/streaming_client.py --agent-id <uuid>

# Demo mode
python examples/streaming_client.py --mode demo
```

**What you'll learn**:
- Consuming streaming APIs
- Server-sent events (SSE) client
- Interactive chat interfaces
- Real-time response handling

---

### 7. Database Persistence (`database_persistence.py`)
**Difficulty**: Intermediate  
**Dependencies**: OpenAI API key, PostgreSQL

Production-ready persistence with conversation history.

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run example
python examples/database_persistence.py
```

**What you'll learn**:
- PostgreSQL repository usage
- Conversation history persistence
- Database migrations
- Connection pooling
- Production deployment patterns

**Features**:
- ACID transaction support
- Efficient indexing
- Conversation history across restarts
- Multi-agent shared state

---

### 8. Agent Templates (`agent_templates.py`)
**Difficulty**: Beginner
**Dependencies**: OpenAI API key only

Pre-built specialized agents for common use cases.

```bash
python examples/agent_templates.py
```

**What you'll learn**:
- Using pre-configured agent templates
- Quick agent creation without prompt engineering
- Specialized agent configurations
- Template customization

**Available templates**:
- Code Reviewer - Reviews code quality
- SQL Generator - Converts English to SQL
- Documentation Writer - Generates docs
- Data Analyst - Analyzes data
- Research Assistant - Researches topics
- Customer Support - Empathetic support
- Content Creator - Marketing content
- System Architect - Designs architectures

---

### 9. Rate Limiting (`rate_limiting.py`)
**Difficulty**: Intermediate
**Dependencies**: OpenAI API key only

Cost control and usage quotas to prevent runaway expenses.

```bash
python examples/rate_limiting.py
```

**What you'll learn**:
- Request and token limits
- Cost caps per time window
- Per-user quotas
- Emergency stop functionality
- Usage monitoring

**Features**:
- Multi-window rate limiting (minute/hour/day)
- Token and cost budgets
- Burst allowance
- Real-time usage tracking
- Emergency kill switch

---

## Example Output

Each example provides detailed output including:
- **Agent responses**: The actual answers/results
- **Execution metrics**: Tokens used, duration, iterations
- **Cost tracking**: Estimated API costs
- **Process visibility**: What the agent is doing at each step

## Customization

All examples are self-contained and can be easily modified:

1. **Change models**: Edit `model_name` (e.g., `gpt-3.5-turbo` for lower cost)
2. **Adjust behavior**: Modify `system_prompt` for different personalities
3. **Add tools**: Create new tool handlers and register them
4. **Tune parameters**: Adjust `temperature`, `max_tokens`, `max_iterations`

## Tips

- **Start small**: Begin with `simple_agent.py` before advanced examples
- **Monitor costs**: Check metrics output to understand API usage
- **Experiment**: Modify prompts and parameters to see effects
- **Read code**: Examples are heavily commented for learning

## Troubleshooting

**"OPENAI_API_KEY not set"**
```bash
export OPENAI_API_KEY="your-key-here"
```

**Redis connection error (multi-agent example)**
```bash
docker-compose up -d redis
# Or run without Redis - it's optional
```

**ChromaDB issues (RAG example)**
```bash
pip install chromadb
# Or use Qdrant with docker-compose
```

## Next Steps

After running examples:

1. **Build your own agent**: Combine concepts from multiple examples
2. **Create custom tools**: Implement domain-specific capabilities
3. **Add persistence**: Use PostgreSQL for production storage
4. **Build an API**: Wrap agents in FastAPI endpoints
5. **Deploy to production**: Follow the deployment guide

## Contributing

Found an issue or have an idea for a new example? Please open an issue or PR!
