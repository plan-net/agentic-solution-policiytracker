"""Thinking output formatter for streaming responses."""

import re
from typing import Dict, Any, List
from datetime import datetime

class ThinkingFormatter:
    """Formats thinking output for educational and transparent agent responses."""
    
    def __init__(self):
        self.educational_notes = {
            "search": "🔍 Graph search finds relationships that keyword search misses",
            "entity_details": "📊 Deep-dive reveals comprehensive entity information and connections",
            "entity_relationships": "🔗 Mapping relationships shows regulatory pathways and dependencies", 
            "traverse_from_entity": "🗺️ Multi-hop traversal reveals indirect impacts and cascading effects",
            "find_paths_between_entities": "🛤️ Path finding shows connection routes through intermediate entities",
            "analyze_entity_impact": "💥 Impact analysis reveals who affects whom and how changes propagate",
            "search_by_date_range": "📅 Temporal search tracks policy evolution and timing patterns",
            "get_entity_timeline": "⏰ Timeline view shows how entities evolved over time",
            "get_communities": "🏘️ Community detection reveals natural groupings in regulatory landscape",
            "get_policy_clusters": "📋 Policy clustering identifies thematic groups and regulatory families"
        }
    
    def format_query_understanding(self, query: str, intent: str = None, entities: List[str] = None, complexity: str = "medium") -> str:
        """Format query understanding thinking."""
        thinking = "<think>\n🎯 UNDERSTANDING QUERY\n"
        thinking += f"Query: {query}\n"
        
        if intent:
            thinking += f"Intent: {intent}\n"
        
        if entities:
            thinking += f"Key entities detected: {', '.join(entities[:3])}\n"
            if len(entities) > 3:
                thinking += f"+ {len(entities) - 3} more entities\n"
        
        thinking += f"Complexity level: {complexity}\n"
        thinking += "Strategy: Use graph-based analysis for comprehensive insights\n"
        thinking += "</think>\n"
        
        return thinking
    
    def format_tool_selection(self, selected_tools: List[str], reasoning: str = None) -> str:
        """Format tool selection thinking."""
        thinking = "<think>\n🛠️ TOOL SELECTION\n"
        thinking += f"Selected tools: {', '.join(selected_tools)}\n"
        
        if reasoning:
            thinking += f"Strategy: {reasoning}\n"
        else:
            thinking += "Strategy: Multi-tool approach for comprehensive analysis\n"
        
        thinking += "Expected outcome: Deep graph-based insights with source citations\n"
        thinking += "</think>\n"
        
        return thinking
    
    def format_tool_execution(self, tool_name: str, tool_input: str, stage: str = "starting") -> str:
        """Format tool execution thinking."""
        clean_tool_name = tool_name.replace("Tool", "").replace("_", " ").title()
        
        if stage == "starting":
            thinking = f"<think>\n🔧 EXECUTING: {clean_tool_name}\n"
            thinking += f"Input: {tool_input[:100]}{'...' if len(tool_input) > 100 else ''}\n"
            
            # Add educational note
            tool_key = tool_name.lower().replace("tool", "").replace("_", "_")
            if tool_key in self.educational_notes:
                thinking += f"💡 {self.educational_notes[tool_key]}\n"
            
            thinking += "</think>\n"
        
        elif stage == "completed":
            thinking = f"<think>\n✅ COMPLETED: {clean_tool_name}\n"
            thinking += "</think>\n"
        
        return thinking
    
    def format_tool_results(self, tool_name: str, result_summary: str, insights: List[str] = None, next_action: str = None) -> str:
        """Format tool results thinking."""
        clean_tool_name = tool_name.replace("Tool", "").replace("_", " ").title()
        
        thinking = f"<think>\n📊 RESULTS: {clean_tool_name}\n"
        thinking += f"Found: {result_summary}\n"
        
        if insights:
            thinking += "Key insights:\n"
            for insight in insights[:2]:  # Limit to 2 insights to avoid overwhelming
                thinking += f"  • {insight}\n"
        
        if next_action:
            thinking += f"Next: {next_action}\n"
        
        thinking += "</think>\n"
        
        return thinking
    
    def format_synthesis(self, findings: List[str], confidence: str = "high", source_count: int = 0) -> str:
        """Format synthesis thinking."""
        thinking = "<think>\n💡 SYNTHESIS\n"
        
        thinking += "Key findings:\n"
        for finding in findings[:3]:  # Limit to top 3 findings
            thinking += f"  • {finding}\n"
        
        thinking += f"\nGraph advantages utilized:\n"
        thinking += "  • Multi-hop relationship analysis\n"
        thinking += "  • Temporal pattern detection\n"
        thinking += "  • Network effect identification\n"
        
        thinking += f"\nConfidence: {confidence.title()}\n"
        if source_count > 0:
            thinking += f"Sources: {source_count} documents analyzed\n"
        
        thinking += "</think>\n"
        
        return thinking
    
    def extract_entities_from_query(self, query: str) -> List[str]:
        """Extract potential entities from query text."""
        # Simple entity extraction - look for capitalized terms, known patterns
        entities = []
        
        # Common patterns
        patterns = [
            r'\b(EU|European Union)\b',
            r'\b(AI Act|GDPR|DSA|DMA)\b',
            r'\b([A-Z][a-z]+ Act)\b',
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # Two-word proper nouns
            r'\b(Meta|Google|Apple|Microsoft|Amazon)\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend([match for match in matches if isinstance(match, str)])
        
        return list(set(entities))
    
    def determine_query_intent(self, query: str) -> str:
        """Determine the intent of the query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['what is', 'define', 'explain']):
            return "Information lookup"
        elif any(word in query_lower for word in ['how does', 'relationship', 'connect']):
            return "Relationship analysis"
        elif any(word in query_lower for word in ['impact', 'effect', 'affect']):
            return "Impact analysis"
        elif any(word in query_lower for word in ['when', 'timeline', 'history']):
            return "Temporal analysis"
        elif any(word in query_lower for word in ['compare', 'difference', 'versus']):
            return "Comparative analysis"
        elif any(word in query_lower for word in ['community', 'group', 'cluster']):
            return "Community analysis"
        else:
            return "General inquiry"
    
    def determine_complexity(self, query: str, entities: List[str]) -> str:
        """Determine query complexity based on content."""
        query_lower = query.lower()
        
        # Complex indicators
        complex_words = ['relationship', 'impact', 'cascade', 'network', 'community', 'evolution']
        has_complex_words = any(word in query_lower for word in complex_words)
        
        # Multiple entities or complex structure
        multiple_entities = len(entities) > 2
        long_query = len(query.split()) > 10
        
        if has_complex_words or multiple_entities or long_query:
            return "complex"
        elif len(entities) > 0 or len(query.split()) > 5:
            return "medium"
        else:
            return "simple"