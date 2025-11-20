"""
Domain Models - Core business entities.

These are framework-agnostic domain models representing the core concepts
of the AI agents platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class MessageRole(str, Enum):
    """Message role in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """
    Represents a message in an agent conversation.
    
    Immutable value object following domain-driven design principles.
    """

    id: UUID = Field(default_factory=uuid4)
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Tool-specific fields
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str, info) -> str:
        """Ensure message content is not empty (unless there are tool_calls)."""
        # Allow empty content if there are tool_calls
        if hasattr(info, 'data') and info.data.get('tool_calls'):
            return v or ""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v

    class Config:
        frozen = True  # Immutable


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"  # Waiting for external input/tool
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCapability(str, Enum):
    """Agent capabilities/permissions."""

    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"
    FILE_ACCESS = "file_access"
    DATABASE_ACCESS = "database_access"
    API_CALLS = "api_calls"


class Agent(BaseModel):
    """
    Core Agent entity representing an AI agent.
    
    An agent has:
    - Identity (id, name)
    - Configuration (model, capabilities, constraints)
    - State (status, conversation history)
    - Behavior (system prompt, tools)
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    system_prompt: str
    
    # LLM Configuration
    model_provider: str  # e.g., "openai", "anthropic"
    model_name: str  # e.g., "gpt-4", "claude-3-opus"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, gt=0)
    
    # Agent capabilities and constraints
    capabilities: List[AgentCapability] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    max_iterations: int = Field(default=10, gt=0)
    timeout_seconds: int = Field(default=300, gt=0)
    
    # State
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    conversation_history: List[Message] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Ensure agent name is not empty."""
        if not v or not v.strip():
            raise ValueError("Agent name cannot be empty")
        return v

    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation history.
        
        Note: In a truly immutable design, this would return a new Agent instance.
        For practical purposes, we mutate the list but enforce validation.
        """
        self.conversation_history.append(message)
        self.updated_at = datetime.utcnow()

    def update_status(self, status: AgentStatus) -> None:
        """Update agent status with timestamp."""
        self.status = status
        self.updated_at = datetime.utcnow()

    class Config:
        # Allow mutation for status updates, but document that messages are append-only
        frozen = False


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""

    name: str
    type: str  # e.g., "string", "integer", "boolean"
    description: str
    required: bool = True
    default: Optional[Any] = None


class Tool(BaseModel):
    """
    Represents a tool/function that an agent can use.
    
    Tools are capabilities that agents can invoke to perform actions
    or retrieve information (e.g., web search, database query, API call).
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    required_capability: Optional[AgentCapability] = None
    
    # Implementation details (not exposed to LLM)
    handler_module: str  # Python module path
    handler_function: str  # Function name to invoke
    
    # Rate limiting and constraints
    max_calls_per_minute: int = Field(default=10, gt=0)
    timeout_seconds: int = Field(default=30, gt=0)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_valid_identifier(cls, v: str) -> str:
        """Ensure tool name is a valid identifier."""
        if not v.isidentifier():
            raise ValueError(f"Tool name must be a valid Python identifier: {v}")
        return v

    def to_llm_schema(self) -> Dict[str, Any]:
        """
        Convert tool to LLM function schema format.
        
        This is the format expected by LLM APIs (OpenAI, Anthropic, etc.)
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description,
                    }
                    for param in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required],
            },
        }


class ExecutionResult(BaseModel):
    """
    Result of an agent execution.
    
    Contains the outcome, any outputs, metrics, and error information.
    """

    agent_id: UUID
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    
    # Execution metrics
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_seconds: float = 0.0
    iterations: int = 0
    
    # Cost tracking (in USD)
    estimated_cost: float = 0.0
    
    # Metadata
    final_status: AgentStatus
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True  # Immutable result
