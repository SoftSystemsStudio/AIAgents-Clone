"""
Gmail Cleanup Agent - Intelligent email management assistant.

This agent can:
- Analyze your inbox and identify cleanup opportunities
- Delete emails from specific senders (promotions, notifications)
- Archive old emails
- Unsubscribe from mailing lists
- Organize emails with smart filtering

Setup:
1. Enable Gmail API in Google Cloud Console
2. Download credentials.json to project root
3. First run will open browser for OAuth authentication
4. Agent will have access to read, modify, and delete emails
"""

import asyncio
from uuid import uuid4

from src.config import get_config
from src.domain.models import Agent, AgentCapability
from src.infrastructure.llm_providers import OpenAIProvider
from src.infrastructure.repositories import InMemoryAgentRepository, InMemoryToolRegistry
from src.infrastructure.observability import StructuredLogger
from src.application.orchestrator import AgentOrchestrator
from src.tools.gmail import create_gmail_tools


async def create_gmail_cleanup_agent(
    credentials_path: str = 'credentials.json',
) -> tuple[Agent, AgentOrchestrator]:
    """
    Create a Gmail cleanup agent with email management tools.
    
    Args:
        credentials_path: Path to Gmail OAuth credentials
        
    Returns:
        Tuple of (agent, orchestrator)
    """
    config = get_config()
    
    if not config.llm.openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in .env file")
    
    # Initialize components
    observability = StructuredLogger(log_level="INFO")
    llm_provider = OpenAIProvider(api_key=config.llm.openai_api_key)
    agent_repo = InMemoryAgentRepository()
    tool_registry = InMemoryToolRegistry()
    
    # Register Gmail tools
    gmail_tools = create_gmail_tools(credentials_path)
    for tool in gmail_tools:
        await tool_registry.register(tool)
    
    # Create agent
    agent = Agent(
        id=uuid4(),
        name="Gmail Cleanup Assistant",
        description="Intelligent email management assistant that can analyze, organize, and clean up your Gmail inbox",
        system_prompt="""You are a helpful Gmail cleanup assistant. You can:

1. ANALYZE the inbox to identify:
   - Unread emails that need attention
   - Promotional emails taking up space
   - Old emails that can be archived/deleted
   - Emails from specific senders to bulk delete

2. CLEANUP operations:
   - Delete emails by sender (promotions, notifications, etc.)
   - Delete old emails (specify how many days old)
   - Archive emails to keep them but clear inbox
   - Search and delete specific types of emails

3. BEST PRACTICES:
   - Always list emails FIRST before deleting
   - Ask for confirmation on bulk deletions
   - Start with small batches (50-100 emails)
   - Suggest archiving instead of deleting when appropriate

When user asks to clean inbox:
1. First use list_emails to show what's there
2. Identify patterns (senders, age, types)
3. Suggest cleanup actions
4. Execute with user's approval

Be helpful, cautious with deletions, and explain what you're doing.""",
        model_provider="openai",
        model_name="gpt-4o",
        temperature=0.3,
        max_tokens=2000,
        capabilities=[AgentCapability.CODE_EXECUTION],
        allowed_tools=[
            "list_emails",
            "delete_emails_by_sender",
            "delete_old_emails",
            "archive_emails_by_sender",
            "search_and_delete",
        ],
        max_iterations=10,
    )
    
    await agent_repo.save(agent)
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
        agent_repository=agent_repo,
        observability=observability,
    )
    
    return agent, orchestrator


async def interactive_cleanup():
    """Interactive Gmail cleanup session."""
    print("\n" + "="*70)
    print("📧 GMAIL CLEANUP ASSISTANT")
    print("="*70)
    print("\n⚠️  SETUP REQUIRED:")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create project & enable Gmail API")
    print("3. Create OAuth 2.0 credentials (Desktop app)")
    print("4. Download as 'credentials.json' in project root")
    print("\n🔐 First run will open browser for authentication")
    print("="*70)
    
    # Check for credentials
    import os
    if not os.path.exists('credentials.json'):
        print("\n❌ credentials.json not found!")
        print("\nFollow setup instructions above, then run again.")
        return
    
    try:
        agent, orchestrator = await create_gmail_cleanup_agent()
        print("\n✅ Agent initialized with Gmail access!")
        print("\n💡 Example commands:")
        print("   • 'Show me my unread emails'")
        print("   • 'Delete all emails from notifications@linkedin.com'")
        print("   • 'Clean up emails older than 90 days'")
        print("   • 'Archive all promotional emails'")
        print("   • 'Help me organize my inbox'")
        
        print("\n" + "-"*70)
        
        # Interactive loop
        while True:
            print("\n📨 What would you like to do? (or 'quit' to exit)")
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Your inbox is cleaner now.")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 Agent working...\n")
            
            # Execute agent
            result = await orchestrator.execute_agent(
                agent=agent,
                user_input=user_input,
            )
            
            if result.success:
                print(f"🤖 Assistant: {result.output}\n")
                print(f"⏱️  {result.duration_seconds:.1f}s | {result.total_tokens} tokens | ${result.estimated_cost:.4f}")
            else:
                print(f"❌ Error: {result.error}")
    
    except FileNotFoundError as e:
        print(f"\n❌ {str(e)}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


async def demo_cleanup():
    """Demo Gmail cleanup with sample commands."""
    print("\n" + "="*70)
    print("📧 GMAIL CLEANUP DEMO")
    print("="*70)
    
    try:
        agent, orchestrator = await create_gmail_cleanup_agent()
        
        # Demo commands
        commands = [
            "Show me my unread emails",
            "What are the most common senders in my inbox?",
            "Help me clean up promotional emails",
        ]
        
        for cmd in commands:
            print(f"\n💬 User: {cmd}")
            print("🤖 Agent working...\n")
            
            result = await orchestrator.execute_agent(
                agent=agent,
                user_input=cmd,
            )
            
            if result.success:
                output = result.output[:500] + "..." if len(result.output or "") > 500 else result.output
                print(f"🤖 Assistant: {output}\n")
                print(f"⏱️  {result.duration_seconds:.1f}s | {result.total_tokens} tokens")
            else:
                print(f"❌ Error: {result.error}")
            
            await asyncio.sleep(1)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        await demo_cleanup()
    else:
        await interactive_cleanup()


if __name__ == "__main__":
    asyncio.run(main())
