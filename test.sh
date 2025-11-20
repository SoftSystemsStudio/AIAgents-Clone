#!/bin/bash
# Test Runner - Run examples with proper environment

set -a  # Automatically export all variables
source .env
set +a

export PYTHONPATH=/workspaces/AIAgents

echo "🧪 AI Agents Platform - Test Runner"
echo "===================================="
echo ""

if [ -z "$1" ]; then
    echo "Usage: ./test.sh <example_name>"
    echo ""
    echo "Available examples:"
    echo "  simple          - Simple agent without tools"
    echo "  tools           - Agent with calculator, time, search tools"
    echo "  rag             - Retrieval-augmented generation"
    echo "  multi           - Multi-agent coordination"
    echo "  streaming       - Streaming token delivery"
    echo "  database        - PostgreSQL persistence"
    echo "  templates       - Pre-built agent templates"
    echo "  ratelimit       - Rate limiting and cost control"
    echo ""
    echo "Example: ./test.sh simple"
    exit 0
fi

case "$1" in
    simple)
        python examples/simple_agent.py
        ;;
    tools)
        python examples/tool_using_agent.py
        ;;
    rag)
        python examples/rag_agent.py
        ;;
    multi)
        python examples/multi_agent_system.py
        ;;
    streaming)
        python examples/streaming_agent.py
        ;;
    database)
        python examples/database_persistence.py
        ;;
    templates)
        python examples/agent_templates.py
        ;;
    ratelimit)
        python examples/rate_limiting.py
        ;;
    *)
        echo "❌ Unknown example: $1"
        echo "Run './test.sh' for available options"
        exit 1
        ;;
esac
