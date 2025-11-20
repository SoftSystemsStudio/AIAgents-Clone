"""
Memory-Enabled Agent - Example showing conversational agents with long-term memory.

This example demonstrates:
- Multi-turn conversations with context retention
- Session-based memory grouping
- Retrieving relevant past context
- Conversation continuity across runs
"""

import asyncio
from uuid import uuid4

from src.config import get_config
from src.domain.models import Agent, Message, MessageRole
from src.domain.memory import ConversationMemory, MemoryConfig
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator


async def demo_basic_memory():
    """
    Demo 1: Basic conversation with memory.
    
    Shows how an agent remembers facts from earlier in the conversation.
    """
    print("\n" + "="*70)
    print("📚 DEMO 1: BASIC CONVERSATION MEMORY")
    print("="*70)
    
    config = get_config()
    
    # Initialize components
    observability = StructuredLogger(log_level="WARNING")
    llm_provider = OpenAIProvider(api_key=config.llm.openai_api_key)
    agent_repo = InMemoryAgentRepository()
    tool_registry = InMemoryToolRegistry()
    
    # Create memory system
    memory = ConversationMemory(config=MemoryConfig(max_memories_per_retrieval=5))
    
    # Create agent
    agent = Agent(
        id=uuid4(),
        name="Memory Assistant",
        description="An assistant that remembers our conversation",
        system_prompt="You are a helpful assistant. You have a good memory and can recall things from our conversation.",
        model_provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=500,
    )
    await agent_repo.save(agent)
    
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
        agent_repository=agent_repo,
        observability=observability,
    )
    
    session_id = "demo_session_1"
    
    # Conversation 1: Tell the agent some facts
    print("\n💬 User: My name is Alice and I love Python programming.")
    
    result1 = await orchestrator.execute_agent(
        agent=agent,
        user_input="My name is Alice and I love Python programming.",
    )
    
    # Store conversation in memory
    user_msg1 = Message(role=MessageRole.USER, content="My name is Alice and I love Python programming.")
    assistant_msg1 = Message(role=MessageRole.ASSISTANT, content=result1.output or "")
    
    await memory.store_message(agent.id, user_msg1, session_id=session_id)
    await memory.store_message(agent.id, assistant_msg1, session_id=session_id)
    
    print(f"🤖 Assistant: {result1.output}\n")
    
    # Conversation 2: Reference the past
    print("💬 User: What's my name and what do I like?")
    
    # Retrieve relevant context
    context_results = await memory.retrieve_relevant_context(
        agent_id=agent.id,
        query="What's my name and what do I like?",
        session_id=session_id,
    )
    
    # Build context string from memory
    if context_results:
        context_str = "\\n\\nPrevious conversation:\\n"
        for result in context_results[:3]:  # Top 3 relevant memories
            context_str += f"- {result.entry.message.role.value}: {result.entry.message.content}\\n"
        
        enhanced_prompt = f"{context_str}\\n\\nCurrent question: What's my name and what do I like?"
    else:
        enhanced_prompt = "What's my name and what do I like?"
    
    result2 = await orchestrator.execute_agent(
        agent=agent,
        user_input=enhanced_prompt,
    )
    
    print(f"🤖 Assistant: {result2.output}\n")
    
    # Store this exchange too
    user_msg2 = Message(role=MessageRole.USER, content="What's my name and what do I like?")
    assistant_msg2 = Message(role=MessageRole.ASSISTANT, content=result2.output or "")
    
    await memory.store_message(agent.id, user_msg2, session_id=session_id)
    await memory.store_message(agent.id, assistant_msg2, session_id=session_id)
    
    # Show memory stats
    stats = memory.get_memory_stats(agent.id)
    print(f"📊 Memory Stats:")
    print(f"   • Total memories: {stats['total_memories']}")
    print(f"   • Sessions: {stats['sessions']}")
    print(f"   • Time span: {stats['oldest']} to {stats['newest']}")


async def demo_session_continuity():
    """
    Demo 2: Session continuity.
    
    Shows how conversations can continue across multiple interactions.
    """
    print("\n" + "="*70)
    print("🔄 DEMO 2: SESSION CONTINUITY")
    print("="*70)
    
    config = get_config()
    
    # Initialize
    observability = StructuredLogger(log_level="WARNING")
    llm_provider = OpenAIProvider(api_key=config.llm.openai_api_key)
    agent_repo = InMemoryAgentRepository()
    tool_registry = InMemoryToolRegistry()
    
    memory = ConversationMemory()
    
    agent = Agent(
        id=uuid4(),
        name="Tutor",
        description="A patient tutor",
        system_prompt="You are a helpful tutor. You remember what we've discussed and build on it.",
        model_provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=400,
    )
    await agent_repo.save(agent)
    
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
        agent_repository=agent_repo,
        observability=observability,
    )
    
    session_id = "tutoring_session"
    
    # Simulate a tutoring session with multiple exchanges
    conversation_pairs = [
        ("I'm learning about Python lists. Can you explain them?", "I'll explain lists..."),
        ("Can you give me an example?", "Here's an example..."),
        ("What's the difference between a list and a tuple?", "The key difference is..."),
    ]
    
    for turn, (user_input, _) in enumerate(conversation_pairs, 1):
        print(f"\n--- Turn {turn} ---")
        print(f"💬 User: {user_input}")
        
        # Get session history for context
        history = await memory.get_session_history(session_id, max_messages=10)
        
        # Build context from history
        context_str = ""
        if history:
            context_str = "Previous conversation:\\n"
            for entry in history[-6:]:  # Last 3 exchanges (6 messages)
                context_str += f"{entry.message.role.value}: {entry.message.content}\\n"
            context_str += f"\\nCurrent: {user_input}"
        else:
            context_str = user_input
        
        result = await orchestrator.execute_agent(
            agent=agent,
            user_input=context_str,
        )
        
        print(f"🤖 Tutor: {result.output[:100]}..." if len(result.output or "") > 100 else f"🤖 Tutor: {result.output}")
        
        # Store in memory
        await memory.store_message(
            agent.id,
            Message(role=MessageRole.USER, content=user_input),
            session_id=session_id,
        )
        await memory.store_message(
            agent.id,
            Message(role=MessageRole.ASSISTANT, content=result.output or ""),
            session_id=session_id,
        )
    
    # Show full session history
    print(f"\n📜 Full Session History ({len(await memory.get_session_history(session_id))} messages)")
    history = await memory.get_session_history(session_id)
    for idx, entry in enumerate(history, 1):
        role_emoji = "💬" if entry.message.role == MessageRole.USER else "🤖"
        preview = entry.message.content[:60] + "..." if len(entry.message.content) > 60 else entry.message.content
        print(f"   {idx}. {role_emoji} {preview}")


async def demo_importance_scoring():
    """
    Demo 3: Importance scoring.
    
    Shows how important messages are prioritized in retrieval.
    """
    print("\n" + "="*70)
    print("⭐ DEMO 3: IMPORTANCE SCORING")
    print("="*70)
    
    memory = ConversationMemory(config=MemoryConfig(enable_importance_weighting=True))
    
    agent_id = uuid4()
    session_id = "important_session"
    
    # Store messages with different importance scores
    messages_with_importance = [
        ("What's the weather?", 0.3),  # Low importance
        ("My password is abc123", 1.0),  # High importance - sensitive info
        ("I like pizza", 0.5),  # Medium importance
        ("Tell me a joke", 0.2),  # Low importance
        ("I'm allergic to peanuts", 1.0),  # High importance - critical info
        ("What time is it?", 0.2),  # Low importance
    ]
    
    print("\n📝 Storing messages with importance scores:")
    for content, importance in messages_with_importance:
        msg = Message(role=MessageRole.USER, content=content)
        await memory.store_message(
            agent_id=agent_id,
            message=msg,
            session_id=session_id,
            importance_score=importance,
        )
        stars = "⭐" * int(importance * 5)
        print(f"   {stars} ({importance}) - {content}")
    
    # Retrieve without semantic search (uses recency + importance)
    print(f"\n🔍 Retrieving important memories:")
    results = await memory.retrieve_relevant_context(
        agent_id=agent_id,
        query="Tell me about the user",
        session_id=session_id,
        max_results=3,
    )
    
    print(f"\nTop 3 memories (by recency + importance):")
    for result in results:
        print(f"   • {result.entry.message.content}")
        print(f"     Importance: {result.entry.importance_score}")


async def main():
    """Run all memory demos."""
    config = get_config()
    
    if not config.llm.openai_api_key:
        print("❌ Error: OPENAI_API_KEY not set in .env file")
        return
    
    print("\n" + "="*70)
    print("🧠 AGENT MEMORY SYSTEM DEMO")
    print("="*70)
    print("\nThis demo shows how agents can maintain conversational context")
    print("and remember facts across multiple interactions.")
    
    # Run demos
    await demo_basic_memory()
    await demo_session_continuity()
    await demo_importance_scoring()
    
    print("\n" + "="*70)
    print("✅ MEMORY DEMOS COMPLETE")
    print("="*70)
    print("\n🎯 Key Features Demonstrated:")
    print("   1. ✅ Context retention across turns")
    print("   2. ✅ Session-based conversation grouping")
    print("   3. ✅ Memory retrieval for relevant context")
    print("   4. ✅ Importance scoring for prioritization")
    print("\n💡 Next Steps:")
    print("   • Add embedding-based semantic search")
    print("   • Integrate with PostgreSQL for persistence")
    print("   • Add auto-summarization for long histories")
    print("   • Build memory visualization dashboard\n")


if __name__ == "__main__":
    asyncio.run(main())
