#!/usr/bin/env python3
"""
Gmail Cleanup CLI - Command-line interface for scheduled cleanup runs.

Usage:
    python scripts/run_gmail_cleanup.py --user-id=user123 --dry-run
    python scripts/run_gmail_cleanup.py --user-id=user123 --policy-id=default
    python scripts/run_gmail_cleanup.py --user-id=user123 --quick
    python scripts/run_gmail_cleanup.py --user-id=user123 --analyze-only

Can be scheduled via cron:
    0 2 * * * /usr/bin/python3 /path/to/scripts/run_gmail_cleanup.py --user-id=user123
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.gmail_client import GmailClient
from src.application.services.inbox_hygiene_service import InboxHygieneService
from src.domain.cleanup_policy import CleanupPolicy


def setup_argparse() -> argparse.ArgumentParser:
    """Configure command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Gmail Cleanup CLI - Automated inbox hygiene",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze inbox without making changes
  %(prog)s --user-id=user123 --analyze-only

  # Preview what cleanup would do
  %(prog)s --user-id=user123 --dry-run

  # Execute quick cleanup (archive old promotions/social)
  %(prog)s --user-id=user123 --quick

  # Execute cleanup with custom policy
  %(prog)s --user-id=user123 --policy-id=aggressive

  # Execute cleanup with custom thresholds
  %(prog)s --user-id=user123 --archive-promotions --archive-social --old-days=14

Scheduling with cron:
  # Run daily at 2 AM
  0 2 * * * /usr/bin/python3 /path/to/scripts/run_gmail_cleanup.py --user-id=user123 --quick

  # Run weekly on Sundays at midnight
  0 0 * * 0 /usr/bin/python3 /path/to/scripts/run_gmail_cleanup.py --user-id=user123 --analyze-only
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--user-id',
        required=True,
        help='User identifier'
    )
    
    # Operation mode
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--analyze-only',
        action='store_true',
        help='Analyze inbox and show recommendations only'
    )
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview cleanup actions without executing'
    )
    mode_group.add_argument(
        '--quick',
        action='store_true',
        help='Quick cleanup with sensible defaults'
    )
    
    # Policy options
    parser.add_argument(
        '--policy-id',
        help='Custom policy ID (TODO: load from database)'
    )
    
    # Quick cleanup options
    parser.add_argument(
        '--archive-promotions',
        action='store_true',
        default=True,
        help='Archive old promotional emails (default: True)'
    )
    parser.add_argument(
        '--archive-social',
        action='store_true',
        default=True,
        help='Archive old social emails (default: True)'
    )
    parser.add_argument(
        '--old-days',
        type=int,
        default=30,
        help='Age threshold in days for archiving (default: 30)'
    )
    
    # Gmail credentials
    parser.add_argument(
        '--credentials',
        default='credentials.json',
        help='Path to Gmail OAuth credentials (default: credentials.json)'
    )
    
    # Processing limits
    parser.add_argument(
        '--max-threads',
        type=int,
        default=100,
        help='Maximum threads to process (default: 100)'
    )
    
    # Output options
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    return parser


def print_banner():
    """Print CLI banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              📧  Gmail Cleanup CLI  📧                       ║
║                                                              ║
║          Automated Inbox Hygiene for Busy Professionals     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_analysis(analysis: dict, verbose: bool = False):
    """Print analysis results in human-readable format."""
    print(f"\n📊 Inbox Analysis for {analysis['user_id']}")
    print("=" * 70)
    
    snapshot = analysis.get('snapshot', {})
    print(f"\n📬 Mailbox Overview:")
    print(f"   Total Threads: {snapshot.get('total_threads', 0):,}")
    print(f"   Total Messages: {snapshot.get('total_messages', 0):,}")
    print(f"   Size: {snapshot.get('size_mb', 0):.2f} MB")
    
    health = analysis.get('health_score', 0)
    health_emoji = "🟢" if health >= 80 else "🟡" if health >= 60 else "🔴"
    print(f"\n{health_emoji} Health Score: {health:.1f}/100")
    
    recs = analysis.get('recommendations', {})
    if recs:
        print(f"\n💡 Recommendations:")
        print(f"   Threads Affected: {recs.get('total_threads_affected', 0):,}")
        print(f"   Total Actions: {recs.get('total_actions', 0):,}")
        
        actions_by_type = recs.get('actions_by_type', {})
        if actions_by_type:
            print(f"\n   Actions Breakdown:")
            for action, count in actions_by_type.items():
                print(f"      • {action}: {count:,}")
        
        if verbose and recs.get('threads'):
            print(f"\n   Sample Affected Threads:")
            for thread in recs['threads'][:5]:
                print(f"      • {thread['subject'][:50]}: {thread['total_actions']} actions")
    
    print()


def print_cleanup_summary(result: dict):
    """Print cleanup execution summary."""
    print(f"\n✅ Cleanup Complete")
    print("=" * 70)
    
    print(f"\n📈 Execution Summary:")
    print(f"   Run ID: {result.get('run_id', 'unknown')}")
    print(f"   Status: {result.get('status', 'unknown')}")
    print(f"   Duration: {result.get('duration_seconds', 0):.1f}s")
    
    actions = result.get('actions', {})
    print(f"\n🎯 Actions:")
    print(f"   Total: {actions.get('total', 0):,}")
    print(f"   Successful: {actions.get('successful', 0):,}")
    print(f"   Failed: {actions.get('failed', 0):,}")
    print(f"   Skipped: {actions.get('skipped', 0):,}")
    
    actions_by_type = actions.get('by_type', {})
    if actions_by_type:
        print(f"\n   By Type:")
        for action_type, count in actions_by_type.items():
            print(f"      • {action_type}: {count:,}")
    
    outcomes = result.get('outcomes', {})
    print(f"\n📦 Outcomes:")
    print(f"   Emails Deleted: {outcomes.get('emails_deleted', 0):,}")
    print(f"   Emails Archived: {outcomes.get('emails_archived', 0):,}")
    print(f"   Emails Labeled: {outcomes.get('emails_labeled', 0):,}")
    
    if 'storage_freed_mb' in result:
        print(f"   Storage Freed: {result['storage_freed_mb']:.2f} MB")
    
    if result.get('error'):
        print(f"\n⚠️  Error: {result['error']}")
    
    print()


async def main():
    """Main CLI entry point."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if not args.json:
        print_banner()
    
    try:
        # Initialize Gmail client
        if args.verbose:
            print(f"🔐 Initializing Gmail client (credentials: {args.credentials})...")
        
        gmail = GmailClient(credentials_path=args.credentials)
        service = InboxHygieneService(gmail)
        
        # Determine operation mode
        if args.analyze_only:
            if args.verbose:
                print(f"📊 Analyzing inbox for {args.user_id}...")
            
            analysis = service.analyze_inbox(
                user_id=args.user_id,
                max_threads=args.max_threads,
            )
            
            if args.json:
                import json
                print(json.dumps(analysis, indent=2))
            else:
                print_analysis(analysis, verbose=args.verbose)
        
        elif args.dry_run:
            if args.verbose:
                print(f"🔍 Previewing cleanup for {args.user_id}...")
            
            result = service.preview_cleanup(
                user_id=args.user_id,
                max_threads=args.max_threads,
            )
            
            if args.json:
                import json
                print(json.dumps(result, indent=2))
            else:
                print_cleanup_summary(result)
                print("ℹ️  This was a dry run - no actions were executed")
        
        elif args.quick:
            if args.verbose:
                print(f"⚡ Running quick cleanup for {args.user_id}...")
            
            result = service.quick_cleanup(
                user_id=args.user_id,
                auto_archive_promotions=args.archive_promotions,
                auto_archive_social=args.archive_social,
                old_threshold_days=args.old_days,
            )
            
            if args.json:
                import json
                print(json.dumps(result, indent=2))
            else:
                print_cleanup_summary(result)
        
        else:
            # Full cleanup execution
            if args.verbose:
                print(f"🚀 Executing cleanup for {args.user_id}...")
            
            result = service.execute_cleanup(
                user_id=args.user_id,
                max_threads=args.max_threads,
            )
            
            if args.json:
                import json
                print(json.dumps(result, indent=2))
            else:
                print_cleanup_summary(result)
        
        if not args.json:
            print(f"✨ Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0
    
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        print("\nFollow Gmail setup instructions in docs/GMAIL_SETUP.md", file=sys.stderr)
        return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user", file=sys.stderr)
        return 130
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
