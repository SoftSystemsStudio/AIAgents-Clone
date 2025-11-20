"""
Memory Repository - Persistent storage for conversation memory.

Stores memories in PostgreSQL with support for:
- Message persistence with embeddings
- Session-based retrieval
- Semantic search (when using vector extensions)
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json

from sqlalchemy import Column, String, Float, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from src.infrastructure.db_repositories import Base
from src.domain.memory import MemoryEntry, Message, MessageRole


class MemoryEntryModel(Base):
    """SQLAlchemy model for memory entries."""
    
    __tablename__ = "memory_entries"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    agent_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Message content
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    
    # Semantic search
    embedding = Column(ARRAY(Float), nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    importance_score = Column(Float, default=1.0)
    metadata = Column(JSONB, default={})
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_agent_session', 'agent_id', 'session_id'),
        Index('idx_timestamp', 'timestamp'),
    )


class PostgresMemoryRepository:
    """
    PostgreSQL repository for conversation memory.
    
    Provides persistent storage with:
    - Fast session-based retrieval
    - Support for embedding storage (for future vector search)
    - Efficient querying by agent and timeframe
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def save_memory(self, entry: MemoryEntry) -> None:
        """
        Save a memory entry to database.
        
        Args:
            entry: Memory entry to save
        """
        model = MemoryEntryModel(
            id=entry.id,
            agent_id=entry.agent_id,
            session_id=entry.session_id,
            role=entry.message.role.value,
            content=entry.message.content,
            embedding=entry.embedding,
            timestamp=entry.timestamp,
            importance_score=entry.importance_score,
            metadata=entry.metadata,
        )
        
        self.session.add(model)
        await self.session.commit()
    
    async def get_by_session(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[MemoryEntry]:
        """
        Retrieve all memories for a session.
        
        Args:
            session_id: Session identifier
            limit: Optional maximum number of memories
            
        Returns:
            List of memory entries, chronologically ordered
        """
        query = (
            select(MemoryEntryModel)
            .where(MemoryEntryModel.session_id == session_id)
            .order_by(MemoryEntryModel.timestamp.asc())
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entry(model) for model in models]
    
    async def get_by_agent(
        self,
        agent_id: UUID,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[MemoryEntry]:
        """
        Retrieve memories for an agent.
        
        Args:
            agent_id: Agent identifier
            session_id: Optional session filter
            limit: Optional maximum number of memories
            
        Returns:
            List of memory entries
        """
        conditions = [MemoryEntryModel.agent_id == agent_id]
        if session_id:
            conditions.append(MemoryEntryModel.session_id == session_id)
        
        query = (
            select(MemoryEntryModel)
            .where(and_(*conditions))
            .order_by(MemoryEntryModel.timestamp.desc())
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entry(model) for model in models]
    
    async def search_by_importance(
        self,
        agent_id: UUID,
        min_importance: float = 0.5,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        Retrieve high-importance memories for an agent.
        
        Args:
            agent_id: Agent identifier
            min_importance: Minimum importance score threshold
            limit: Maximum memories to return
            
        Returns:
            List of important memory entries
        """
        query = (
            select(MemoryEntryModel)
            .where(
                and_(
                    MemoryEntryModel.agent_id == agent_id,
                    MemoryEntryModel.importance_score >= min_importance,
                )
            )
            .order_by(MemoryEntryModel.importance_score.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entry(model) for model in models]
    
    async def delete_session(self, session_id: str) -> int:
        """
        Delete all memories for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of memories deleted
        """
        query = select(func.count()).where(
            MemoryEntryModel.session_id == session_id
        )
        result = await self.session.execute(query)
        count = result.scalar()
        
        # Delete memories
        delete_query = MemoryEntryModel.__table__.delete().where(
            MemoryEntryModel.session_id == session_id
        )
        await self.session.execute(delete_query)
        await self.session.commit()
        
        return count or 0
    
    async def get_stats(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Get memory statistics for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Statistics dictionary
        """
        # Count total memories
        count_query = select(func.count()).where(
            MemoryEntryModel.agent_id == agent_id
        )
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0
        
        if total == 0:
            return {
                "total_memories": 0,
                "sessions": 0,
                "oldest": None,
                "newest": None,
                "avg_importance": 0.0,
            }
        
        # Get sessions count
        sessions_query = (
            select(func.count(func.distinct(MemoryEntryModel.session_id)))
            .where(MemoryEntryModel.agent_id == agent_id)
        )
        sessions_result = await self.session.execute(sessions_query)
        sessions_count = sessions_result.scalar() or 0
        
        # Get timestamp range
        range_query = select(
            func.min(MemoryEntryModel.timestamp),
            func.max(MemoryEntryModel.timestamp),
            func.avg(MemoryEntryModel.importance_score),
        ).where(MemoryEntryModel.agent_id == agent_id)
        
        range_result = await self.session.execute(range_query)
        oldest, newest, avg_importance = range_result.one()
        
        return {
            "total_memories": total,
            "sessions": sessions_count,
            "oldest": oldest,
            "newest": newest,
            "avg_importance": float(avg_importance) if avg_importance else 0.0,
        }
    
    def _model_to_entry(self, model: MemoryEntryModel) -> MemoryEntry:
        """Convert database model to domain object."""
        message = Message(
            role=MessageRole(model.role),
            content=model.content,
        )
        
        return MemoryEntry(
            id=model.id,
            agent_id=model.agent_id,
            session_id=model.session_id,
            message=message,
            embedding=model.embedding,
            timestamp=model.timestamp,
            metadata=model.metadata or {},
            importance_score=model.importance_score,
        )
