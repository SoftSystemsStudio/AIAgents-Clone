"""
PostgreSQL Database Example - Production persistence.

Demonstrates:
- PostgreSQL repository usage
- Database migrations
- Conversation history persistence
- Connection pooling
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.models import Agent
from src.infrastructure.db_repositories import PostgreSQLAgentRepository
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator
from src.infrastructure.repositories import InMemoryToolRegistry
from src.config import get_config


async def main():
    """Demonstrate PostgreSQL persistence."""
    config = get_config()
    
    # Ensure API key is set
    if not config.llm.openai_api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        return
    
    print("=" * 80)
    print("🐘 POSTGRESQL PERSISTENCE DEMO")
    print("=" * 80)
    print()
    
    # Get database URL
    database_url = config.database.get_url()
    print(f"📊 Database: {database_url.split('@')[1] if '@' in database_url else database_url}")
    print()
    
    # Initialize repository
    print("🔄 Initializing database...")
    db_repo = PostgreSQLAgentRepository(
        database_url=database_url,
        pool_size=config.database.database_pool_size,
        max_overflow=config.database.database_max_overflow,
    )
    
    try:
        # Create tables if they don't exist
        await db_repo.initialize()
        print("✅ Database initialized")
        print()
        
        # Initialize other dependencies
        llm_provider = OpenAIProvider(api_key=config.llm.openai_api_key)
        tool_registry = InMemoryToolRegistry()
        logger = StructuredLogger()
        
        # Create orchestrator with PostgreSQL
        orchestrator = AgentOrchestrator(
            llm_provider=llm_provider,
            agent_repository=db_repo,
            tool_registry=tool_registry,
            observability=logger,
        )
        
        # === TEST 1: Create and Save Agent ===
        print("📝 TEST 1: Creating agent...")
        agent = Agent(
            name="Database Test Agent",
            description="Agent for testing PostgreSQL persistence",
            system_prompt="You are a helpful assistant that remembers conversations.",
            model_provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.7,
        )
        await db_repo.save(agent)
        print(f"✅ Agent created: {agent.name} (ID: {agent.id})")
        print()
        
        # === TEST 2: Retrieve Agent ===
        print("🔍 TEST 2: Retrieving agent from database...")
        retrieved = await db_repo.get_by_id(agent.id)
        if retrieved:
            print(f"✅ Agent retrieved: {retrieved.name}")
            print(f"   Conversation history: {len(retrieved.conversation_history)} messages")
        print()
        
        # === TEST 3: Execute Agent (adds to conversation history) ===
        print("💬 TEST 3: Having conversation (persists to DB)...")
        result1 = await orchestrator.execute_agent(
            agent=agent,
            user_input="My favorite color is blue. Remember this!",
        )
        print(f"🤖 Response: {result1.output[:100]}...")
        print(f"   Messages in history: {len(agent.conversation_history)}")
        print()
        
        # === TEST 4: Verify Persistence ===
        print("💾 TEST 4: Verifying conversation persisted...")
        retrieved = await db_repo.get_by_id(agent.id)
        if retrieved:
            print(f"✅ History persisted: {len(retrieved.conversation_history)} messages")
            for i, msg in enumerate(retrieved.conversation_history[-2:]):
                preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                print(f"   [{i+1}] {msg.role.value}: {preview}")
        print()
        
        # === TEST 5: Continue Conversation (memory test) ===
        print("🧠 TEST 5: Testing memory (asks about previous conversation)...")
        result2 = await orchestrator.execute_agent(
            agent=retrieved,  # Use retrieved agent to prove persistence
            user_input="What's my favorite color? You should remember!",
        )
        print(f"🤖 Response: {result2.output}")
        print()
        
        # === TEST 6: List All Agents ===
        print("📋 TEST 6: Listing all agents...")
        all_agents = await db_repo.list_all(limit=10)
        print(f"✅ Found {len(all_agents)} agents in database:")
        for a in all_agents:
            print(f"   - {a.name} (Status: {a.status.value})")
        print()
        
        # === TEST 7: Update Status ===
        print("🔄 TEST 7: Updating agent status...")
        await db_repo.update_status(agent.id, "completed")
        updated = await db_repo.get_by_id(agent.id)
        print(f"✅ Status updated: {updated.status.value}")
        print()
        
        # === TEST 8: Search by Name ===
        print("🔍 TEST 8: Searching by name...")
        found = await db_repo.get_by_name("Database Test Agent")
        if found:
            print(f"✅ Found agent: {found.name}")
            print(f"   Total conversation messages: {len(found.conversation_history)}")
        print()
        
        # === CLEANUP (Optional) ===
        print("🧹 Cleanup: Delete test agent? (y/n)")
        # Auto-delete for demo
        await db_repo.delete(agent.id)
        print("✅ Test agent deleted")
        print()
        
        # Summary
        print("=" * 80)
        print("✅ POSTGRESQL INTEGRATION SUCCESSFUL")
        print("=" * 80)
        print()
        print("Benefits of PostgreSQL persistence:")
        print("  ✓ Conversation history preserved across restarts")
        print("  ✓ Multi-agent coordination with shared state")
        print("  ✓ Production-ready with connection pooling")
        print("  ✓ ACID transactions for data consistency")
        print("  ✓ Efficient querying with indexes")
        print("  ✓ Backup and recovery capabilities")
        print()
        print("💡 To use in production:")
        print("   1. Set DATABASE_URL in .env")
        print("   2. Run migrations: python scripts/migrate_db.py")
        print("   3. Use PostgreSQLAgentRepository instead of InMemory")
        print()
        
    finally:
        # Close database connections
        await db_repo.close()
        print("🔒 Database connections closed")


if __name__ == "__main__":
    asyncio.run(main())
