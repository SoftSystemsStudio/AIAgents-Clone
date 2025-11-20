"""
Database Migration Script - Initialize PostgreSQL schema.

Creates tables and indexes for production deployment.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.db_repositories import Base, PostgreSQLAgentRepository
from src.config import get_config


async def run_migrations():
    """Run database migrations."""
    config = get_config()
    
    # Get database URL from config or environment
    database_url = config.database.url if hasattr(config, 'database') else None
    
    if not database_url:
        # Build from individual components
        database_url = (
            f"postgresql+asyncpg://"
            f"{config.database.user}:{config.database.password}@"
            f"{config.database.host}:{config.database.port}/"
            f"{config.database.name}"
        )
    
    print("🔄 Running database migrations...")
    print(f"📊 Database: {database_url.split('@')[1] if '@' in database_url else 'N/A'}")
    print()
    
    try:
        # Initialize repository (creates tables)
        repo = PostgreSQLAgentRepository(database_url)
        await repo.initialize()
        
        print("✅ Migration complete!")
        print()
        print("Created tables:")
        print("  - agents")
        print("  - messages")
        print()
        print("Created indexes:")
        print("  - idx_agent_status_created")
        print("  - idx_agent_provider_model")
        print("  - idx_message_agent_created")
        print("  - idx_message_role")
        print()
        
        await repo.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_migrations())
