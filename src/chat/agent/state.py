"""Agent state management for LangGraph workflow."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState


class SearchResult(BaseModel):
    """Individual search result from Graphiti."""
    fact: str
    relationship: Optional[str] = None
    source_entities: List[str] = Field(default_factory=list)
    target_entities: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class ExplorationPlan(BaseModel):
    """Plan for exploring the knowledge graph."""
    query_intent: str  # What the user is trying to find
    search_strategy: str  # How to approach the search
    tools_to_use: List[str] = Field(default_factory=list)
    search_depth: int = 1  # How deep to search
    expected_entities: List[str] = Field(default_factory=list)


class AgentState(MessagesState):
    """Extended state for the political monitoring chat agent."""
    
    # User query understanding
    original_query: str = ""
    processed_query: str = ""
    query_intent: str = ""
    
    # Exploration planning
    exploration_plan: Optional[ExplorationPlan] = None
    
    # Search results
    search_results: List[SearchResult] = Field(default_factory=list)
    total_results_found: int = 0
    
    # Agent reasoning
    iterations: int = 0
    max_iterations: int = 10
    is_satisfied: bool = False
    confidence_score: float = 0.0
    
    # Context and memory
    session_context: Dict[str, Any] = Field(default_factory=dict)
    previous_searches: List[str] = Field(default_factory=list)
    
    # Final response
    final_response: str = ""
    citations: List[str] = Field(default_factory=list)