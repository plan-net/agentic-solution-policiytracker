"""Enhanced multi-agent state management with memory and streaming support."""

from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState, add_messages
from langchain_core.messages import BaseMessage


class QueryAnalysis(BaseModel):
    """Results from query understanding agent."""
    intent: str  # Primary intent category
    complexity: str  # Simple/Medium/Complex
    primary_entity: Optional[str] = None
    secondary_entities: List[str] = Field(default_factory=list)
    key_relationships: List[str] = Field(default_factory=list)
    temporal_scope: str = "current"
    analysis_strategy: str = ""
    confidence: float = 0.8


class ToolPlan(BaseModel):
    """Plan from tool planning agent."""
    tool_sequence: List[str] = Field(default_factory=list)
    rationale: str = ""
    expected_insights: str = ""
    strategy_type: str = ""  # comprehensive, focused, exploratory
    estimated_execution_time: int = 30  # seconds


class ToolResult(BaseModel):
    """Result from individual tool execution."""
    tool_name: str
    success: bool
    output: str = ""
    insights: List[str] = Field(default_factory=list)
    entities_found: List[str] = Field(default_factory=list)
    source_citations: List[str] = Field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None


class AgentTransition(BaseModel):
    """Information about agent transitions."""
    from_agent: str
    to_agent: str
    transition_reason: str
    timestamp: float
    data_passed: Dict[str, Any] = Field(default_factory=dict)


class MultiAgentState(MessagesState):
    """Enhanced state for multi-agent political monitoring system."""
    
    # Core query processing
    original_query: str = ""
    processed_query: str = ""
    query_analysis: Optional[Dict[str, Any]] = None  # From QueryAnalysis.model_dump()
    
    # Agent workflow tracking
    current_agent: str = "query_understanding"
    agent_sequence: List[str] = Field(default_factory=list)
    agent_transitions: List[AgentTransition] = Field(default_factory=list)
    
    # Tool planning and execution
    tool_plan: Optional[Dict[str, Any]] = None  # From ToolPlan.model_dump()
    executed_tools: List[str] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)  # From ToolResult.model_dump()
    
    # Memory and session management
    session_id: Optional[str] = None
    thread_id: Optional[str] = None
    conversation_history: List[BaseMessage] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    learned_patterns: Dict[str, Any] = Field(default_factory=dict)
    
    # Streaming and progress
    is_streaming: bool = False
    thinking_updates: List[str] = Field(default_factory=list)
    progress_indicators: List[str] = Field(default_factory=list)
    custom_stream_data: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Final output
    synthesis_complete: bool = False
    final_response: str = ""
    response_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Error handling and monitoring
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Performance tracking
    total_execution_time: float = 0.0
    agent_execution_times: Dict[str, float] = Field(default_factory=dict)


# Legacy compatibility - keep existing AgentState for gradual migration
class AgentState(MessagesState):
    """Legacy state - maintained for backward compatibility during migration."""
    
    # Core query processing
    original_query: str = ""
    processed_query: str = ""
    query_analysis: Optional[QueryAnalysis] = None
    
    # Tool planning and execution
    tool_plan: Optional[ToolPlan] = None
    executed_tools: List[str] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    
    # Progress tracking
    current_step: str = "start"
    iterations: int = 0
    max_iterations: int = 8
    
    # Memory and context
    conversation_memory: Dict[str, Any] = Field(default_factory=dict)
    session_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Final output
    synthesis_complete: bool = False
    final_response: str = ""
    
    # Streaming state
    is_streaming: bool = False
    stream_buffer: List[str] = Field(default_factory=list)