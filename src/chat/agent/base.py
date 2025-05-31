"""Base classes and interfaces for multi-agent political monitoring system."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState


class AgentRole(Enum):
    """Enumeration of agent roles in the multi-agent system."""

    QUERY_UNDERSTANDING = "query_understanding"
    TOOL_PLANNING = "tool_planning"
    TOOL_EXECUTION = "tool_execution"
    RESPONSE_SYNTHESIS = "response_synthesis"


@dataclass
class AgentResult:
    """Standard result structure for inter-agent communication."""

    success: bool
    updated_state: "MultiAgentState"
    data: dict[str, Any]
    message: str = ""
    next_agent: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    metadata: dict[str, Any] = None
    errors: list[str] = None
    thinking_output: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for state management."""
        return {
            "agent_role": self.agent_role.value,
            "success": self.success,
            "updated_state": self.updated_state,
            "data": self.data,
            "metadata": self.metadata,
            "errors": self.errors,
            "thinking_output": self.thinking_output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentResult":
        """Create from dictionary."""
        return cls(
            agent_role=AgentRole(data["agent_role"]),
            success=data["success"],
            updated_state=data["updated_state"],
            data=data["data"],
            metadata=data["metadata"],
            errors=data["errors"],
            thinking_output=data.get("thinking_output"),
        )


class MultiAgentState(MessagesState):
    """Enhanced state schema for multi-agent system with memory support."""

    # Core query information
    original_query: str
    processed_query: str = ""

    # Agent results
    query_analysis: Optional[dict[str, Any]] = None
    tool_plan: Optional[dict[str, Any]] = None
    tool_results: list[dict[str, Any]] = []
    final_response: str = ""

    # Execution tracking
    current_agent: str = ""
    agent_sequence: list[str] = []
    execution_metadata: dict[str, Any] = {}

    # Memory context
    session_id: Optional[str] = None
    conversation_history: list[BaseMessage] = []
    user_preferences: dict[str, Any] = {}
    learned_patterns: dict[str, Any] = {}

    # Streaming and progress
    is_streaming: bool = False
    thinking_updates: list[str] = []
    progress_indicators: list[str] = []

    # Error handling
    errors: list[str] = []
    warnings: list[str] = []


class BaseAgent(ABC):
    """Abstract base class for all agents in the multi-agent system."""

    def __init__(self, agent_role: AgentRole, name: str):
        self.agent_role = agent_role
        self.name = name
        self._thinking_buffer: list[str] = []

    @abstractmethod
    async def process(self, state: MultiAgentState) -> AgentResult:
        """
        Process the current state and return results.

        Args:
            state: Current multi-agent state

        Returns:
            AgentResult with processing results
        """
        pass

    @abstractmethod
    def get_prompt_template(self) -> str:
        """Get the prompt template for this agent."""
        pass

    def add_thinking(self, thought: str) -> None:
        """Add thinking output for streaming."""
        self._thinking_buffer.append(thought)

    def get_thinking_output(self) -> str:
        """Get accumulated thinking output."""
        output = " ".join(self._thinking_buffer)
        self._thinking_buffer.clear()
        return output

    async def stream_thinking_buffer(self) -> AsyncGenerator[str, None]:
        """Stream thinking output from buffer in real-time."""
        for thought in self._thinking_buffer:
            yield thought
        self._thinking_buffer.clear()

    def create_success_result(
        self,
        updated_state: "MultiAgentState",
        data: dict[str, Any],
        metadata: dict[str, Any] = None,
    ) -> AgentResult:
        """Helper to create successful result."""
        return AgentResult(
            agent_role=self.agent_role,
            success=True,
            updated_state=updated_state,
            data=data,
            metadata=metadata or {},
            errors=[],
            thinking_output=self.get_thinking_output(),
        )

    def create_error_result(
        self, updated_state: "MultiAgentState", errors: list[str], data: dict[str, Any] = None
    ) -> AgentResult:
        """Helper to create error result."""
        return AgentResult(
            agent_role=self.agent_role,
            success=False,
            updated_state=updated_state,
            data=data or {},
            metadata={},
            errors=errors,
            thinking_output=self.get_thinking_output(),
        )


class StreamingMixin:
    """Mixin for agents that support advanced streaming capabilities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stream_writer = None

    def set_stream_writer(self, writer):
        """Set the stream writer for real-time updates."""
        self._stream_writer = writer

    async def stream_custom(self, data: dict[str, Any]) -> None:
        """Stream custom data using LangGraph's streaming system."""
        if self._stream_writer:
            await self._stream_writer(data)

    async def stream_thinking(self, thought: str) -> None:
        """Stream thinking output."""
        await self.stream_custom({"thinking": thought, "agent": self.name})

    async def stream_progress(self, progress: str) -> None:
        """Stream progress updates."""
        await self.stream_custom({"progress": progress, "agent": self.name})

    async def stream_transition(self, next_agent: str) -> None:
        """Stream agent transition."""
        await self.stream_custom(
            {
                "transition": f"Handing off from {self.name} to {next_agent}",
                "from_agent": self.name,
                "to_agent": next_agent,
            }
        )


class MemoryMixin:
    """Mixin for agents that use memory capabilities."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._memory_store = None
        self._checkpointer = None

    def set_memory_components(self, memory_store, checkpointer):
        """Set memory components."""
        self._memory_store = memory_store
        self._checkpointer = checkpointer

    async def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference from long-term memory."""
        if not self._memory_store:
            return default

        try:
            prefs = await self._memory_store.aget(f"user_prefs_{user_id}")
            return prefs.get(key, default) if prefs else default
        except Exception:
            return default

    async def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set user preference in long-term memory."""
        if not self._memory_store:
            return

        try:
            prefs = await self._memory_store.aget(f"user_prefs_{user_id}") or {}
            prefs[key] = value
            await self._memory_store.aput(f"user_prefs_{user_id}", prefs)
        except Exception:
            pass  # Graceful degradation

    async def get_conversation_context(
        self, thread_id: str, max_messages: int = 10
    ) -> list[BaseMessage]:
        """Get recent conversation context."""
        if not self._checkpointer:
            return []

        try:
            # This would integrate with LangGraph's checkpointing system
            # Implementation depends on specific checkpointer
            return []  # Placeholder
        except Exception:
            return []

    async def learn_pattern(self, pattern_type: str, pattern_data: dict[str, Any]) -> None:
        """Store learned patterns for future optimization."""
        if not self._memory_store:
            return

        try:
            patterns = await self._memory_store.aget(f"patterns_{pattern_type}") or []
            patterns.append(pattern_data)
            await self._memory_store.aput(f"patterns_{pattern_type}", patterns)
        except Exception:
            pass
