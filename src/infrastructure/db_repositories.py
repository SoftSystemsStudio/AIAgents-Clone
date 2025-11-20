"""
PostgreSQL Repository Implementation - Production-ready persistence.

Provides database-backed storage for agents and conversation history.
Uses SQLAlchemy for ORM and async database operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import relationship

from src.domain.interfaces import IAgentRepository
from src.domain.models import Agent, AgentCapability, AgentStatus, Message, MessageRole
from src.domain.exceptions import AgentNotFoundError

# SQLAlchemy Base
Base = declarative_base()


class AgentModel(Base):
    """SQLAlchemy model for Agent table."""
    
    __tablename__ = "agents"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    model_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4000)
    status = Column(String(20), default="idle", index=True)
    capabilities = Column(JSON, default=list)
    allowed_tools = Column(JSON, default=list)
    max_iterations = Column(Integer, default=10)
    timeout_seconds = Column(Integer, default=300)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
    # Relationships
    messages = relationship("MessageModel", back_populates="agent", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_agent_status_created', 'status', 'created_at'),
        Index('idx_agent_provider_model', 'model_provider', 'model_name'),
    )


class MessageModel(Base):
    """SQLAlchemy model for Message table."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON)
    tool_call_id = Column(String(255))
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("AgentModel", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_agent_created', 'agent_id', 'created_at'),
        Index('idx_message_role', 'role'),
    )


class PostgreSQLAgentRepository(IAgentRepository):
    """
    PostgreSQL implementation of agent repository.
    
    Provides production-ready persistence with:
    - Async database operations
    - Transaction management
    - Connection pooling
    - Conversation history storage
    - Efficient indexing
    
    RISK: Database can become bottleneck at scale.
    Mitigation: Connection pooling, indexes, read replicas.
    """
    
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        """
        Initialize PostgreSQL repository.
        
        Args:
            database_url: PostgreSQL connection string (async format)
                Example: "postgresql+asyncpg://user:pass@localhost/dbname"
            pool_size: Number of connections to maintain
            max_overflow: Max connections above pool_size
        """
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            echo=False,  # Set to True for SQL logging in development
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def initialize(self):
        """Create database tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def save(self, agent: Agent) -> None:
        """
        Persist an agent and its conversation history.
        
        If agent exists, updates it. Otherwise, creates new record.
        """
        async with self.async_session() as session:
            async with session.begin():
                # Check if agent exists
                result = await session.execute(
                    select(AgentModel).where(AgentModel.id == agent.id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing agent
                    existing.name = agent.name
                    existing.description = agent.description
                    existing.system_prompt = agent.system_prompt
                    existing.model_provider = agent.model_provider
                    existing.model_name = agent.model_name
                    existing.temperature = agent.temperature
                    existing.max_tokens = agent.max_tokens
                    existing.status = agent.status.value
                    existing.capabilities = [cap.value for cap in agent.capabilities]
                    existing.allowed_tools = agent.allowed_tools
                    existing.max_iterations = agent.max_iterations
                    existing.timeout_seconds = agent.timeout_seconds
                    existing.updated_at = agent.updated_at
                    
                    # Delete old messages and add new ones
                    await session.execute(
                        select(MessageModel).where(MessageModel.agent_id == agent.id)
                    )
                    for msg_model in existing.messages:
                        await session.delete(msg_model)
                    
                    # Add current messages
                    for msg in agent.conversation_history:
                        msg_model = MessageModel(
                            agent_id=agent.id,
                            role=msg.role.value,
                            content=msg.content,
                            tool_calls=msg.tool_calls,
                            tool_call_id=msg.tool_call_id,
                            metadata=msg.metadata,
                            created_at=datetime.utcnow(),
                        )
                        session.add(msg_model)
                else:
                    # Create new agent
                    agent_model = AgentModel(
                        id=agent.id,
                        name=agent.name,
                        description=agent.description,
                        system_prompt=agent.system_prompt,
                        model_provider=agent.model_provider,
                        model_name=agent.model_name,
                        temperature=agent.temperature,
                        max_tokens=agent.max_tokens,
                        status=agent.status.value,
                        capabilities=[cap.value for cap in agent.capabilities],
                        allowed_tools=agent.allowed_tools,
                        max_iterations=agent.max_iterations,
                        timeout_seconds=agent.timeout_seconds,
                        created_at=agent.created_at,
                        updated_at=agent.updated_at,
                    )
                    session.add(agent_model)
                    
                    # Add messages
                    for msg in agent.conversation_history:
                        msg_model = MessageModel(
                            agent_id=agent.id,
                            role=msg.role.value,
                            content=msg.content,
                            tool_calls=msg.tool_calls,
                            tool_call_id=msg.tool_call_id,
                            metadata=msg.metadata,
                            created_at=datetime.utcnow(),
                        )
                        session.add(msg_model)
                
                await session.commit()
    
    async def get_by_id(self, agent_id: UUID) -> Optional[Agent]:
        """Retrieve an agent by ID with conversation history."""
        async with self.async_session() as session:
            result = await session.execute(
                select(AgentModel).where(AgentModel.id == agent_id)
            )
            agent_model = result.scalar_one_or_none()
            
            if not agent_model:
                return None
            
            # Load messages
            msg_result = await session.execute(
                select(MessageModel)
                .where(MessageModel.agent_id == agent_id)
                .order_by(MessageModel.created_at)
            )
            message_models = msg_result.scalars().all()
            
            return self._model_to_domain(agent_model, message_models)
    
    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Retrieve an agent by name."""
        async with self.async_session() as session:
            result = await session.execute(
                select(AgentModel).where(AgentModel.name == name)
            )
            agent_model = result.scalar_one_or_none()
            
            if not agent_model:
                return None
            
            # Load messages
            msg_result = await session.execute(
                select(MessageModel)
                .where(MessageModel.agent_id == agent_model.id)
                .order_by(MessageModel.created_at)
            )
            message_models = msg_result.scalars().all()
            
            return self._model_to_domain(agent_model, message_models)
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Agent]:
        """
        List all agents with pagination.
        
        Note: Does not load conversation history for performance.
        Use get_by_id to load full agent with history.
        """
        async with self.async_session() as session:
            result = await session.execute(
                select(AgentModel)
                .order_by(AgentModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            agent_models = result.scalars().all()
            
            # Return agents without conversation history (performance)
            return [self._model_to_domain(model, []) for model in agent_models]
    
    async def delete(self, agent_id: UUID) -> None:
        """Delete an agent and all associated messages (cascade)."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(AgentModel).where(AgentModel.id == agent_id)
                )
                agent_model = result.scalar_one_or_none()
                
                if agent_model:
                    await session.delete(agent_model)
                    await session.commit()
    
    async def update_status(self, agent_id: UUID, status: str) -> None:
        """Efficiently update agent status without loading full entity."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(AgentModel).where(AgentModel.id == agent_id)
                )
                agent_model = result.scalar_one_or_none()
                
                if not agent_model:
                    raise AgentNotFoundError(str(agent_id))
                
                agent_model.status = status
                agent_model.updated_at = datetime.utcnow()
                await session.commit()
    
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
    
    def _model_to_domain(
        self,
        agent_model: AgentModel,
        message_models: List[MessageModel],
    ) -> Agent:
        """Convert SQLAlchemy models to domain Agent."""
        # Convert messages
        messages = []
        for msg_model in message_models:
            messages.append(
                Message(
                    role=MessageRole(msg_model.role),
                    content=msg_model.content,
                    tool_calls=msg_model.tool_calls,
                    tool_call_id=msg_model.tool_call_id,
                    metadata=msg_model.metadata or {},
                )
            )
        
        # Create agent
        agent = Agent(
            name=agent_model.name,
            description=agent_model.description,
            system_prompt=agent_model.system_prompt,
            model_provider=agent_model.model_provider,
            model_name=agent_model.model_name,
            temperature=agent_model.temperature,
            max_tokens=agent_model.max_tokens,
            capabilities=[AgentCapability(cap) for cap in agent_model.capabilities],
            allowed_tools=agent_model.allowed_tools,
            max_iterations=agent_model.max_iterations,
            timeout_seconds=agent_model.timeout_seconds,
        )
        
        # Override generated fields with stored values
        agent.id = agent_model.id
        agent.status = AgentStatus(agent_model.status)
        agent.created_at = agent_model.created_at
        agent.updated_at = agent_model.updated_at
        agent.conversation_history = messages
        
        return agent
