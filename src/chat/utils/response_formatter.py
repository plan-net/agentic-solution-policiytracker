"""Response formatting utilities for the chat agent."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Utility class for formatting agent responses with consistent styling."""
    
    def __init__(self):
        """Initialize the response formatter."""
        pass
    
    def format_entity_summary(self, entity_name: str, facts: List[str], 
                            source_count: int = 0) -> str:
        """Format a summary for an entity with key facts."""
        response = f"## {entity_name}\n\n"
        
        if facts:
            response += "**Key Information:**\n"
            for i, fact in enumerate(facts[:5], 1):
                # Clean up the fact text
                clean_fact = self._clean_fact_text(fact)
                response += f"{i}. {clean_fact}\n"
            
            if len(facts) > 5:
                response += f"\n*... and {len(facts) - 5} more facts available*\n"
        
        if source_count > 0:
            response += f"\n*Based on information from {source_count} document(s)*\n"
        
        return response
    
    def format_relationship_network(self, entity_name: str, 
                                  relationships: List[Dict[str, Any]]) -> str:
        """Format a relationship network visualization."""
        response = f"## Relationship Network: {entity_name}\n\n"
        
        if not relationships:
            response += f"No relationships found for {entity_name}.\n"
            return response
        
        # Group by relationship type
        by_type = {}
        for rel in relationships:
            rel_type = rel.get('type', 'UNKNOWN')
            if rel_type not in by_type:
                by_type[rel_type] = []
            by_type[rel_type].append(rel)
        
        response += f"**Found {len(relationships)} relationships across {len(by_type)} types**\n\n"
        
        for rel_type, rels in sorted(by_type.items()):
            response += f"### {rel_type} ({len(rels)})\n"
            for rel in rels[:3]:  # Top 3 per type
                fact = self._clean_fact_text(rel.get('fact', ''))
                response += f"- {fact[:120]}{'...' if len(fact) > 120 else ''}\n"
            
            if len(rels) > 3:
                response += f"  *... and {len(rels) - 3} more*\n"
            response += "\n"
        
        return response
    
    def format_timeline(self, entity_name: str, events: List[Dict[str, Any]], 
                       days_back: int = 365) -> str:
        """Format a timeline of events for an entity."""
        response = f"## Timeline: {entity_name}\n\n"
        response += f"**Period**: Last {days_back} days\n\n"
        
        if not events:
            response += f"No timeline events found for {entity_name}.\n"
            return response
        
        # Sort events by timestamp if available, otherwise by relevance
        sorted_events = sorted(events, 
                             key=lambda x: x.get('timestamp', datetime.min),
                             reverse=True)
        
        response += "**Key Events:**\n"
        for i, event in enumerate(sorted_events[:10], 1):
            event_type = event.get('type', 'Event').title()
            fact = self._clean_fact_text(event.get('fact', ''))
            
            timestamp_str = ""
            if event.get('timestamp'):
                timestamp_str = f" ({event['timestamp'].strftime('%Y-%m-%d')})"
            
            response += f"{i}. **{event_type}**{timestamp_str}: {fact}\n"
        
        if len(events) > 10:
            response += f"\n*... and {len(events) - 10} more events*\n"
        
        return response
    
    def format_path_analysis(self, source: str, target: str, 
                           paths: List[Dict[str, Any]]) -> str:
        """Format connection path analysis between entities."""
        response = f"## Connection Analysis: {source} ↔ {target}\n\n"
        
        if not paths:
            response += f"No clear connection paths found.\n\n"
            response += "**Suggestions:**\n"
            response += "- Try using broader entity names\n"
            response += "- Explore each entity's network separately\n"
            response += "- Look for common regulatory frameworks\n"
            return response
        
        # Categorize paths
        direct_paths = [p for p in paths if p.get('type') == 'direct']
        indirect_paths = [p for p in paths if p.get('type') == 'indirect']
        
        if direct_paths:
            response += f"### Direct Connections ({len(direct_paths)})\n"
            for i, path in enumerate(direct_paths[:5], 1):
                fact = self._clean_fact_text(path.get('fact', ''))
                rel_type = path.get('relationship', 'CONNECTED')
                response += f"{i}. **{rel_type}**: {fact}\n"
            response += "\n"
        
        if indirect_paths:
            response += f"### Indirect Connections ({len(indirect_paths)})\n"
            for i, path in enumerate(indirect_paths[:5], 1):
                fact = self._clean_fact_text(path.get('fact', ''))
                response += f"{i}. {fact[:150]}{'...' if len(fact) > 150 else ''}\n"
            response += "\n"
        
        # Connection strength
        total = len(direct_paths) + len(indirect_paths)
        strength = "Strong" if len(direct_paths) > 2 else "Moderate" if total > 2 else "Weak"
        response += f"**Connection Strength**: {strength}\n"
        
        return response
    
    def format_community_analysis(self, communities: List[Dict[str, Any]], 
                                 focus_entity: Optional[str] = None) -> str:
        """Format community detection results."""
        response = "## Community Analysis\n\n"
        
        if not communities:
            response += "No clear communities detected in the current data.\n"
            return response
        
        response += f"**Detected {len(communities)} communities**\n\n"
        
        # Highlight the community containing the focus entity if specified
        focus_community = None
        if focus_entity:
            for i, comm in enumerate(communities):
                entities = comm.get('entities', [])
                if any(focus_entity.lower() in str(entity).lower() for entity in entities):
                    focus_community = i
                    break
        
        for i, community in enumerate(communities[:6], 1):  # Show top 6 communities
            entities = community.get('entities', [])
            themes = community.get('themes', [])
            
            # Mark focus community
            focus_marker = " ⭐" if i-1 == focus_community else ""
            response += f"### Community {i}{focus_marker}\n"
            response += f"**Size**: {len(entities)} entities\n"
            
            if themes:
                response += f"**Themes**: {', '.join(themes[:3])}\n"
            
            response += f"**Key Entities**: "
            response += ", ".join(str(entity) for entity in entities[:5])
            if len(entities) > 5:
                response += f" ... and {len(entities) - 5} more"
            response += "\n\n"
        
        if focus_entity and focus_community is not None:
            response += f"*{focus_entity} is in Community {focus_community + 1}*\n"
        
        return response
    
    def format_impact_analysis(self, entity_name: str, impacts: Dict[str, List[Dict]]) -> str:
        """Format impact analysis results."""
        response = f"## Impact Analysis: {entity_name}\n\n"
        
        direct = impacts.get('direct', [])
        indirect = impacts.get('indirect', [])
        mutual = impacts.get('mutual', [])
        
        total = len(direct) + len(indirect) + len(mutual)
        response += f"**Total Impact Relationships**: {total}\n\n"
        
        if direct:
            response += f"### Outbound Impact ({len(direct)} relationships)\n"
            response += f"*What {entity_name} affects:*\n"
            for impact in direct[:5]:
                fact = self._clean_fact_text(impact.get('fact', ''))
                response += f"- {fact}\n"
            if len(direct) > 5:
                response += f"  *... and {len(direct) - 5} more*\n"
            response += "\n"
        
        if indirect:
            response += f"### Inbound Impact ({len(indirect)} relationships)\n"
            response += f"*What affects {entity_name}:*\n"
            for impact in indirect[:5]:
                fact = self._clean_fact_text(impact.get('fact', ''))
                response += f"- {fact}\n"
            if len(indirect) > 5:
                response += f"  *... and {len(indirect) - 5} more*\n"
            response += "\n"
        
        if mutual:
            response += f"### Mutual Impact ({len(mutual)} relationships)\n"
            for impact in mutual[:3]:
                fact = self._clean_fact_text(impact.get('fact', ''))
                response += f"- {fact}\n"
            response += "\n"
        
        # Impact characterization
        if total > 0:
            response += "### Impact Profile:\n"
            if len(direct) > len(indirect):
                response += f"- **Primary role**: Influencer\n"
            elif len(indirect) > len(direct):
                response += f"- **Primary role**: Influenced\n"
            else:
                response += f"- **Primary role**: Balanced participant\n"
            
            centrality = "High" if total > 10 else "Medium" if total > 5 else "Low"
            response += f"- **Network centrality**: {centrality}\n"
        
        return response
    
    def format_search_results(self, query: str, results: List[Dict[str, Any]], 
                            total_found: int = None) -> str:
        """Format search results with source citations."""
        response = f"## Search Results: \"{query}\"\n\n"
        
        if total_found:
            response += f"**Found {total_found} relevant results**\n\n"
        
        if not results:
            response += "No results found for this query.\n"
            return response
        
        for i, result in enumerate(results, 1):
            fact = result.get('fact', result.get('content', ''))
            clean_fact = self._clean_fact_text(fact)
            
            response += f"### Result {i}\n"
            response += f"{clean_fact}\n"
            
            # Add source information if available
            source = result.get('source_url', '')
            if source:
                response += f"**Source**: {source}\n"
            
            episodes = result.get('episodes', [])
            if episodes:
                response += f"*From {len(episodes)} document(s)*\n"
            
            response += "\n"
        
        return response
    
    def _clean_fact_text(self, fact: str) -> str:
        """Clean and normalize fact text for display."""
        if not fact:
            return ""
        
        # Remove excessive whitespace
        fact = re.sub(r'\s+', ' ', fact.strip())
        
        # Ensure proper sentence ending
        if fact and not fact.endswith(('.', '!', '?', ':')):
            fact += "."
        
        return fact
    
    def add_section_divider(self, response: str) -> str:
        """Add a visual divider to separate response sections."""
        return response + "\n" + "─" * 50 + "\n\n"
    
    def add_next_steps(self, suggestions: List[str]) -> str:
        """Add suggested next steps to a response."""
        if not suggestions:
            return ""
        
        response = "### Suggested Next Steps:\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"
        
        return response + "\n"
    
    def format_error_message(self, operation: str, error: str, 
                           suggestions: Optional[List[str]] = None) -> str:
        """Format error messages with helpful suggestions."""
        response = f"## ⚠️ {operation} Error\n\n"
        response += f"**Issue**: {error}\n\n"
        
        if suggestions:
            response += "**Suggestions**:\n"
            for suggestion in suggestions:
                response += f"- {suggestion}\n"
        else:
            response += "**Suggestions**:\n"
            response += "- Try rephrasing your query\n"
            response += "- Use more specific entity names\n"
            response += "- Check entity spelling and capitalization\n"
        
        return response


# Global formatter instance
formatter = ResponseFormatter()