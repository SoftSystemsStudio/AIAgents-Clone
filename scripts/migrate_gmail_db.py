#!/usr/bin/env python3
"""
Database migration script for Gmail Cleanup persistence.

Creates PostgreSQL schema for storing policies, runs, and actions.
"""
import asyncio
import argparse
import os
import sys

try:
    import asyncpg
except ImportError:
    print("Error: asyncpg not installed. Install with: pip install asyncpg")
    sys.exit(1)


# Database schema
SCHEMA_SQL = """
-- Cleanup policies table
CREATE TABLE IF NOT EXISTS cleanup_policies (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    rules JSONB NOT NULL,
    retention JSONB,
    dry_run BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    CONSTRAINT uk_user_policy UNIQUE(user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_policies_user 
ON cleanup_policies(user_id);

CREATE INDEX IF NOT EXISTS idx_policies_created 
ON cleanup_policies(user_id, created_at DESC);

-- Cleanup runs table
CREATE TABLE IF NOT EXISTS cleanup_runs (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    error_message TEXT,
    dry_run BOOLEAN DEFAULT FALSE,
    
    -- Metrics
    emails_deleted INTEGER DEFAULT 0,
    emails_archived INTEGER DEFAULT 0,
    emails_labeled INTEGER DEFAULT 0,
    actions_successful INTEGER DEFAULT 0,
    actions_failed INTEGER DEFAULT 0,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_user 
ON cleanup_runs(user_id);

CREATE INDEX IF NOT EXISTS idx_runs_status 
ON cleanup_runs(user_id, status);

CREATE INDEX IF NOT EXISTS idx_runs_started 
ON cleanup_runs(user_id, started_at DESC);

-- Cleanup actions table
CREATE TABLE IF NOT EXISTS cleanup_actions (
    id VARCHAR(255) PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL REFERENCES cleanup_runs(id) ON DELETE CASCADE,
    thread_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actions_run 
ON cleanup_actions(run_id);

CREATE INDEX IF NOT EXISTS idx_actions_status 
ON cleanup_actions(run_id, status);

-- Materialized view for run statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS run_statistics AS
SELECT 
    user_id,
    DATE_TRUNC('day', started_at) as run_date,
    COUNT(*) as total_runs,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_runs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
    SUM(emails_deleted) as total_deleted,
    SUM(emails_archived) as total_archived,
    AVG(duration_seconds) as avg_duration_seconds
FROM cleanup_runs
GROUP BY user_id, DATE_TRUNC('day', started_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_run_stats_user_date 
ON run_statistics(user_id, run_date);
"""


async def create_schema(connection_string: str) -> None:
    """Create database schema."""
    print(f"Connecting to database...")
    conn = await asyncpg.connect(connection_string)
    
    try:
        print("Creating schema...")
        await conn.execute(SCHEMA_SQL)
        print("✅ Schema created successfully!")
        
        # Verify tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('cleanup_policies', 'cleanup_runs', 'cleanup_actions')
            ORDER BY tablename
        """)
        
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table['tablename']}")
        
    finally:
        await conn.close()


async def drop_schema(connection_string: str) -> None:
    """Drop database schema (use with caution!)."""
    print(f"Connecting to database...")
    conn = await asyncpg.connect(connection_string)
    
    try:
        print("⚠️  WARNING: This will delete all Gmail cleanup data!")
        confirmation = input("Type 'DELETE' to confirm: ")
        
        if confirmation != "DELETE":
            print("Aborted.")
            return
        
        print("Dropping schema...")
        await conn.execute("""
            DROP MATERIALIZED VIEW IF EXISTS run_statistics;
            DROP TABLE IF EXISTS cleanup_actions CASCADE;
            DROP TABLE IF EXISTS cleanup_runs CASCADE;
            DROP TABLE IF EXISTS cleanup_policies CASCADE;
        """)
        print("✅ Schema dropped successfully!")
        
    finally:
        await conn.close()


async def verify_schema(connection_string: str) -> None:
    """Verify schema exists and is correct."""
    print(f"Connecting to database...")
    conn = await asyncpg.connect(connection_string)
    
    try:
        # Check tables
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('cleanup_policies', 'cleanup_runs', 'cleanup_actions')
        """)
        
        print("\nTables:")
        for table in tables:
            # Get row count
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table['tablename']}")
            print(f"  ✓ {table['tablename']}: {count} rows")
        
        # Check indexes
        indexes = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
            ORDER BY indexname
        """)
        
        print(f"\nIndexes: {len(indexes)}")
        for idx in indexes:
            print(f"  ✓ {idx['indexname']}")
        
        # Check materialized view
        views = await conn.fetch("""
            SELECT matviewname 
            FROM pg_matviews 
            WHERE schemaname = 'public'
        """)
        
        if views:
            print(f"\nMaterialized Views:")
            for view in views:
                print(f"  ✓ {view['matviewname']}")
        
        print("\n✅ Schema verification complete!")
        
    finally:
        await conn.close()


async def refresh_stats(connection_string: str) -> None:
    """Refresh materialized view statistics."""
    print(f"Connecting to database...")
    conn = await asyncpg.connect(connection_string)
    
    try:
        print("Refreshing statistics...")
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY run_statistics")
        
        # Show recent stats
        stats = await conn.fetch("""
            SELECT * FROM run_statistics 
            ORDER BY run_date DESC 
            LIMIT 10
        """)
        
        if stats:
            print("\nRecent statistics:")
            for stat in stats:
                print(f"  {stat['run_date']}: {stat['total_runs']} runs, "
                      f"{stat['total_deleted']} deleted, {stat['total_archived']} archived")
        
        print("✅ Statistics refreshed!")
        
    finally:
        await conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Gmail Cleanup Database Migration")
    parser.add_argument(
        "command",
        choices=["create", "drop", "verify", "refresh"],
        help="Migration command"
    )
    parser.add_argument(
        "--connection-string",
        default=os.getenv("DATABASE_URL", "postgresql://localhost/gmail_cleanup"),
        help="PostgreSQL connection string (default: from DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    print(f"\nGmail Cleanup Database Migration")
    print(f"Command: {args.command}")
    print(f"Database: {args.connection_string}\n")
    
    try:
        if args.command == "create":
            asyncio.run(create_schema(args.connection_string))
        elif args.command == "drop":
            asyncio.run(drop_schema(args.connection_string))
        elif args.command == "verify":
            asyncio.run(verify_schema(args.connection_string))
        elif args.command == "refresh":
            asyncio.run(refresh_stats(args.connection_string))
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
