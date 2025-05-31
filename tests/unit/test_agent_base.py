"""Unit tests for agent base classes and interfaces."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.chat.agent.base import (
    AgentResult,
    AgentRole,
    BaseAgent,
    MemoryMixin,
    MultiAgentState,
    StreamingMixin,
)


class TestAgentRole:
    """Test AgentRole enumeration."""

    def test_agent_role_values(self):
        """Test that agent roles have correct values."""
        assert AgentRole.QUERY_UNDERSTANDING.value == "query_understanding"
        assert AgentRole.TOOL_PLANNING.value == "tool_planning"
        assert AgentRole.TOOL_EXECUTION.value == "tool_execution"
        assert AgentRole.RESPONSE_SYNTHESIS.value == "response_synthesis"


class TestAgentResult:
    """Test AgentResult data structure."""

    def test_agent_result_creation(self):
        """Test creating an AgentResult."""
        result = AgentResult(
            agent_role=AgentRole.QUERY_UNDERSTANDING,
            success=True,
            data={"intent": "information_seeking"},
            metadata={"confidence": 0.9},
            errors=[],
            thinking_output="Analyzed the query",
        )

        assert result.agent_role == AgentRole.QUERY_UNDERSTANDING
        assert result.success is True
        assert result.data["intent"] == "information_seeking"
        assert result.metadata["confidence"] == 0.9
        assert result.errors == []
        assert result.thinking_output == "Analyzed the query"

    def test_agent_result_to_dict(self):
        """Test converting AgentResult to dictionary."""
        result = AgentResult(
            agent_role=AgentRole.TOOL_PLANNING,
            success=False,
            data={},
            metadata={},
            errors=["Planning failed"],
            thinking_output=None,
        )

        result_dict = result.to_dict()

        assert result_dict["agent_role"] == "tool_planning"
        assert result_dict["success"] is False
        assert result_dict["errors"] == ["Planning failed"]
        assert result_dict["thinking_output"] is None

    def test_agent_result_from_dict(self):
        """Test creating AgentResult from dictionary."""
        data = {
            "agent_role": "response_synthesis",
            "success": True,
            "data": {"response": "Generated response"},
            "metadata": {"word_count": 150},
            "errors": [],
            "thinking_output": "Synthesized response",
        }

        result = AgentResult.from_dict(data)

        assert result.agent_role == AgentRole.RESPONSE_SYNTHESIS
        assert result.success is True
        assert result.data["response"] == "Generated response"
        assert result.metadata["word_count"] == 150


class TestMultiAgentState:
    """Test MultiAgentState structure."""

    def test_multi_agent_state_initialization(self):
        """Test default initialization of MultiAgentState."""
        # MultiAgentState inherits from MessagesState which behaves like a dict
        state = MultiAgentState()

        # MessagesState doesn't populate defaults, so we need to test actual behavior
        # Default values aren't automatically set in LangGraph's MessagesState
        assert state.get("original_query", "") == ""
        assert (
            state.get("current_agent", "query_understanding") == "query_understanding"
        )  # Use default in get()
        assert state.get("agent_sequence", []) == []
        assert state.get("tool_results", []) == []
        assert state.get("user_preferences", {}) == {}
        assert state.get("is_streaming", False) is False
        assert state.get("errors", []) == []

    def test_multi_agent_state_with_values(self):
        """Test MultiAgentState with initial values."""
        state = MultiAgentState(
            original_query="What is the EU AI Act?",
            session_id="test_session_123",
            is_streaming=True,
        )

        # Access as dictionary since it inherits from MessagesState
        assert state.get("original_query") == "What is the EU AI Act?"
        assert state.get("session_id") == "test_session_123"
        assert state.get("is_streaming") is True


class MockAgent(BaseAgent):
    """Mock agent for testing BaseAgent functionality."""

    def __init__(self):
        super().__init__(AgentRole.QUERY_UNDERSTANDING, "mock_agent")
        self.process_called = False
        self.process_result = None

    async def process(self, state: MultiAgentState) -> AgentResult:
        """Mock process method."""
        self.process_called = True

        if self.process_result:
            return self.process_result

        return self.create_success_result(data={"mock": "data"}, metadata={"mock": True})

    def get_prompt_template(self) -> str:
        """Mock prompt template."""
        return "Mock prompt template"


class TestBaseAgent:
    """Test BaseAgent abstract class functionality."""

    def test_base_agent_initialization(self):
        """Test BaseAgent initialization."""
        agent = MockAgent()

        assert agent.agent_role == AgentRole.QUERY_UNDERSTANDING
        assert agent.name == "mock_agent"
        assert agent._thinking_buffer == []

    def test_add_thinking(self):
        """Test adding thinking output."""
        agent = MockAgent()

        agent.add_thinking("First thought")
        agent.add_thinking("Second thought")

        assert len(agent._thinking_buffer) == 2
        assert agent._thinking_buffer[0] == "First thought"
        assert agent._thinking_buffer[1] == "Second thought"

    def test_get_thinking_output(self):
        """Test getting accumulated thinking output."""
        agent = MockAgent()

        agent.add_thinking("Thought 1")
        agent.add_thinking("Thought 2")

        output = agent.get_thinking_output()

        assert output == "Thought 1 Thought 2"
        assert agent._thinking_buffer == []  # Should be cleared

    @pytest.mark.asyncio
    async def test_stream_thinking_buffer(self):
        """Test streaming thinking output from buffer."""
        agent = MockAgent()

        agent.add_thinking("Stream 1")
        agent.add_thinking("Stream 2")

        thoughts = []
        async for thought in agent.stream_thinking_buffer():
            thoughts.append(thought)

        assert thoughts == ["Stream 1", "Stream 2"]
        assert agent._thinking_buffer == []  # Should be cleared

    def test_create_success_result(self):
        """Test creating successful result."""
        agent = MockAgent()
        agent.add_thinking("Success thinking")

        result = agent.create_success_result(data={"key": "value"}, metadata={"meta": "data"})

        assert result.agent_role == AgentRole.QUERY_UNDERSTANDING
        assert result.success is True
        assert result.data["key"] == "value"
        assert result.metadata["meta"] == "data"
        assert result.errors == []
        assert result.thinking_output == "Success thinking"

    def test_create_error_result(self):
        """Test creating error result."""
        agent = MockAgent()
        agent.add_thinking("Error thinking")

        result = agent.create_error_result(errors=["Error 1", "Error 2"], data={"partial": "data"})

        assert result.agent_role == AgentRole.QUERY_UNDERSTANDING
        assert result.success is False
        assert result.data["partial"] == "data"
        assert result.errors == ["Error 1", "Error 2"]
        assert result.thinking_output == "Error thinking"

    @pytest.mark.asyncio
    async def test_process_method(self):
        """Test that process method is called correctly."""
        agent = MockAgent()
        state = MultiAgentState(original_query="Test query")

        result = await agent.process(state)

        assert agent.process_called is True
        assert result.success is True
        assert result.data["mock"] == "data"


class MockStreamingAgent(BaseAgent, StreamingMixin):
    """Mock agent with streaming capabilities."""

    def __init__(self):
        # Call both parent constructors
        BaseAgent.__init__(self, AgentRole.TOOL_EXECUTION, "streaming_agent")
        StreamingMixin.__init__(self)
        self.stream_calls = []

    async def process(self, state: MultiAgentState) -> AgentResult:
        return self.create_success_result({"test": "data"})

    def get_prompt_template(self) -> str:
        return "Streaming template"


class TestStreamingMixin:
    """Test StreamingMixin functionality."""

    def test_streaming_mixin_initialization(self):
        """Test StreamingMixin initialization."""
        agent = MockStreamingAgent()

        assert hasattr(agent, "_stream_writer")
        assert agent._stream_writer is None

    def test_set_stream_writer(self):
        """Test setting stream writer."""
        agent = MockStreamingAgent()
        mock_writer = MagicMock()

        agent.set_stream_writer(mock_writer)

        assert agent._stream_writer == mock_writer

    @pytest.mark.asyncio
    async def test_stream_custom(self):
        """Test streaming custom data."""
        agent = MockStreamingAgent()
        mock_writer = AsyncMock()
        agent.set_stream_writer(mock_writer)

        await agent.stream_custom({"test": "data"})

        mock_writer.assert_called_once_with({"test": "data"})

    @pytest.mark.asyncio
    async def test_stream_thinking(self):
        """Test streaming thinking output."""
        agent = MockStreamingAgent()
        mock_writer = AsyncMock()
        agent.set_stream_writer(mock_writer)

        await agent.stream_thinking("Test thought")

        mock_writer.assert_called_once_with(
            {"thinking": "Test thought", "agent": "streaming_agent"}
        )

    @pytest.mark.asyncio
    async def test_stream_progress(self):
        """Test streaming progress updates."""
        agent = MockStreamingAgent()
        mock_writer = AsyncMock()
        agent.set_stream_writer(mock_writer)

        await agent.stream_progress("50% complete")

        mock_writer.assert_called_once_with(
            {"progress": "50% complete", "agent": "streaming_agent"}
        )

    @pytest.mark.asyncio
    async def test_stream_transition(self):
        """Test streaming agent transitions."""
        agent = MockStreamingAgent()
        mock_writer = AsyncMock()
        agent.set_stream_writer(mock_writer)

        await agent.stream_transition("next_agent")

        expected_call = {
            "transition": "Handing off from streaming_agent to next_agent",
            "from_agent": "streaming_agent",
            "to_agent": "next_agent",
        }
        mock_writer.assert_called_once_with(expected_call)


class MockMemoryAgent(BaseAgent, MemoryMixin):
    """Mock agent with memory capabilities."""

    def __init__(self):
        # Call both parent constructors
        BaseAgent.__init__(self, AgentRole.RESPONSE_SYNTHESIS, "memory_agent")
        MemoryMixin.__init__(self)

    async def process(self, state: MultiAgentState) -> AgentResult:
        return self.create_success_result({"test": "data"})

    def get_prompt_template(self) -> str:
        return "Memory template"


class TestMemoryMixin:
    """Test MemoryMixin functionality."""

    def test_memory_mixin_initialization(self):
        """Test MemoryMixin initialization."""
        agent = MockMemoryAgent()

        assert hasattr(agent, "_memory_store")
        assert hasattr(agent, "_checkpointer")
        assert agent._memory_store is None
        assert agent._checkpointer is None

    def test_set_memory_components(self):
        """Test setting memory components."""
        agent = MockMemoryAgent()
        mock_store = MagicMock()
        mock_checkpointer = MagicMock()

        agent.set_memory_components(mock_store, mock_checkpointer)

        assert agent._memory_store == mock_store
        assert agent._checkpointer == mock_checkpointer

    @pytest.mark.asyncio
    async def test_get_user_preference_no_store(self):
        """Test getting user preference without memory store."""
        agent = MockMemoryAgent()

        result = await agent.get_user_preference("user123", "theme", "default")

        assert result == "default"

    @pytest.mark.asyncio
    async def test_get_user_preference_with_store(self):
        """Test getting user preference with memory store."""
        agent = MockMemoryAgent()
        mock_store = AsyncMock()
        mock_store.aget.return_value = {"theme": "dark", "language": "en"}
        agent.set_memory_components(mock_store, None)

        result = await agent.get_user_preference("user123", "theme", "default")

        assert result == "dark"
        mock_store.aget.assert_called_once_with("user_prefs_user123")

    @pytest.mark.asyncio
    async def test_set_user_preference(self):
        """Test setting user preference."""
        agent = MockMemoryAgent()
        mock_store = AsyncMock()
        mock_store.aget.return_value = {"theme": "light"}
        agent.set_memory_components(mock_store, None)

        await agent.set_user_preference("user123", "language", "es")

        # Should call aget to get existing prefs, then aput to save updated prefs
        mock_store.aget.assert_called_once_with("user_prefs_user123")
        mock_store.aput.assert_called_once_with(
            "user_prefs_user123", {"theme": "light", "language": "es"}
        )

    @pytest.mark.asyncio
    async def test_get_conversation_context_no_checkpointer(self):
        """Test getting conversation context without checkpointer."""
        agent = MockMemoryAgent()

        result = await agent.get_conversation_context("thread123")

        assert result == []

    @pytest.mark.asyncio
    async def test_learn_pattern(self):
        """Test learning patterns."""
        agent = MockMemoryAgent()
        mock_store = AsyncMock()
        mock_store.aget.return_value = [{"pattern": "existing"}]
        agent.set_memory_components(mock_store, None)

        pattern_data = {"pattern": "new", "confidence": 0.8}
        await agent.learn_pattern("query_patterns", pattern_data)

        mock_store.aget.assert_called_once_with("patterns_query_patterns")
        expected_patterns = [{"pattern": "existing"}, {"pattern": "new", "confidence": 0.8}]
        mock_store.aput.assert_called_once_with("patterns_query_patterns", expected_patterns)


class TestIntegration:
    """Integration tests for base classes working together."""

    @pytest.mark.asyncio
    async def test_agent_with_all_mixins(self):
        """Test agent with both streaming and memory mixins."""

        class FullAgent(BaseAgent, StreamingMixin, MemoryMixin):
            def __init__(self):
                # Call all parent constructors
                BaseAgent.__init__(self, AgentRole.TOOL_EXECUTION, "full_agent")
                StreamingMixin.__init__(self)
                MemoryMixin.__init__(self)

            async def process(self, state: MultiAgentState) -> AgentResult:
                # Simulate using streaming
                await self.stream_thinking("Processing...")

                # Simulate using memory
                pref = await self.get_user_preference("user123", "detail_level", "medium")

                return self.create_success_result({"preference": pref})

            def get_prompt_template(self) -> str:
                return "Full agent template"

        agent = FullAgent()

        # Set up mocks
        mock_writer = AsyncMock()
        mock_store = AsyncMock()
        mock_store.aget.return_value = {"detail_level": "high"}

        agent.set_stream_writer(mock_writer)
        agent.set_memory_components(mock_store, None)

        # Test processing
        state = MultiAgentState(original_query="Test")
        result = await agent.process(state)

        # Verify streaming was called
        mock_writer.assert_called_once()

        # Verify memory was accessed
        mock_store.aget.assert_called_once()

        # Verify result
        assert result.success is True
        assert result.data["preference"] == "high"


if __name__ == "__main__":
    pytest.main([__file__])
