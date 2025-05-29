"""Enhanced agent state management for LangGraph workflow."""

from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState, add_messages


class QueryAnalysis(BaseModel):
    """Results from query analysis."""
    intent: str  # Primary intent category
    complexity: str  # Simple/Medium/Complex
    primary_entity: Optional[str] = None
    secondary_entities: List[str] = Field(default_factory=list)
    key_relationships: List[str] = Field(default_factory=list)
    temporal_scope: str = "current"
    analysis_strategy: str = ""


class ToolPlan(BaseModel):
    """Plan for tool execution sequence."""
    tool_sequence: List[str] = Field(default_factory=list)
    rationale: str = ""
    expected_insights: str = ""
    thinking_narrative: str = ""


class ToolResult(BaseModel):
    """Result from individual tool execution."""
    tool_name: str
    success: bool
    output: str = ""
    insights: List[str] = Field(default_factory=list)
    entities_found: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ThinkingState(BaseModel):
    """State for tracking thinking output."""
    current_phase: str = "understanding"
    thinking_content: List[str] = Field(default_factory=list)
    tool_reasoning: str = ""
    synthesis_progress: str = ""


class AgentState(MessagesState):
    """Enhanced state for the political monitoring chat agent."""
    
    # Core query processing
    original_query: str = ""
    processed_query: str = ""
    query_analysis: Optional[QueryAnalysis] = None
    
    # Tool planning and execution
    tool_plan: Optional[ToolPlan] = None
    executed_tools: List[str] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    
    # Thinking and reasoning state
    thinking_state: ThinkingState = Field(default_factory=ThinkingState)
    
    # Progress tracking
    current_step: str = "start"
    iterations: int = 0
    max_iterations: int = 8
    
    # Memory and context (using LangChain memory)
    conversation_memory: Dict[str, Any] = Field(default_factory=dict)
    session_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Final output
    synthesis_complete: bool = False
    final_response: str = ""
    
    # Streaming state
    is_streaming: bool = False
    stream_buffer: List[str] = Field(default_factory=list)