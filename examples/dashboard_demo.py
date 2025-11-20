"""
Dashboard Demo - Visualize agent activity in real-time.

This example demonstrates:
- Starting the FastAPI server with dashboard
- Running agents via API to generate metrics
- Viewing live statistics and charts

Run this:
1. python examples/dashboard_demo.py (runs both server and agents)
2. Browser: http://localhost:8000/dashboard
"""

import asyncio
import sys
import random
import time
import requests
from uuid import uuid4

from src.config import get_config
from src.domain.models import Agent, AgentCapability
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator


async def create_sample_agents(orchestrator: AgentOrchestrator, repo: InMemoryAgentRepository) -> list:
    """Create sample agents for testing."""
    agents = []
    
    # Code Reviewer
    agent1 = Agent(
        id=uuid4(),
        name="Code Reviewer",
        description="Reviews code for quality and best practices",
        system_prompt="You are a code reviewer. Analyze code and provide constructive feedback.",
        model_provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.3,
        max_tokens=1000,
        capabilities=[],
    )
    await repo.save(agent1)
    agents.append(agent1)
    
    # Math Helper
    agent2 = Agent(
        id=uuid4(),
        name="Math Helper",
        description="Solves mathematical problems",
        system_prompt="You are a math tutor. Help solve math problems step by step.",
        model_provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.2,
        max_tokens=500,
        capabilities=[],
    )
    await repo.save(agent2)
    agents.append(agent2)
    
    # Creative Writer
    agent3 = Agent(
        id=uuid4(),
        name="Creative Writer",
        description="Writes creative content",
        system_prompt="You are a creative writer. Write engaging and imaginative content.",
        model_provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.9,
        max_tokens=800,
        capabilities=[],
    )
    await repo.save(agent3)
    agents.append(agent3)
    
    return agents


async def run_sample_queries_via_api():
    """Run sample queries via API to generate dashboard data."""
    
    base_url = "http://localhost:8000"
    
    # Create agents via API
    agents = []
    agent_configs = [
        {
            "name": "Code Reviewer",
            "description": "Reviews code for quality",
            "system_prompt": "You are a code reviewer. Analyze code and provide brief feedback.",
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.3,
            "max_tokens": 800,
            "capabilities": [],
            "allowed_tools": [],
        },
        {
            "name": "Math Helper",
            "description": "Solves math problems",
            "system_prompt": "You are a math tutor. Solve problems concisely.",
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 400,
            "capabilities": [],
            "allowed_tools": [],
        },
        {
            "name": "Creative Writer",
            "description": "Writes creative content",
            "system_prompt": "You are a creative writer. Be imaginative and concise.",
            "model_provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.9,
            "max_tokens": 600,
            "capabilities": [],
            "allowed_tools": [],
        },
    ]
    
    print("\n" + "="*60)
    print("🎬 DASHBOARD DEMO - Setting Up Agents")
    print("="*60)
    
    # First, try to get existing agents
    try:
        response = requests.get(f"{base_url}/agents", timeout=10)
        if response.status_code == 200:
            existing_agents = response.json()
            agent_names = {a["name"]: a for a in existing_agents}
            
            # Use existing agents or create new ones
            for config in agent_configs:
                if config["name"] in agent_names:
                    agents.append(agent_names[config["name"]])
                    print(f"✅ Using existing: {config['name']}")
                else:
                    # Create new agent
                    response = requests.post(f"{base_url}/agents", json=config, timeout=10)
                    if response.status_code in [200, 201]:
                        agent = response.json()
                        agents.append(agent)
                        print(f"✅ Created: {config['name']}")
                    else:
                        print(f"❌ Failed to create {config['name']}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    if not agents:
        print("\n❌ No agents created, exiting")
        return
    
    # Query sets for each agent
    queries = {
        "Code Reviewer": [
            "Review: def add(a, b): return a + b",
            "Best practices for Python error handling?",
            "Is this efficient: for i in range(len(arr)): print(arr[i])",
        ],
        "Math Helper": [
            "What is 15% of 240?",
            "Solve: 2x + 5 = 15",
            "Area of circle with radius 7?",
        ],
        "Creative Writer": [
            "Write a haiku about coding",
            "Short story opening about AI",
            "Tagline for a coding bootcamp",
        ],
    }
    
    print(f"\n📊 Dashboard at: http://localhost:8000/dashboard")
    print(f"🔄 Running {sum(len(q) for q in queries.values())} queries...\n")
    
    total_executions = 0
    
    # Run queries in rounds
    for round_num in range(3):
        print(f"\n🔄 Round {round_num + 1}/3")
        print("-" * 60)
        
        for agent in agents:
            agent_name = agent["name"]
            agent_id = agent["id"]
            
            if agent_name in queries and queries[agent_name]:
                query = random.choice(queries[agent_name])
                
                print(f"\n🤖 {agent_name}")
                print(f"   Query: {query[:50]}{'...' if len(query) > 50 else ''}")
                
                try:
                    response = requests.post(
                        f"{base_url}/agents/{agent_id}/execute",
                        json={"user_input": query},
                        timeout=60,
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        total_executions += 1
                        
                        print(f"   ✅ {result['total_tokens']} tokens | "
                              f"${result['estimated_cost']:.4f} | "
                              f"{result['duration_seconds']:.2f}s")
                    else:
                        print(f"   ❌ Failed: {response.status_code}")
                
                except Exception as e:
                    print(f"   ❌ Error: {str(e)[:50]}")
                
                # Small delay
                time.sleep(0.5)
        
        # Delay between rounds
        if round_num < 2:
            print(f"\n⏸️  Waiting 2 seconds...")
            time.sleep(2)
    
    print("\n" + "="*60)
    print(f"✅ DEMO COMPLETE")
    print("="*60)
    print(f"\n📊 Total Executions: {total_executions}")
    print(f"🔍 Dashboard shows:")
    print(f"   • System stats (tokens, costs, success rates)")
    print(f"   • Live charts (usage over time)")
    print(f"   • Agent performance comparison")
    print(f"   • Recent execution history")
    print(f"\n💡 Run again to see metrics accumulate!\n")


def main_agents():
    """Run agents via API to generate dashboard data."""
    print("\n⏳ Waiting for API server to be ready...")
    
    # Wait for server
    for i in range(10):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ API server is ready!")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("❌ API server not responding. Start it first:")
        print("   python examples/dashboard_demo.py server")
        return
    
    # Run agents via API
    asyncio.run(run_sample_queries_via_api())


def main_server():
    """Start the API server with dashboard."""
    print("\n" + "="*60)
    print("🚀 STARTING API SERVER WITH DASHBOARD")
    print("="*60)
    print(f"\n📊 Dashboard: http://localhost:8000/dashboard")
    print(f"📚 API Docs:  http://localhost:8000/docs")
    print(f"\n💡 Dashboard will auto-update as agents run\n")
    
    import uvicorn
    from src.config import get_config
    
    config = get_config()
    
    uvicorn.run(
        "src.api.rest:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "server":
            main_server()
        elif mode == "agents":
            main_agents()
        else:
            print(f"❌ Unknown mode: {mode}")
            print(f"Usage:")
            print(f"  python examples/dashboard_demo.py server  # Start API server")
            print(f"  python examples/dashboard_demo.py agents  # Run test agents")
    else:
        print("🤖 Dashboard Demo")
        print("\nUsage:")
        print("  python examples/dashboard_demo.py server  # Start API server with dashboard")
        print("  python examples/dashboard_demo.py agents  # Run agents via API")
        print("\nRecommended workflow:")
        print("  1. Terminal 1: python examples/dashboard_demo.py server")
        print("  2. Terminal 2: python examples/dashboard_demo.py agents")
        print("  3. Browser:    http://localhost:8000/dashboard")
