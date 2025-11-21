"""
Persistence Layer for Gmail Cleanup - Database storage.

Stores cleanup policies, runs, and audit trails.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import asyncio
import uuid

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None  # type: ignore

from src.domain.cleanup_policy import CleanupPolicy, CleanupRule, RetentionPolicy
from src.domain.metrics import CleanupRun, CleanupStatus, CleanupAction as MetricAction, ActionStatus


class GmailCleanupRepository:
    """
    Repository for Gmail cleanup data.
    
    Abstract interface - can be implemented for different storage backends
    (Postgres, Supabase, SQLite, etc.)
    """
    
    async def save_policy(self, policy: CleanupPolicy) -> None:
        """Save or update cleanup policy."""
        raise NotImplementedError
    
    async def get_policy(self, user_id: str, policy_id: str) -> Optional[CleanupPolicy]:
        """Retrieve cleanup policy."""
        raise NotImplementedError
    
    async def list_policies(self, user_id: str) -> List[CleanupPolicy]:
        """List all policies for a user."""
        raise NotImplementedError
    
    async def delete_policy(self, user_id: str, policy_id: str) -> None:
        """Delete cleanup policy."""
        raise NotImplementedError
    
    async def save_run(self, run: CleanupRun) -> None:
        """Save cleanup run."""
        raise NotImplementedError
    
    async def get_run(self, user_id: str, run_id: str) -> Optional[CleanupRun]:
        """Retrieve cleanup run."""
        raise NotImplementedError
    
    async def list_runs(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[CleanupRun]:
        """List cleanup runs for a user."""
        raise NotImplementedError
    
    async def get_run_count(self, user_id: str) -> int:
        """Get total run count for user."""
        raise NotImplementedError


class InMemoryGmailCleanupRepository(GmailCleanupRepository):
    """
    In-memory implementation for testing and development.
    
    Data is lost when process restarts.
    """
    
    def __init__(self):
        self._policies: dict = {}  # {user_id: {policy_id: CleanupPolicy}}
        self._runs: dict = {}  # {user_id: [CleanupRun]}
    
    async def save_policy(self, policy: CleanupPolicy) -> None:
        """Save or update cleanup policy."""
        if policy.user_id not in self._policies:
            self._policies[policy.user_id] = {}
        
        policy.updated_at = datetime.utcnow()
        self._policies[policy.user_id][policy.id] = policy
    
    async def get_policy(self, user_id: str, policy_id: str) -> Optional[CleanupPolicy]:
        """Retrieve cleanup policy."""
        user_policies = self._policies.get(user_id, {})
        return user_policies.get(policy_id)
    
    async def list_policies(self, user_id: str) -> List[CleanupPolicy]:
        """List all policies for a user."""
        user_policies = self._policies.get(user_id, {})
        return list(user_policies.values())
    
    async def delete_policy(self, user_id: str, policy_id: str) -> None:
        """Delete cleanup policy."""
        if user_id in self._policies and policy_id in self._policies[user_id]:
            del self._policies[user_id][policy_id]
    
    async def save_run(self, run: CleanupRun) -> None:
        """Save cleanup run."""
        if run.user_id not in self._runs:
            self._runs[run.user_id] = []
        
        self._runs[run.user_id].append(run)
        
        # Sort by started_at (most recent first)
        self._runs[run.user_id].sort(key=lambda r: r.started_at, reverse=True)
    
    async def get_run(self, user_id: str, run_id: str) -> Optional[CleanupRun]:
        """Retrieve cleanup run."""
        user_runs = self._runs.get(user_id, [])
        for run in user_runs:
            if run.id == run_id:
                return run
        return None
    
    async def list_runs(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[CleanupRun]:
        """List cleanup runs for a user."""
        user_runs = self._runs.get(user_id, [])
        return user_runs[offset:offset + limit]
    
    async def get_run_count(self, user_id: str) -> int:
        """Get total run count for user."""
        return len(self._runs.get(user_id, []))


class PostgresGmailCleanupRepository(GmailCleanupRepository):
    """
    PostgreSQL implementation with asyncpg.
    
    Schema:
    - cleanup_policies: Stores cleanup policies
    - cleanup_runs: Stores cleanup run metadata
    - cleanup_actions: Stores individual actions (audit trail)
    """
    
    def __init__(self, connection_string: str):
        """
        Initialize Postgres repository.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        if not ASYNCPG_AVAILABLE:
            raise RuntimeError("asyncpg not installed. Install with: pip install asyncpg")
        
        self.connection_string = connection_string
        self._pool: Optional[Any] = None  # asyncpg.Pool when available
        self._pool_lock = asyncio.Lock()
    
    async def _get_pool(self) -> Any:  # Returns asyncpg.Pool
        """Get or create connection pool."""
        if self._pool is None:
            async with self._pool_lock:
                if self._pool is None:
                    self._pool = await asyncpg.create_pool(
                        self.connection_string,
                        min_size=2,
                        max_size=10,
                        command_timeout=60,
                    )
        return self._pool
    
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    def _policy_to_dict(self, policy: CleanupPolicy) -> Dict[str, Any]:
        """Convert policy to dict for storage."""
        return {
            "id": policy.id,
            "user_id": policy.user_id,
            "name": policy.name,
            "rules": [
                {
                    "sender_domain": rule.sender_domain,
                    "older_than_days": rule.older_than_days,
                    "category": rule.category.value if rule.category else None,
                    "action": rule.action.value,
                }
                for rule in policy.rules
            ],
            "retention": {
                "keep_starred": policy.retention.keep_starred,
                "keep_important": policy.retention.keep_important,
                "keep_unread": policy.retention.keep_unread,
                "keep_recent_days": policy.retention.keep_recent_days,
            } if policy.retention else None,
            "dry_run": policy.dry_run,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        }
    
    def _dict_to_policy(self, data: Dict[str, Any]) -> CleanupPolicy:
        """Convert dict from storage to policy."""
        from src.domain.email_thread import EmailCategory, CleanupAction as Action
        
        rules = []
        for rule_data in data["rules"]:
            rules.append(CleanupRule(
                sender_domain=rule_data.get("sender_domain"),
                older_than_days=rule_data.get("older_than_days"),
                category=EmailCategory(rule_data["category"]) if rule_data.get("category") else None,
                action=Action(rule_data["action"]),
            ))
        
        retention = None
        if data.get("retention"):
            retention = RetentionPolicy(**data["retention"])
        
        return CleanupPolicy(
            id=data["id"],
            user_id=data["user_id"],
            name=data["name"],
            rules=rules,
            retention=retention,
            dry_run=data.get("dry_run", False),
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
        )
    
    async def save_policy(self, policy: CleanupPolicy) -> None:
        """Save or update cleanup policy."""
        pool = await self._get_pool()
        policy_dict = self._policy_to_dict(policy)
        
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cleanup_policies (
                    id, user_id, name, rules, retention, dry_run, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    rules = EXCLUDED.rules,
                    retention = EXCLUDED.retention,
                    dry_run = EXCLUDED.dry_run,
                    updated_at = EXCLUDED.updated_at
            """,
                policy_dict["id"],
                policy_dict["user_id"],
                policy_dict["name"],
                json.dumps(policy_dict["rules"]),
                json.dumps(policy_dict["retention"]) if policy_dict["retention"] else None,
                policy_dict["dry_run"],
                policy_dict["created_at"],
                policy_dict["updated_at"] or datetime.utcnow(),
            )
    
    async def get_policy(self, user_id: str, policy_id: str) -> Optional[CleanupPolicy]:
        """Retrieve cleanup policy."""
        # TODO: Implement Postgres get
        # SELECT * FROM gmail_cleanup_policies WHERE user_id = ? AND policy_id = ?
        raise NotImplementedError("Postgres implementation pending")
    
    async def list_policies(self, user_id: str) -> List[CleanupPolicy]:
        """List all policies for a user."""
        # TODO: Implement Postgres list
        # SELECT * FROM gmail_cleanup_policies WHERE user_id = ?
        raise NotImplementedError("Postgres implementation pending")
    
    async def delete_policy(self, user_id: str, policy_id: str) -> None:
        """Delete cleanup policy."""
        # TODO: Implement Postgres delete
        # DELETE FROM gmail_cleanup_policies WHERE user_id = ? AND policy_id = ?
        raise NotImplementedError("Postgres implementation pending")
    
    async def save_run(self, run: CleanupRun) -> None:
        """Save cleanup run."""
        # TODO: Implement Postgres save
        # INSERT INTO gmail_cleanup_runs (run_id, user_id, policy_id, ...)
        # INSERT INTO gmail_cleanup_actions (run_id, message_id, action_type, ...)
        raise NotImplementedError("Postgres implementation pending")
    
    async def get_run(self, user_id: str, run_id: str) -> Optional[CleanupRun]:
        """Retrieve cleanup run."""
        # TODO: Implement Postgres get
        # SELECT * FROM gmail_cleanup_runs WHERE user_id = ? AND run_id = ?
        # SELECT * FROM gmail_cleanup_actions WHERE run_id = ?
        raise NotImplementedError("Postgres implementation pending")
    
    async def list_runs(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[CleanupRun]:
        """List cleanup runs for a user."""
        # TODO: Implement Postgres list
        # SELECT * FROM gmail_cleanup_runs WHERE user_id = ?
        # ORDER BY started_at DESC LIMIT ? OFFSET ?
        raise NotImplementedError("Postgres implementation pending")
    
    async def get_run_count(self, user_id: str) -> int:
        """Get total run count for user."""
        # TODO: Implement Postgres count
        # SELECT COUNT(*) FROM gmail_cleanup_runs WHERE user_id = ?
        raise NotImplementedError("Postgres implementation pending")


# SQL Schema for Postgres
POSTGRES_SCHEMA = """
-- Cleanup policies table
CREATE TABLE IF NOT EXISTS gmail_cleanup_policies (
    user_id VARCHAR(255) NOT NULL,
    policy_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Policy configuration (stored as JSONB for flexibility)
    config JSONB NOT NULL,
    
    -- Metadata
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (user_id, policy_id)
);

CREATE INDEX idx_policies_user ON gmail_cleanup_policies(user_id);
CREATE INDEX idx_policies_enabled ON gmail_cleanup_policies(user_id, enabled);

-- Cleanup runs table
CREATE TABLE IF NOT EXISTS gmail_cleanup_runs (
    run_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    policy_id VARCHAR(255) NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    
    -- Snapshots (stored as JSONB)
    before_snapshot JSONB,
    after_snapshot JSONB,
    
    -- Agent context
    agent_session_id VARCHAR(255),
    agent_model VARCHAR(100),
    agent_prompts JSONB,
    
    -- Indexes
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_runs_user ON gmail_cleanup_runs(user_id);
CREATE INDEX idx_runs_status ON gmail_cleanup_runs(user_id, status);
CREATE INDEX idx_runs_started ON gmail_cleanup_runs(user_id, started_at DESC);
CREATE INDEX idx_runs_policy ON gmail_cleanup_runs(user_id, policy_id);

-- Cleanup actions table (audit trail)
CREATE TABLE IF NOT EXISTS gmail_cleanup_actions (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL REFERENCES gmail_cleanup_runs(run_id) ON DELETE CASCADE,
    
    -- Action details
    message_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_params JSONB,
    
    -- Status
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    executed_at TIMESTAMP,
    
    -- Context for audit trail
    message_subject TEXT,
    message_from TEXT,
    message_date TIMESTAMP,
    
    -- Index
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_actions_run ON gmail_cleanup_actions(run_id);
CREATE INDEX idx_actions_message ON gmail_cleanup_actions(message_id);
CREATE INDEX idx_actions_type ON gmail_cleanup_actions(run_id, action_type);
CREATE INDEX idx_actions_status ON gmail_cleanup_actions(run_id, status);

-- View for quick stats
CREATE OR REPLACE VIEW gmail_cleanup_stats AS
SELECT 
    user_id,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
    SUM(duration_seconds) as total_duration_seconds,
    AVG(duration_seconds) as avg_duration_seconds,
    MAX(started_at) as last_run_at
FROM gmail_cleanup_runs
GROUP BY user_id;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_policies_updated_at BEFORE UPDATE ON gmail_cleanup_policies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""


def get_repository(backend: str = "memory", **kwargs) -> GmailCleanupRepository:
    """
    Factory function to get repository implementation.
    
    Args:
        backend: Repository backend ('memory', 'postgres')
        **kwargs: Backend-specific configuration
        
    Returns:
        Repository implementation
    """
    if backend == "memory":
        return InMemoryGmailCleanupRepository()
    elif backend == "postgres":
        connection_string = kwargs.get("connection_string")
        if not connection_string:
            raise ValueError("Postgres backend requires connection_string")
        return PostgresGmailCleanupRepository(connection_string)
    else:
        raise ValueError(f"Unknown backend: {backend}")
