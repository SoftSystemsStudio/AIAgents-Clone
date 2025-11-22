"""
Gmail Cleanup Agent - Reference Implementation

This is a REFERENCE IMPLEMENTATION showing how to use the Gmail cleanup solution.

The actual business logic lives in:
- src/domain/gmail_interfaces.py (contracts)
- src/application/gmail_cleanup_use_cases.py (orchestration)
- src/infrastructure/gmail_client.py (Gmail API adapter)

This file demonstrates:
- How to wire up dependencies
- How to use the fluent builder API
- How to execute cleanup operations
- Interactive agent-style workflows (optional)

For production CLI usage, see: run_gmail_agent.sh
For API endpoints, see: src/api/gmail_cleanup.py (future)

Setup:
1. Follow docs/GMAIL_SETUP.md for OAuth credentials
2. Run this example: python -m examples.gmail_cleanup_agent
3. Or use production CLI: ./run_gmail_agent.sh --dry-run
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from application.gmail_cleanup_use_cases import (
    AnalyzeInboxUseCase,
    DryRunCleanupUseCase,
    ExecuteCleanupUseCase,
)
from infrastructure.gmail_client import GmailClient
from infrastructure.gmail_persistence import InMemoryGmailCleanupRepository
from infrastructure.gmail_observability import GmailCleanupObservability
from infrastructure.observability import ObservabilityProvider
from domain.cleanup_policy import CleanupPolicy
from domain.cleanup_rule_builder import CleanupRuleBuilder


def demo_basic_usage():
    """Demonstrate basic Gmail cleanup usage."""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║        Gmail Cleanup - Reference Implementation            ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    print("This example demonstrates how to use the Gmail cleanup")
    print("solution modules.")
    print("")
    
    # 1. Initialize dependencies (dependency injection)
    print("1️⃣  Initializing components...")
    gmail_client = GmailClient(
        credentials_path='credentials.json',
        token_path='token.pickle'
    )
    repository = InMemoryGmailCleanupRepository()
    observability = GmailCleanupObservability(ObservabilityProvider())
    print("   ✅ Gmail client, repository, and observability initialized")
    print("")
    
    # 2. Get user email
    profile = gmail_client.get_profile()
    user_id = profile.get('emailAddress', 'unknown')
    print(f"2️⃣  Connected to Gmail: {user_id}")
    print("")
    
    # 3. Create cleanup policy using fluent builder
    print("3️⃣  Building cleanup policy...")
    policy = (
        CleanupRuleBuilder()
        .archive_if_category("promotions")
        .archive_if_older_than_days(90)
        .never_touch_starred()
        .never_touch_important()
        .build()
    )
    print(f"   ✅ Policy created: {policy.name}")
    print(f"      Rules: {len(policy.rules)}")
    print("")
    
    # 4. Analyze inbox (read-only)
    print("4️⃣  Analyzing inbox...")
    analyze_use_case = AnalyzeInboxUseCase(gmail_client, observability)
    analysis = analyze_use_case.execute(
        user_id=user_id,
        policy=policy,
        max_threads=50,
    )
    print(f"   ✅ Analysis complete")
    print(f"      Threads analyzed: {analysis['snapshot']['total_threads']}")
    print(f"      Actions recommended: {analysis['recommendations']['total_actions']}")
    print(f"      Mailbox health: {analysis['health_score']:.1f}/100")
    print("")
    
    # 5. Dry run (preview actions)
    print("5️⃣  Running dry run (preview)...")
    dry_run_use_case = DryRunCleanupUseCase(gmail_client, observability)
    dry_run = dry_run_use_case.execute(
        user_id=user_id,
        policy=policy,
        max_threads=50,
    )
    print(f"   ✅ Dry run complete")
    print(f"      Run ID: {dry_run.id}")
    print(f"      Actions planned: {len(dry_run.actions)}")
    print("")
    
    # Show action breakdown
    summary = dry_run.get_summary()
    actions_by_type = summary.get('actions_by_type', {})
    if actions_by_type:
        print("   Action breakdown:")
        for action_type, count in actions_by_type.items():
            print(f"     • {action_type}: {count}")
        print("")
    
    # 6. Execute cleanup (optional - commented out for safety)
    print("6️⃣  Ready to execute...")
    print("   ⚠️  Uncomment the code below to actually execute cleanup")
    print("   ⚠️  This will modify your Gmail!")
    print("")
    print("   # execute_use_case = ExecuteCleanupUseCase(")
    print("   #     gmail_client=gmail_client,")
    print("   #     repository=repository,")
    print("   #     observability=observability,")
    print("   # )")
    print("   # result = execute_use_case.execute(")
    print("   #     user_id=user_id,")
    print("   #     policy=policy,")
    print("   #     max_threads=50,")
    print("   #     dry_run=False,  # Set to False to execute")
    print("   # )")
    print("")
    
    # Uncomment to execute:
    # execute_use_case = ExecuteCleanupUseCase(
    #     gmail_client=gmail_client,
    #     repository=repository,
    #     observability=observability,
    # )
    # result = execute_use_case.execute(
    #     user_id=user_id,
    #     policy=policy,
    #     max_threads=50,
    #     dry_run=False,
    # )
    # print(f"✅ Cleanup complete!")
    # print(f"   Actions performed: {len(result.actions)}")
    # print(f"   Successful: {result.actions_successful}")
    # print(f"   Failed: {result.actions_failed}")
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║   ✅ Demo complete! Check the code to see how it works    ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")
    print("For production usage:")
    print("  ./run_gmail_agent.sh --dry-run")
    print("  ./run_gmail_agent.sh --execute --policy moderate")
    print("")


def demo_fluent_builder():
    """Demonstrate the fluent builder API for creating policies."""
    print("Fluent Builder API Demo")
    print("=" * 60)
    print("")
    
    # Conservative policy
    print("Conservative Policy:")
    policy = (
        CleanupRuleBuilder()
        .archive_if_category("promotions")
        .archive_if_older_than_days(90)
        .never_touch_starred()
        .build()
    )
    print(f"  {policy.name}: {len(policy.rules)} rules")
    print("")
    
    # Moderate policy  
    print("Moderate Policy:")
    policy = (
        CleanupRuleBuilder()
        .archive_if_category("promotions")
        .archive_if_category("social")
        .archive_if_older_than_days(60)
        .delete_if_older_than_days(180)
        .never_touch_starred()
        .never_touch_important()
        .build()
    )
    print(f"  {policy.name}: {len(policy.rules)} rules")
    print("")
    
    # Aggressive policy
    print("Aggressive Policy:")
    policy = (
        CleanupRuleBuilder()
        .archive_if_category("promotions")
        .archive_if_category("social")
        .archive_if_category("updates")
        .archive_if_older_than_days(30)
        .delete_if_older_than_days(90)
        .mark_read_if_category("forums")
        .never_touch_starred()
        .never_touch_important()
        .build()
    )
    print(f"  {policy.name}: {len(policy.rules)} rules")
    print("")


def demo_custom_policy():
    """Demonstrate creating custom policies for specific needs."""
    print("Custom Policy Demo")
    print("=" * 60)
    print("")
    
    # Custom policy for a specific sender
    print("Example: Clean up newsletters from specific sender")
    policy = (
        CleanupRuleBuilder()
        .archive_if_sender("@newsletters.example.com")
        .archive_if_older_than_days(30)
        .never_touch_starred()
        .build()
    )
    print(f"  {policy.name}")
    for i, rule in enumerate(policy.rules, 1):
        print(f"    {i}. {rule.name}: {rule.description}")
    print("")


if __name__ == "__main__":
    """
    Run the Gmail cleanup reference implementation.
    
    Choose which demo to run:
    """
    import sys
    
    if len(sys.argv) > 1:
        demo_type = sys.argv[1]
    else:
        demo_type = "basic"
    
    try:
        if demo_type == "basic":
            demo_basic_usage()
        elif demo_type == "builder":
            demo_fluent_builder()
        elif demo_type == "custom":
            demo_custom_policy()
        else:
            print(f"Unknown demo type: {demo_type}")
            print("")
            print("Usage: python -m examples.gmail_cleanup_agent [demo_type]")
            print("")
            print("Demo types:")
            print("  basic   - Full usage demo with all use cases (default)")
            print("  builder - Fluent builder API examples")
            print("  custom  - Custom policy creation examples")
            sys.exit(1)
    except Exception as e:
        print(f"")
        print(f"❌ Error: {e}")
        print(f"")
        print(f"Make sure you have:")
        print(f"  1. Followed docs/GMAIL_SETUP.md for OAuth setup")
        print(f"  2. credentials.json in project root")
        print(f"  3. Completed OAuth flow (token.pickle created)")
        print(f"")
        sys.exit(1)


"""
Legacy agent-style implementation below for reference.
This shows how to integrate Gmail cleanup with the platform's
agent orchestration layer if you want interactive chat-style workflows.

Instructions for agent:
When user asks to clean inbox:
1. First use list_emails to show what's there
2. Identify patterns (senders, age, types)
3. Suggest cleanup actions
4. Execute with user's approval

Be helpful, cautious with deletions, and explain what you're doing.
"""

# Legacy code commented out - use direct Gmail API calls instead (see main() above)
# async def create_gmail_cleanup_agent():
#     return AgentConfig(
#         agent_id="gmail-cleanup-assistant",
#         name="Gmail Cleanup Assistant",
#         instructions=instructions,
#         model_provider="openai",
#         model_name="gpt-4o-mini",  # Fast, cost-effective model for email management
#         temperature=0.3,
#         max_tokens=2000,
#         capabilities=[AgentCapability.CODE_EXECUTION],
#         allowed_tools=[
#             "list_emails",
#             "delete_emails_by_sender",
#             "delete_old_emails",
#             "archive_emails_by_sender",
#             "search_and_delete",
#         ],
#         max_iterations=10,
#     )
#     
#     await agent_repo.save(agent)
#     
#     # Create orchestrator
#     orchestrator = AgentOrchestrator(
#         llm_provider=llm_provider,
#         tool_registry=tool_registry,
#         agent_repository=agent_repo,
#         observability=observability,
#     )
#     
#     return agent, orchestrator
# 
# 
# async def interactive_cleanup():
#     """Interactive Gmail cleanup session."""
#     print("\n" + "="*70)
#     print("📧 GMAIL CLEANUP ASSISTANT")
#     print("="*70)
#     print("\n⚠️  SETUP REQUIRED:")
#     print("1. Go to: https://console.cloud.google.com/")
#     print("2. Create project & enable Gmail API")
#     print("3. Create OAuth 2.0 credentials (Desktop app)")
#     print("4. Download as 'credentials.json' in project root")
#     print("\n🔐 First run will open browser for authentication")
#     print("="*70)
#     
#     # Check for credentials
#     import os
#     if not os.path.exists('credentials.json'):
#         print("\n❌ credentials.json not found!")
#         print("\nFollow setup instructions above, then run again.")
#         return
#     
#     try:
#         agent, orchestrator = await create_gmail_cleanup_agent()
#         print("\n✅ Agent initialized with Gmail access!")
#         print("\n💡 Example commands:")
#         print("   • 'Show me my unread emails'")
#         print("   • 'Delete all emails from notifications@linkedin.com'")
#         print("   • 'Clean up emails older than 90 days'")
#         print("   • 'Archive all promotional emails'")
#         print("   • 'Help me organize my inbox'")
#         
#         print("\n" + "-"*70)
#         
#         # Interactive loop
#         while True:
#             print("\n📨 What would you like to do? (or 'quit' to exit)")
#             user_input = input("You: ").strip()
#             
#             if user_input.lower() in ['quit', 'exit', 'q']:
#                 print("\n👋 Goodbye! Your inbox is cleaner now.")
#                 break
#             
#             if not user_input:
#                 continue
#             
#             print("\n🤖 Agent working...\n")
#             
#             # Execute agent
#             try:
#                 result = await orchestrator.execute_agent(
#                     agent=agent,
#                     user_input=user_input,
#                 )
#                 
#                 if result.success:
#                     print(f"🤖 Assistant: {result.output}\n")
#                     print(f"⏱️  {result.duration_seconds:.1f}s | {result.total_tokens} tokens | ${result.estimated_cost:.4f}")
#                 else:
#                     print(f"❌ Error: {result.error}")
#                     if result.metadata:
#                         print(f"   Details: {result.metadata}")
#             except Exception as e:
#                 print(f"❌ Error executing agent: {type(e).__name__}: {str(e)}")
#                 # Print the full traceback for debugging
#                 import traceback
#                 print("\nFull error traceback:")
#                 traceback.print_exc()
#     
#     except FileNotFoundError as e:
#         print(f"\n❌ {str(e)}")
#     except Exception as e:
#         print(f"\n❌ Error: {str(e)}")
# 
# 
# async def demo_cleanup():
#     """Demo Gmail cleanup with sample commands."""
#     print("\n" + "="*70)
#     print("📧 GMAIL CLEANUP DEMO")
#     print("="*70)
#     
#     try:
#         agent, orchestrator = await create_gmail_cleanup_agent()
#         
#         # Demo commands
#         commands = [
#             "Show me my unread emails",
#             "What are the most common senders in my inbox?",
#             "Help me clean up promotional emails",
#         ]
#         
#         for cmd in commands:
#             print(f"\n💬 User: {cmd}")
#             print("🤖 Agent working...\n")
#             
#             result = await orchestrator.execute_agent(
#                 agent=agent,
#                 user_input=cmd,
#             )
#             
#             if result.success:
#                 output = result.output[:500] + "..." if len(result.output or "") > 500 else result.output
#                 print(f"🤖 Assistant: {output}\n")
#                 print(f"⏱️  {result.duration_seconds:.1f}s | {result.total_tokens} tokens")
#             else:
#                 print(f"❌ Error: {result.error}")
#             
#             await asyncio.sleep(1)
#     
#     except Exception as e:
#         print(f"\n❌ Error: {str(e)}")
# 
# 
# async def main():
#     """Main entry point."""
#     import sys
#     
#     if len(sys.argv) > 1 and sys.argv[1] == 'demo':
#         await demo_cleanup()
#     else:
#         await interactive_cleanup()
# 
# 
# if __name__ == "__main__":
#     asyncio.run(main())
