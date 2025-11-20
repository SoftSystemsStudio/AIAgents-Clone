"""
Rate Limiting Example - Preventing runaway costs.

Demonstrates how rate limiting protects against excessive API usage
and provides cost control.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rate_limiting import RateLimiter, RateLimitConfig, RateLimitError
from src.domain.models import Agent
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator
from src.config import get_config


async def main():
    """Demonstrate rate limiting."""
    config = get_config()
    
    if not config.llm.openai_api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        return
    
    print("=" * 80)
    print("🛡️  RATE LIMITING DEMO")
    print("=" * 80)
    print()
    
    # === Configure Rate Limiter ===
    print("⚙️  Configuring rate limiter...")
    rate_config = RateLimitConfig(
        max_requests_per_minute=5,  # Low for demo
        max_tokens_per_request=1000,
        max_tokens_per_minute=5000,
        max_cost_per_hour=0.50,  # $0.50 per hour
        max_cost_per_day=5.00,    # $5 per day
    )
    
    limiter = RateLimiter(rate_config)
    print("✅ Rate limiter configured")
    print()
    print("Limits:")
    print(f"  • Max requests/minute: {rate_config.max_requests_per_minute}")
    print(f"  • Max tokens/request: {rate_config.max_tokens_per_request}")
    print(f"  • Max cost/hour: ${rate_config.max_cost_per_hour}")
    print(f"  • Max cost/day: ${rate_config.max_cost_per_day}")
    print()
    
    # === Test Normal Usage ===
    print("📊 Test 1: Normal usage (within limits)")
    print("-" * 80)
    
    user_id = "demo_user"
    
    for i in range(3):
        try:
            await limiter.check_and_record(
                tokens=200,
                estimated_cost=0.01,
                user_id=user_id,
            )
            print(f"✅ Request {i+1}: Allowed (200 tokens, $0.01)")
        except RateLimitError as e:
            print(f"❌ Request {i+1}: {e}")
    
    # Show usage
    usage = limiter.get_usage(user_id)
    print()
    print("Current usage:")
    print(f"  • Requests (minute): {usage['minute']['requests']}/{usage['minute']['limit']}")
    print(f"  • Tokens (minute): {usage['minute']['tokens']}")
    print(f"  • Cost (hour): ${usage['hour']['cost']}")
    print()
    
    # === Test Rate Limit Exceeded ===
    print("📊 Test 2: Exceeding request limit")
    print("-" * 80)
    
    try:
        # Try to make more requests than allowed
        for i in range(5):
            await limiter.check_and_record(
                tokens=200,
                estimated_cost=0.01,
                user_id=user_id,
            )
            print(f"✅ Request {i+4}: Allowed")
    except RateLimitError as e:
        print(f"❌ Rate limit exceeded: {e}")
        print(f"   Limit type: {e.limit_type}")
        if e.retry_after:
            print(f"   Retry after: {e.retry_after} seconds")
    print()
    
    # === Test Token Limit ===
    print("📊 Test 3: Token limit exceeded")
    print("-" * 80)
    
    try:
        await limiter.check_and_record(
            tokens=5000,  # Exceeds per-request limit
            estimated_cost=0.05,
            user_id="another_user",
        )
        print("✅ Request allowed")
    except RateLimitError as e:
        print(f"❌ Token limit exceeded: {e}")
        print(f"   Limit type: {e.limit_type}")
    print()
    
    # === Test Cost Limit ===
    print("📊 Test 4: Cost limit protection")
    print("-" * 80)
    
    try:
        await limiter.check_and_record(
            tokens=500,
            estimated_cost=2.00,  # Exceeds per-request limit
            user_id="high_cost_user",
        )
        print("✅ Request allowed")
    except RateLimitError as e:
        print(f"❌ Cost limit exceeded: {e}")
        print(f"   Limit type: {e.limit_type}")
    print()
    
    # === Global Usage Stats ===
    print("📊 Global Usage Statistics")
    print("-" * 80)
    global_usage = limiter.get_global_usage()
    print(f"Minute: {global_usage['minute']['requests']} requests, "
          f"{global_usage['minute']['tokens']} tokens, ${global_usage['minute']['cost']}")
    print(f"Hour:   {global_usage['hour']['requests']} requests, "
          f"{global_usage['hour']['tokens']} tokens, ${global_usage['hour']['cost']}")
    print(f"Day:    {global_usage['day']['requests']} requests, "
          f"{global_usage['day']['tokens']} tokens, ${global_usage['day']['cost']}")
    print()
    
    # === Integration with Agent ===
    print("📊 Test 5: Rate-limited agent execution")
    print("-" * 80)
    
    # Create agent
    agent = Agent(
        name="Rate Limited Agent",
        description="Agent with rate limiting",
        system_prompt="You are a helpful assistant. Be concise.",
        model_provider="openai",
        model_name="gpt-4o-mini",
        max_tokens=100,  # Small for demo
    )
    
    # Setup
    llm_provider = OpenAIProvider(api_key=config.llm.openai_api_key)
    agent_repo = InMemoryAgentRepository()
    tool_registry = InMemoryToolRegistry()
    logger = StructuredLogger()
    
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        agent_repository=agent_repo,
        tool_registry=tool_registry,
        observability=logger,
    )
    
    await agent_repo.save(agent)
    
    # Execute with rate limit check
    print("Executing agent with rate limit check...")
    
    try:
        # Check rate limit before execution
        await limiter.check_and_record(
            tokens=100,  # Estimated
            estimated_cost=0.01,
            user_id="agent_user",
        )
        
        result = await orchestrator.execute_agent(
            agent=agent,
            user_input="What is 2+2?",
        )
        
        # Record actual usage
        await limiter.check_and_record(
            tokens=result.total_tokens,
            estimated_cost=result.estimated_cost,
            user_id="agent_user",
        )
        
        print(f"✅ Agent response: {result.output}")
        print(f"   Tokens: {result.total_tokens}, Cost: ${result.estimated_cost:.4f}")
        
    except RateLimitError as e:
        print(f"❌ Request blocked by rate limiter: {e}")
    
    print()
    
    # === Emergency Stop ===
    print("📊 Test 6: Emergency stop")
    print("-" * 80)
    
    print("Activating emergency stop...")
    limiter.activate_emergency_stop()
    
    try:
        await limiter.check_and_record(
            tokens=10,
            estimated_cost=0.001,
            user_id="any_user",
        )
        print("✅ Request allowed")
    except RateLimitError as e:
        print(f"❌ All requests blocked: {e}")
    
    print("Deactivating emergency stop...")
    limiter.deactivate_emergency_stop()
    print()
    
    # === Summary ===
    print("=" * 80)
    print("✅ RATE LIMITING DEMO COMPLETE")
    print("=" * 80)
    print()
    print("Benefits of Rate Limiting:")
    print("  ✓ Prevent runaway costs")
    print("  ✓ Per-user quotas")
    print("  ✓ Multiple time windows (minute, hour, day)")
    print("  ✓ Token and cost limits")
    print("  ✓ Emergency stop capability")
    print("  ✓ Burst allowance for flexibility")
    print()
    print("💡 Integration tips:")
    print("   - Check limits BEFORE making LLM calls")
    print("   - Record ACTUAL usage after execution")
    print("   - Monitor usage stats regularly")
    print("   - Set alerts for approaching limits")
    print("   - Use emergency stop for incidents")
    print()


if __name__ == "__main__":
    asyncio.run(main())
