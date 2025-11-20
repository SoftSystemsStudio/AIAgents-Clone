"""
Agent Templates Example - Using pre-built agent configurations.

Demonstrates how to quickly create specialized agents using templates.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.templates import (
    list_templates,
    create_agent_from_template,
    describe_template,
)
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator
from src.config import get_config


async def main():
    """Demonstrate agent templates."""
    config = get_config()
    
    if not config.llm.openai_api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        return
    
    print("=" * 80)
    print("🤖 AGENT TEMPLATES DEMO")
    print("=" * 80)
    print()
    
    # === List Available Templates ===
    print("📚 Available Agent Templates:")
    print("-" * 80)
    templates = list_templates()
    for i, template_name in enumerate(templates, 1):
        template_display = template_name.replace("_", " ").title()
        print(f"   {i}. {template_display}")
    print()
    
    # === Show Template Details ===
    print("📝 Template Details:")
    print("-" * 80)
    print(describe_template("code_reviewer"))
    print()
    
    # === Create Agent from Template ===
    print("🔧 Creating Code Reviewer agent from template...")
    code_reviewer = create_agent_from_template("code_reviewer")
    print(f"✅ Created: {code_reviewer.name}")
    print(f"   Model: {code_reviewer.model_name}")
    print(f"   Temperature: {code_reviewer.temperature}")
    print(f"   Tools: {code_reviewer.allowed_tools}")
    print()
    
    # === Initialize Dependencies ===
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
    
    await agent_repo.save(code_reviewer)
    
    # === Test Code Reviewer ===
    print("💬 Testing Code Reviewer:")
    print("-" * 80)
    
    code_sample = '''
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item['price'] * item['quantity']
    return total
'''
    
    result = await orchestrator.execute_agent(
        agent=code_reviewer,
        user_input=f"Please review this Python function:\n\n{code_sample}",
    )
    
    print(f"🤖 Review:\n{result.output}")
    print()
    print(f"📊 Tokens: {result.total_tokens}, Cost: ${result.estimated_cost:.4f}")
    print()
    
    # === Try SQL Generator ===
    print("=" * 80)
    print("🔧 Creating SQL Generator agent...")
    sql_agent = create_agent_from_template("sql_generator", custom_name="My SQL Helper")
    await agent_repo.save(sql_agent)
    print(f"✅ Created: {sql_agent.name}")
    print()
    
    print("💬 Testing SQL Generator:")
    print("-" * 80)
    result2 = await orchestrator.execute_agent(
        agent=sql_agent,
        user_input="Write a query to find the top 10 customers by total purchase amount from orders and customers tables.",
    )
    
    print(f"🤖 SQL Query:\n{result2.output}")
    print()
    print(f"📊 Tokens: {result2.total_tokens}, Cost: ${result2.estimated_cost:.4f}")
    print()
    
    # === Summary ===
    print("=" * 80)
    print("✅ AGENT TEMPLATES DEMO COMPLETE")
    print("=" * 80)
    print()
    print("Benefits of Agent Templates:")
    print("  ✓ Instant agent creation - no prompt engineering needed")
    print("  ✓ Pre-optimized configurations (temperature, tokens, model)")
    print("  ✓ Best practices built-in")
    print("  ✓ Consistent agent behavior")
    print("  ✓ Easy customization when needed")
    print()
    print("💡 Try other templates:")
    print("   - data_analyst: Analyze CSV/JSON data")
    print("   - research_assistant: Research and summarize topics")
    print("   - documentation_writer: Generate docs from code")
    print("   - customer_support: Empathetic customer service")
    print()


if __name__ == "__main__":
    asyncio.run(main())
