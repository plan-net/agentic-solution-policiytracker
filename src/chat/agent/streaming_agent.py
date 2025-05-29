"""Streaming agent with intelligent thinking output."""

import logging
import asyncio
from typing import AsyncGenerator, List, Dict, Any
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish

from .simple_agent import SimplePoliticalAgent
from ..utils.thinking_formatter import ThinkingFormatter

logger = logging.getLogger(__name__)


class StreamingThinkingHandler(BaseCallbackHandler):
    """Callback handler to capture agent actions for thinking output."""
    
    def __init__(self, thinking_formatter: ThinkingFormatter):
        self.thinking_formatter = thinking_formatter
        self.thoughts = []
        self.current_tool = None
        self.tool_results = {}
    
    def on_agent_action(self, action: AgentAction, **kwargs) -> Any:
        """Called when agent decides to use a tool."""
        self.current_tool = action.tool
        tool_input = str(action.tool_input)
        
        # Generate thinking for tool execution
        thinking = self.thinking_formatter.format_tool_execution(
            tool_name=action.tool,
            tool_input=tool_input,
            stage="starting"
        )
        self.thoughts.append(thinking)
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> Any:
        """Called when agent finishes."""
        if self.current_tool:
            thinking = self.thinking_formatter.format_tool_execution(
                tool_name=self.current_tool,
                tool_input="",
                stage="completed"
            )
            self.thoughts.append(thinking)
    
    def on_tool_end(self, output: str, **kwargs) -> Any:
        """Called when a tool finishes."""
        if self.current_tool and output:
            # Summarize tool output
            summary = self._summarize_output(output)
            insights = self._extract_insights(output)
            
            thinking = self.thinking_formatter.format_tool_results(
                tool_name=self.current_tool,
                result_summary=summary,
                insights=insights
            )
            self.thoughts.append(thinking)
    
    def _summarize_output(self, output: str) -> str:
        """Summarize tool output for thinking."""
        if len(output) < 100:
            return output
        
        # Simple summarization
        lines = output.split('\n')
        first_line = lines[0] if lines else ""
        
        if "entities" in output.lower():
            entity_count = output.lower().count("entity")
            return f"{entity_count} entities and relationships found"
        elif "results" in output.lower():
            return f"Analysis completed with multiple insights"
        else:
            return first_line[:80] + "..." if len(first_line) > 80 else first_line
    
    def _extract_insights(self, output: str) -> List[str]:
        """Extract key insights from tool output."""
        insights = []
        
        # Look for common insight patterns
        if "relationship" in output.lower():
            insights.append("Relationship patterns identified")
        if "impact" in output.lower():
            insights.append("Impact analysis completed")
        if "temporal" in output.lower() or "time" in output.lower():
            insights.append("Temporal patterns detected")
        if "community" in output.lower():
            insights.append("Community structures found")
        
        return insights[:2]  # Limit to 2 insights


class StreamingPoliticalAgent:
    """Enhanced political agent with streaming and intelligent thinking."""
    
    def __init__(self, graphiti_client, openai_api_key: str):
        # Initialize base agent
        self.base_agent = SimplePoliticalAgent(graphiti_client, openai_api_key)
        self.thinking_formatter = ThinkingFormatter()
        
        # Create streaming callback handler
        self.thinking_handler = StreamingThinkingHandler(self.thinking_formatter)
        
        # Add callback to agent
        self.base_agent.agent.callbacks = [self.thinking_handler]
    
    async def stream_query(self, query: str) -> AsyncGenerator[str, None]:
        """Stream query with intelligent thinking output."""
        try:
            logger.info(f"Streaming query with intelligent thinking: {query}")
            
            # Clean query
            clean_query = query.replace("search", "").strip()
            if not clean_query:
                clean_query = query
            
            # Phase 1: Query Understanding
            entities = self.thinking_formatter.extract_entities_from_query(clean_query)
            intent = self.thinking_formatter.determine_query_intent(clean_query)
            complexity = self.thinking_formatter.determine_complexity(clean_query, entities)
            
            understanding_thinking = self.thinking_formatter.format_query_understanding(
                query=clean_query,
                intent=intent,
                entities=entities,
                complexity=complexity
            )
            yield understanding_thinking
            
            # Small delay for UX
            await asyncio.sleep(0.1)
            
            # Phase 2: Execute agent (this will show actual tool usage)
            self.thinking_handler.thoughts = []  # Reset thoughts
            
            # Run agent and capture real tool execution
            result = await self.base_agent.agent.ainvoke({"input": clean_query})
            
            # Stream captured thoughts from actual execution
            for thought in self.thinking_handler.thoughts:
                yield thought
                await asyncio.sleep(0.05)
            
            # Phase 3: Synthesis
            if isinstance(result, dict):
                response = result.get("output", "I couldn't generate a response.")
            else:
                response = str(result)
            findings = self._extract_findings(response)
            synthesis_thinking = self.thinking_formatter.format_synthesis(
                findings=findings,
                confidence="high",
                source_count=len(entities)
            )
            yield synthesis_thinking
            
            await asyncio.sleep(0.1)
            
            # Phase 4: Stream final response
            yield "## Analysis Results\n\n"
            yield response
            
            logger.info("Streaming with intelligent thinking completed successfully")
            
        except Exception as e:
            logger.error(f"Streaming agent error: {e}")
            yield f"<think>\n❌ ERROR\nEncountered an error: {str(e)}\n</think>\n\n"
            yield f"I encountered an error while processing your request: {str(e)}"
    
    def _predict_tools(self, intent: str, entities: List[str], complexity: str) -> List[str]:
        """Predict which tools will be used based on query analysis."""
        tools = ["search"]  # Always start with search
        
        if intent == "Information lookup":
            tools.extend(["get_entity_details"])
        elif intent == "Relationship analysis":
            tools.extend(["get_entity_relationships", "traverse_from_entity"])
        elif intent == "Impact analysis":
            tools.extend(["analyze_entity_impact", "get_entity_relationships"])
        elif intent == "Temporal analysis":
            tools.extend(["get_entity_timeline", "search_by_date_range"])
        elif intent == "Community analysis":
            tools.extend(["get_communities", "get_policy_clusters"])
        else:
            tools.extend(["get_entity_details", "get_entity_relationships"])
        
        # Add complexity-based tools
        if complexity == "complex":
            tools.extend(["find_paths_between_entities", "get_entity_neighbors"])
        
        return tools[:4]  # Limit to 4 predicted tools
    
    def _extract_findings(self, response: str) -> List[str]:
        """Extract key findings from agent response."""
        findings = []
        
        # Simple extraction based on common patterns
        sentences = response.split('. ')
        for sentence in sentences[:5]:  # Look at first 5 sentences
            if any(keyword in sentence.lower() for keyword in ['regulates', 'requires', 'applies to', 'establishes']):
                findings.append(sentence.strip())
            elif any(keyword in sentence.lower() for keyword in ['relationship', 'connection', 'impact']):
                findings.append(sentence.strip())
        
        # Ensure we have at least some findings
        if not findings and sentences:
            findings = [sentences[0].strip(), sentences[1].strip() if len(sentences) > 1 else ""]
        
        return [f for f in findings if f][:3]  # Max 3 findings
    
    # Delegate other methods to base agent
    async def process_query(self, query: str) -> str:
        """Non-streaming query processing (fallback)."""
        try:
            return await self.base_agent.process_query(query)
        except Exception as e:
            logger.error(f"Error in process_query fallback: {e}")
            return f"I encountered an error while processing your request: {str(e)}"