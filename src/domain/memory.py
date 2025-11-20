"""
Agent Memory - Conversation memory with semantic search.

Provides long-term memory for agents to maintain context across sessions.
Uses embeddings for semantic similarity search to retrieve relevant past conversations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from src.domain.models import Message


@dataclass
class MemoryEntry:
    """
    A single memory entry in conversation history.
    
    Stores a message along with metadata for retrieval and context.
    """
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    session_id: str = ""  # Group related conversations
    message: Message = None
    embedding: Optional[List[float]] = None  # Vector embedding for semantic search
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 1.0  # Weight for retrieval prioritization
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "session_id": self.session_id,
            "role": self.message.role.value if self.message else None,
            "content": self.message.content if self.message else None,
            "embedding": self.embedding,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "importance_score": self.importance_score,
        }


@dataclass
class MemorySearchResult:
    """Result from semantic memory search."""
    entry: MemoryEntry
    similarity_score: float  # Cosine similarity (0-1)
    relevance_rank: int  # Position in results


class MemoryConfig:
    """Configuration for memory system."""
    
    def __init__(
        self,
        max_memories_per_retrieval: int = 10,
        similarity_threshold: float = 0.7,
        max_context_window: int = 4000,  # tokens
        enable_importance_weighting: bool = True,
        auto_summarize_threshold: int = 50,  # summarize after N messages
    ):
        self.max_memories_per_retrieval = max_memories_per_retrieval
        self.similarity_threshold = similarity_threshold
        self.max_context_window = max_context_window
        self.enable_importance_weighting = enable_importance_weighting
        self.auto_summarize_threshold = auto_summarize_threshold


class ConversationMemory:
    """
    Manages conversation memory with semantic search.
    
    Features:
    - Store messages with embeddings
    - Semantic similarity search for context retrieval
    - Importance scoring for prioritization
    - Session management for grouping conversations
    - Auto-summarization of long histories
    
    Use cases:
    - Multi-turn conversations with context
    - Customer support with history recall
    - Personalized tutoring
    - Long-term agent relationships
    """
    
    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        embedding_provider: Optional[Any] = None,
    ):
        """
        Initialize conversation memory.
        
        Args:
            config: Memory configuration
            embedding_provider: Provider for generating embeddings
        """
        self.config = config or MemoryConfig()
        self.embedding_provider = embedding_provider
        
        # In-memory storage (will be replaced with persistent storage)
        self.memories: Dict[str, List[MemoryEntry]] = {}  # agent_id -> entries
        self.sessions: Dict[str, List[UUID]] = {}  # session_id -> entry_ids
    
    async def store_message(
        self,
        agent_id: UUID,
        message: Message,
        session_id: Optional[str] = None,
        importance_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """
        Store a message in memory.
        
        Args:
            agent_id: Agent this memory belongs to
            message: Message to store
            session_id: Optional session grouping
            importance_score: Weight for retrieval (0-1)
            metadata: Additional context
            
        Returns:
            Created memory entry
        """
        # Generate embedding for semantic search
        embedding = None
        if self.embedding_provider:
            embedding = await self._generate_embedding(message.content)
        
        # Create memory entry
        entry = MemoryEntry(
            agent_id=agent_id,
            session_id=session_id or "default",
            message=message,
            embedding=embedding,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            importance_score=importance_score,
        )
        
        # Store in memory
        agent_key = str(agent_id)
        if agent_key not in self.memories:
            self.memories[agent_key] = []
        self.memories[agent_key].append(entry)
        
        # Track session
        if entry.session_id not in self.sessions:
            self.sessions[entry.session_id] = []
        self.sessions[entry.session_id].append(entry.id)
        
        return entry
    
    async def retrieve_relevant_context(
        self,
        agent_id: UUID,
        query: str,
        session_id: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[MemorySearchResult]:
        """
        Retrieve relevant memories using semantic search.
        
        Args:
            agent_id: Agent to retrieve memories for
            query: Query text for semantic similarity
            session_id: Optionally filter by session
            max_results: Maximum memories to return
            
        Returns:
            Ranked list of relevant memory entries
        """
        agent_key = str(agent_id)
        if agent_key not in self.memories:
            return []
        
        # Get query embedding
        if not self.embedding_provider:
            # Fallback: return recent memories
            return self._get_recent_memories(
                agent_id, 
                session_id, 
                max_results or self.config.max_memories_per_retrieval
            )
        
        query_embedding = await self._generate_embedding(query)
        
        # Filter memories
        candidates = self.memories[agent_key]
        if session_id:
            candidates = [m for m in candidates if m.session_id == session_id]
        
        # Calculate similarity scores
        results = []
        for entry in candidates:
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                
                # Apply importance weighting
                if self.config.enable_importance_weighting:
                    similarity *= entry.importance_score
                
                if similarity >= self.config.similarity_threshold:
                    results.append((entry, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        max_count = max_results or self.config.max_memories_per_retrieval
        results = results[:max_count]
        
        # Create search results
        return [
            MemorySearchResult(
                entry=entry,
                similarity_score=score,
                relevance_rank=idx + 1,
            )
            for idx, (entry, score) in enumerate(results)
        ]
    
    async def get_session_history(
        self,
        session_id: str,
        max_messages: Optional[int] = None,
    ) -> List[MemoryEntry]:
        """
        Get full conversation history for a session.
        
        Args:
            session_id: Session identifier
            max_messages: Optional limit on messages
            
        Returns:
            Chronological list of messages
        """
        if session_id not in self.sessions:
            return []
        
        entry_ids = self.sessions[session_id]
        
        # Find entries by ID
        entries = []
        for agent_memories in self.memories.values():
            for entry in agent_memories:
                if entry.id in entry_ids:
                    entries.append(entry)
        
        # Sort by timestamp
        entries.sort(key=lambda x: x.timestamp)
        
        if max_messages:
            entries = entries[-max_messages:]
        
        return entries
    
    def get_memory_stats(self, agent_id: UUID) -> Dict[str, Any]:
        """Get statistics about agent's memory."""
        agent_key = str(agent_id)
        if agent_key not in self.memories:
            return {
                "total_memories": 0,
                "sessions": 0,
                "oldest": None,
                "newest": None,
            }
        
        entries = self.memories[agent_key]
        sessions = set(e.session_id for e in entries)
        
        return {
            "total_memories": len(entries),
            "sessions": len(sessions),
            "oldest": min(e.timestamp for e in entries) if entries else None,
            "newest": max(e.timestamp for e in entries) if entries else None,
            "avg_importance": sum(e.importance_score for e in entries) / len(entries) if entries else 0,
        }
    
    async def clear_session(self, session_id: str) -> int:
        """
        Clear all memories for a session.
        
        Returns:
            Number of memories deleted
        """
        if session_id not in self.sessions:
            return 0
        
        entry_ids = self.sessions[session_id]
        deleted = 0
        
        # Remove from memories
        for agent_key in list(self.memories.keys()):
            original_count = len(self.memories[agent_key])
            self.memories[agent_key] = [
                e for e in self.memories[agent_key]
                if e.id not in entry_ids
            ]
            deleted += original_count - len(self.memories[agent_key])
        
        # Remove session
        del self.sessions[session_id]
        
        return deleted
    
    def _get_recent_memories(
        self,
        agent_id: UUID,
        session_id: Optional[str],
        max_results: int,
    ) -> List[MemorySearchResult]:
        """Fallback: get recent memories when embeddings unavailable."""
        agent_key = str(agent_id)
        if agent_key not in self.memories:
            return []
        
        entries = self.memories[agent_key]
        if session_id:
            entries = [e for e in entries if e.session_id == session_id]
        
        # Sort by timestamp (descending)
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        entries = entries[:max_results]
        
        return [
            MemorySearchResult(
                entry=entry,
                similarity_score=1.0,  # No similarity score available
                relevance_rank=idx + 1,
            )
            for idx, entry in enumerate(entries)
        ]
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        if not self.embedding_provider:
            return []
        
        # Use embedding provider (OpenAI, local model, etc.)
        # For now, return empty - will be implemented with real provider
        return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
