"""Advanced streaming utilities for multi-agent system."""

from typing import Dict, Any, AsyncGenerator, Optional, List
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of streaming events."""
    THINKING = "thinking"
    PROGRESS = "progress"
    AGENT_TRANSITION = "agent_transition"
    TOOL_EXECUTION = "tool_execution"
    LLM_TOKEN = "llm_token"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class StreamEvent:
    """Standard streaming event structure."""
    event_type: StreamEventType
    agent_name: str
    content: str
    metadata: Dict[str, Any]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "agent_name": self.agent_name,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class StreamingManager:
    """Manages streaming events across the multi-agent system."""
    
    def __init__(self):
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._active_streams: List[AsyncGenerator] = []
        self._stream_writer = None
        self._stream_callback = None
    
    def set_stream_writer(self, writer):
        """Set LangGraph's stream writer."""
        self._stream_writer = writer
    
    def get_stream_writer(self):
        """Get the current stream writer."""
        return self._stream_writer
    
    def set_stream_callback(self, callback):
        """Set a custom streaming callback."""
        self._stream_callback = callback
    
    async def emit_thinking(
        self, 
        agent_name: str, 
        thought: str, 
        metadata: Dict[str, Any] = None
    ) -> None:
        """Emit thinking output from an agent."""
        if self._stream_writer:
            await self._stream_writer({
                "thinking": thought,
                "agent": agent_name,
                "metadata": metadata or {}
            })
    
    async def emit_progress(
        self, 
        agent_name: str, 
        progress: str, 
        percentage: Optional[float] = None
    ) -> None:
        """Emit progress update from an agent."""
        if self._stream_writer:
            await self._stream_writer({
                "progress": progress,
                "agent": agent_name,
                "percentage": percentage,
                "event_type": "progress"
            })
    
    async def emit_agent_transition(
        self, 
        from_agent: str, 
        to_agent: str, 
        reason: str = ""
    ) -> None:
        """Emit agent transition event."""
        if self._stream_writer:
            await self._stream_writer({
                "transition": f"Transitioning from {from_agent} to {to_agent}",
                "from_agent": from_agent,
                "to_agent": to_agent,
                "reason": reason,
                "event_type": "agent_transition"
            })
    
    async def emit_tool_execution(
        self, 
        agent_name: str, 
        tool_name: str, 
        status: str,
        result_preview: str = ""
    ) -> None:
        """Emit tool execution update."""
        if self._stream_writer:
            await self._stream_writer({
                "tool_execution": f"Executing {tool_name}: {status}",
                "agent": agent_name,
                "tool_name": tool_name,
                "status": status,
                "result_preview": result_preview,
                "event_type": "tool_execution"
            })
    
    async def emit_error(
        self, 
        agent_name: str, 
        error_message: str, 
        error_type: str = "error"
    ) -> None:
        """Emit error event."""
        if self._stream_writer:
            await self._stream_writer({
                "error": error_message,
                "agent": agent_name,
                "error_type": error_type,
                "event_type": "error"
            })


class ThinkingTemplates:
    """Templates for generating thinking output for each agent."""
    
    QUERY_UNDERSTANDING = {
        "start": "Analyzing your question to understand what type of political or regulatory information you're seeking...",
        "intent_analysis": "Identifying the primary intent: {intent}. This helps me choose the right analysis approach.",
        "entity_extraction": "I've identified these key entities: {entities}. These will guide my search strategy.",
        "complexity_assessment": "Query complexity: {complexity}. This determines how many tools I'll need to use.",
        "temporal_scope": "Time scope: {temporal_scope}. Understanding the temporal dimension is crucial for political analysis.",
        "strategy_formation": "Based on my analysis, I'll use a {strategy} approach to explore the knowledge graph.",
        "complete": "Query understanding complete. I have a clear picture of what you're looking for."
    }
    
    TOOL_PLANNING = {
        "start": "Now I need to plan the optimal sequence of tools to gather comprehensive information...",
        "strategy_selection": "For {intent} queries, I'll use a {strategy_type} strategy with {tool_count} tools.",
        "tool_sequencing": "I'll start with {first_tool} to map the landscape, then use {subsequent_tools} for deeper analysis.",
        "optimization": "This sequence is optimized for {optimization_reason}, based on learned patterns.",
        "time_estimation": "I estimate this will take approximately {estimated_time} seconds to execute thoroughly.",
        "contingency": "I have backup strategies ready if the primary approach doesn't yield sufficient information.",
        "complete": "Execution plan ready. This approach should provide comprehensive insights about your query."
    }
    
    TOOL_EXECUTION = {
        "start": "Beginning systematic exploration of the knowledge graph using {tool_count} specialized tools...",
        "tool_start": "Executing {tool_name}: {purpose}",
        "tool_progress": "Found {entity_count} entities and {relationship_count} relationships so far...",
        "tool_complete": "Completed {tool_name}: {insight_summary}",
        "synthesis_start": "Synthesizing findings from {completed_tools} tools to build a comprehensive picture...",
        "pattern_detection": "I'm seeing interesting patterns: {patterns}",
        "source_validation": "Verifying sources and ensuring citation accuracy...",
        "quality_check": "Quality check: {quality_metrics}",
        "complete": "Tool execution complete. I've gathered {total_facts} facts from {source_count} sources."
    }
    
    RESPONSE_SYNTHESIS = {
        "start": "Combining all findings into a comprehensive, well-cited response...",
        "structure_planning": "Organizing information by {organization_method} to best address your question.",
        "citation_formatting": "Ensuring all {citation_count} sources are properly attributed with links and context.",
        "insight_highlighting": "Identifying the most significant insights that emerged from the graph analysis.",
        "relationship_mapping": "Explaining the key relationships: {key_relationships}",
        "context_building": "Adding essential political and regulatory context to help you understand the implications.",
        "follow_up_generation": "Preparing related questions you might want to explore next.",
        "quality_review": "Final quality review: ensuring accuracy, completeness, and clarity.",
        "complete": "Response synthesis complete. I've created a comprehensive answer with full source attribution."
    }


class StreamingThinkingGenerator:
    """Enhanced generator for natural thinking output with dynamic adaptation."""
    
    def __init__(self, streaming_manager: StreamingManager):
        self.streaming_manager = streaming_manager
        self.templates = ThinkingTemplates()
        self.user_preferences = {}
        self.thinking_history = []
        self.adaptive_timing = True
        self.context_aware = True
    
    def set_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """Set user preferences for thinking output customization."""
        self.user_preferences = preferences
    
    def get_adaptive_delay(self, content_complexity: str, user_speed_pref: str = "normal") -> float:
        """Calculate adaptive delay based on content complexity and user preferences."""
        base_delays = {
            "simple": 0.3,
            "normal": 0.6,
            "complex": 1.0
        }
        
        speed_multipliers = {
            "fast": 0.5,
            "normal": 1.0,
            "slow": 1.5,
            "detailed": 2.0
        }
        
        base_delay = base_delays.get(content_complexity, 0.6)
        speed_mult = speed_multipliers.get(user_speed_pref, 1.0)
        
        return base_delay * speed_mult if self.adaptive_timing else 0.5
    
    async def emit_contextual_thinking(
        self, 
        agent_name: str, 
        template_key: str, 
        context: Dict[str, Any],
        complexity: str = "normal"
    ) -> None:
        """Emit thinking with contextual adaptation and user preferences."""
        template_dict = getattr(self.templates, agent_name.upper(), {})
        template = template_dict.get(template_key, "Processing...")
        
        # Format template with context
        try:
            formatted_text = template.format(**context)
        except KeyError:
            formatted_text = template
        
        # Record thinking for learning
        self.thinking_history.append({
            "agent": agent_name,
            "template_key": template_key,
            "context": context,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        await self.streaming_manager.emit_thinking(agent_name, formatted_text)
        
        # Adaptive delay
        user_speed = self.user_preferences.get("thinking_speed", "normal")
        delay = self.get_adaptive_delay(complexity, user_speed)
        if delay > 0:
            await asyncio.sleep(delay)
    
    async def generate_query_understanding_thinking(
        self, 
        agent_name: str, 
        query: str,
        analysis_results: Dict[str, Any]
    ) -> None:
        """Generate thinking output for query understanding phase."""
        templates = self.templates.QUERY_UNDERSTANDING
        
        await self.streaming_manager.emit_thinking(agent_name, templates["start"])
        await asyncio.sleep(0.8)
        
        if "intent" in analysis_results:
            await self.streaming_manager.emit_thinking(
                agent_name, 
                templates["intent_analysis"].format(intent=analysis_results["intent"])
            )
            await asyncio.sleep(0.6)
        
        if "entities" in analysis_results and analysis_results["entities"]:
            entity_list = ", ".join(analysis_results["entities"][:3])
            await self.streaming_manager.emit_thinking(
                agent_name,
                templates["entity_extraction"].format(entities=entity_list)
            )
            await asyncio.sleep(0.7)
        
        if "complexity" in analysis_results:
            await self.streaming_manager.emit_thinking(
                agent_name,
                templates["complexity_assessment"].format(complexity=analysis_results["complexity"])
            )
            await asyncio.sleep(0.5)
        
        await self.streaming_manager.emit_thinking(agent_name, templates["complete"])
    
    async def generate_tool_planning_thinking(
        self, 
        agent_name: str,
        plan: Dict[str, Any]
    ) -> None:
        """Generate thinking output for tool planning phase."""
        templates = self.templates.TOOL_PLANNING
        
        await self.streaming_manager.emit_thinking(agent_name, templates["start"])
        await asyncio.sleep(0.8)
        
        if "strategy_type" in plan and "tool_sequence" in plan:
            await self.streaming_manager.emit_thinking(
                agent_name,
                templates["strategy_selection"].format(
                    intent=plan.get("intent", "analysis"),
                    strategy_type=plan["strategy_type"],
                    tool_count=len(plan["tool_sequence"])
                )
            )
            await asyncio.sleep(0.7)
        
        if "tool_sequence" in plan and len(plan["tool_sequence"]) > 0:
            first_tool = plan["tool_sequence"][0]
            subsequent_tools = ", ".join(plan["tool_sequence"][1:3])
            await self.streaming_manager.emit_thinking(
                agent_name,
                templates["tool_sequencing"].format(
                    first_tool=first_tool,
                    subsequent_tools=subsequent_tools
                )
            )
            await asyncio.sleep(0.6)
        
        await self.streaming_manager.emit_thinking(agent_name, templates["complete"])
    
    async def generate_tool_execution_thinking(
        self, 
        agent_name: str,
        tool_name: str,
        execution_status: str,
        results_summary: Dict[str, Any] = None
    ) -> None:
        """Generate thinking output for tool execution."""
        templates = self.templates.TOOL_EXECUTION
        
        if execution_status == "start":
            await self.streaming_manager.emit_thinking(
                agent_name,
                templates["tool_start"].format(
                    tool_name=tool_name,
                    purpose=self._get_tool_purpose(tool_name)
                )
            )
        elif execution_status == "progress" and results_summary:
            await self.streaming_manager.emit_thinking(
                agent_name,
                templates["tool_progress"].format(
                    entity_count=results_summary.get("entity_count", 0),
                    relationship_count=results_summary.get("relationship_count", 0)
                )
            )
        elif execution_status == "complete" and results_summary:
            await self.streaming_manager.emit_thinking(
                agent_name,
                templates["tool_complete"].format(
                    tool_name=tool_name,
                    insight_summary=results_summary.get("insight_summary", "valuable insights gathered")
                )
            )
    
    async def generate_synthesis_thinking(
        self, 
        agent_name: str,
        synthesis_stage: str,
        stage_data: Dict[str, Any] = None
    ) -> None:
        """Generate thinking output for response synthesis."""
        templates = self.templates.RESPONSE_SYNTHESIS
        
        if synthesis_stage in templates:
            thinking_text = templates[synthesis_stage]
            if stage_data:
                thinking_text = thinking_text.format(**stage_data)
            
            await self.streaming_manager.emit_thinking(agent_name, thinking_text)
    
    def _get_tool_purpose(self, tool_name: str) -> str:
        """Get human-readable purpose for a tool."""
        purposes = {
            "search": "finding relevant facts and entities in the knowledge graph",
            "get_entity_details": "gathering comprehensive information about specific entities",
            "get_entity_relationships": "exploring connections and relationships between entities",
            "get_entity_timeline": "tracking how entities have evolved over time",
            "find_similar_entities": "discovering related entities and patterns",
            "traverse_from_entity": "following multi-hop relationships through the network",
            "find_paths_between_entities": "finding connection paths between different entities",
            "get_entity_neighbors": "examining immediate connections and relationships",
            "analyze_entity_impact": "understanding influence and impact networks",
            "search_by_date_range": "exploring temporal patterns and time-based events",
            "get_entity_history": "tracking historical changes and evolution",
            "find_concurrent_events": "finding related events that happened simultaneously",
            "track_policy_evolution": "following how policies have changed over time",
            "get_communities": "discovering clusters and communities of related entities",
            "get_community_members": "exploring membership and composition of entity groups",
            "get_policy_clusters": "identifying related policies and regulatory themes"
        }
        return purposes.get(tool_name, "specialized knowledge graph analysis")


# Helper functions for stream processing

async def format_stream_for_openai_api(
    stream_events: AsyncGenerator[Dict[str, Any], None]
) -> AsyncGenerator[str, None]:
    """Format streaming events for OpenAI-compatible API."""
    async for event in stream_events:
        if event.get("event_type") == "thinking":
            yield f"<think>{event.get('content', '')}</think>\n"
        elif event.get("event_type") == "progress":
            yield f"⚙️ {event.get('content', '')}\n"
        elif event.get("event_type") == "agent_transition":
            yield f"🔄 {event.get('content', '')}\n"
        elif event.get("event_type") == "llm_token":
            yield event.get("content", "")
        else:
            # Other event types
            yield f"{event.get('content', '')}\n"


async def aggregate_stream_events(
    events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Aggregate streaming events for analysis."""
    aggregated = {
        "total_events": len(events),
        "event_types": {},
        "agents_involved": set(),
        "thinking_content": [],
        "progress_updates": [],
        "transitions": []
    }
    
    for event in events:
        event_type = event.get("event_type", "unknown")
        aggregated["event_types"][event_type] = aggregated["event_types"].get(event_type, 0) + 1
        
        if "agent" in event:
            aggregated["agents_involved"].add(event["agent"])
        
        if event_type == "thinking":
            aggregated["thinking_content"].append(event.get("content", ""))
        elif event_type == "progress":
            aggregated["progress_updates"].append(event.get("content", ""))
        elif event_type == "agent_transition":
            aggregated["transitions"].append(event.get("content", ""))
    
    aggregated["agents_involved"] = list(aggregated["agents_involved"])
    return aggregated