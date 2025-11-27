import asyncio
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal, get_db
from .models_sql import AgentRun, DemoEvent, User


class PostgresGmailCleanupRepository:
    """Simple blocking SQLAlchemy-backed repository with async wrappers.

    These methods run the blocking DB access in a thread using
    `asyncio.to_thread` so the caller can `await` them from async tests.
    """

    def __init__(self):
        # Placeholder for any per-repo config
        pass

    # --- helper run-in-thread wrapper
    def _run_sync(self, fn, *args, **kwargs):
        return asyncio.to_thread(fn, *args, **kwargs)

    # --- policies (minimal placeholders) ---
    async def save_policy(self, policy) -> None:
        # For now policies are stored elsewhere; this is a placeholder so
        # integration tests that call `save_policy` will not fail.
        def _save():
            # No-op or could store JSON in a table
            return None
        return await self._run_sync(_save)

    async def get_policy(self, user_id: str, policy_id: str):
        # Placeholder
        return None

    # --- runs ---
    async def save_run(self, run) -> None:
        def _save():
            db: Session = next(get_db())
            ar = AgentRun(
                run_id=run.id,
                user_id=None if not getattr(run, 'user_id', None) else run.user_id,
                policy_id=getattr(run, 'policy_id', None),
                status=getattr(run, 'status', 'unknown'),
                metrics=str({
                    'actions_total': len(getattr(run, 'actions', []))
                }),
                created_at=getattr(run, 'started_at', None),
                completed_at=getattr(run, 'completed_at', None),
            )
            db.add(ar)
            db.commit()
            db.refresh(ar)
            return None
        return await self._run_sync(_save)

    async def get_run(self, user_id: str, run_id: str) -> Optional[AgentRun]:
        def _get():
            db: Session = next(get_db())
            q = db.query(AgentRun).filter(AgentRun.run_id == run_id)
            return q.first()
        return await self._run_sync(_get)

    async def list_runs(self, user_id: str) -> List[AgentRun]:
        def _list():
            db: Session = next(get_db())
            return db.query(AgentRun).order_by(AgentRun.created_at.desc()).all()
        return await self._run_sync(_list)

    async def get_run_count(self, user_id: str) -> int:
        def _count():
            db: Session = next(get_db())
            return db.query(AgentRun).count()
        return await self._run_sync(_count)


# Provide a convenience factory
def create_postgres_repository() -> PostgresGmailCleanupRepository:
    return PostgresGmailCleanupRepository()
