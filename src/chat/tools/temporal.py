"""Temporal analysis tools for exploring time-based patterns in the knowledge graph."""

import logging
from typing import List, Dict, Any, Optional, Type
from datetime import datetime, timedelta
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field
from graphiti_core import Graphiti
from graphiti_core.search.search_config_recipes import (
    EDGE_HYBRID_SEARCH_EPISODE_MENTIONS,
    COMBINED_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_RRF
)

logger = logging.getLogger(__name__)


class DateRangeSearchInput(BaseModel):
    """Input schema for date range search tool."""
    query: str = Field(description="Search query within the specified date range")
    start_date: datetime = Field(description="Start date for the search range")
    end_date: datetime = Field(description="End date for the search range")
    max_results: int = Field(default=10, description="Maximum number of results to return")


class EntityHistoryInput(BaseModel):
    """Input schema for entity history tool."""
    entity_name: str = Field(description="Name of the entity to get history for")
    days_back: int = Field(default=365, description="Number of days back to search for entity history")
    event_types: Optional[List[str]] = Field(default=None, description="Types of events to focus on (e.g., 'regulatory', 'enforcement')")


class ConcurrentEventsInput(BaseModel):
    """Input schema for concurrent events tool."""
    reference_date: datetime = Field(description="Reference date to find concurrent events around")
    window_days: int = Field(default=30, description="Number of days before and after reference date to search")
    event_context: Optional[str] = Field(default=None, description="Context or theme to focus concurrent events on")


class TimelineComparisonInput(BaseModel):
    """Input schema for timeline comparison tool."""
    entities: List[str] = Field(description="List of entities to compare timelines for")
    time_period: int = Field(default=365, description="Time period in days to compare")
    comparison_focus: Optional[str] = Field(default=None, description="Specific aspect to focus comparison on")


class PolicyEvolutionInput(BaseModel):
    """Input schema for policy evolution tool."""
    policy_name: str = Field(description="Name of the policy to track evolution for")
    evolution_period: int = Field(default=730, description="Period in days to track evolution (default: 2 years)")
    evolution_aspects: Optional[List[str]] = Field(default=None, description="Specific aspects to track (e.g., 'amendments', 'enforcement', 'compliance')")


class DateRangeSearchTool(BaseTool):
    """Tool for searching within specific date ranges to track temporal patterns."""
    
    name: str = "search_by_date_range"
    description: str = "Search for events, policies, or changes within a specific date range. Useful for tracking what happened during specific periods."
    args_schema: Type[BaseModel] = DateRangeSearchInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, query: str, start_date: datetime, end_date: datetime, max_results: int = 10, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, query: str, start_date: datetime, end_date: datetime, max_results: int = 10, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Search within date range using episode mentions."""
        try:
            logger.info(f"Searching date range {start_date.date()} to {end_date.date()} for: {query}")
            
            # Build temporal search query
            date_keywords = ["announced", "published", "enacted", "implemented", "released", "updated", "changed"]
            temporal_query = f"{query} " + " ".join(date_keywords)
            
            # Use episode mentions search config for better temporal relevance
            search_results = await self.client._search(
                query=temporal_query,
                config=EDGE_HYBRID_SEARCH_EPISODE_MENTIONS
            )
            
            # Extract and filter results
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, 'nodes') and search_results.nodes:
                results.extend(search_results.nodes)
            
            if not results:
                return f"No events found in date range {start_date.date()} to {end_date.date()} for query: {query}"
            
            # Process temporal results
            temporal_events = []
            for result in results[:max_results * 2]:  # Get more to filter by temporal relevance
                content = ""
                if hasattr(result, 'fact') and result.fact:
                    content = result.fact
                elif hasattr(result, 'summary') and result.summary:
                    content = result.summary
                
                if content:
                    # Extract temporal relevance
                    temporal_score = self._calculate_temporal_relevance(content, start_date, end_date)
                    if temporal_score > 0:
                        temporal_events.append({
                            'content': content,
                            'temporal_score': temporal_score,
                            'episodes': getattr(result, 'episodes', []),
                            'type': 'fact' if hasattr(result, 'fact') else 'entity'
                        })
            
            # Sort by temporal relevance
            temporal_events.sort(key=lambda x: x['temporal_score'], reverse=True)
            
            # Format response
            response = f"## Temporal Search: {start_date.date()} to {end_date.date()}\n\n"
            response += f"**Query**: {query}\n"
            response += f"**Period**: {(end_date - start_date).days} days\n\n"
            
            if temporal_events:
                response += f"**Found {len(temporal_events)} temporally relevant events:**\n\n"
                for i, event in enumerate(temporal_events[:max_results], 1):
                    response += f"{i}. **[{event['type'].title()}]** {event['content'][:150]}...\n"
                    if event['temporal_score'] > 0.7:
                        response += f"   *High temporal relevance ({event['temporal_score']:.2f})*\n"
                    response += "\n"
                
                if len(temporal_events) > max_results:
                    response += f"... and {len(temporal_events) - max_results} more events in this period.\n"
            else:
                response += f"No temporally relevant events found for '{query}' in the specified date range.\n\n"
                response += "**Suggestions:**\n"
                response += "- Try expanding the date range\n"
                response += "- Use broader search terms\n"
                response += "- Check if the events occurred outside this period\n"
            
            logger.info(f"Found {len(temporal_events)} temporal events")
            return response
            
        except Exception as e:
            logger.error(f"Error in date range search: {e}")
            return f"Error searching date range: {str(e)}"
    
    def _calculate_temporal_relevance(self, content: str, start_date: datetime, end_date: datetime) -> float:
        """Calculate how temporally relevant content is to the date range."""
        content_lower = content.lower()
        
        # Look for temporal indicators
        temporal_indicators = [
            "announced", "published", "enacted", "implemented", "released", 
            "updated", "changed", "effective", "deadline", "commenced"
        ]
        
        relevance_score = 0.0
        
        # Base score for temporal keywords
        for indicator in temporal_indicators:
            if indicator in content_lower:
                relevance_score += 0.2
        
        # Look for date patterns
        import re
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, content_lower):
                relevance_score += 0.3
                break
        
        # Look for year mentions within range
        start_year = start_date.year
        end_year = end_date.year
        
        for year in range(start_year, end_year + 1):
            if str(year) in content:
                relevance_score += 0.3
                break
        
        return min(relevance_score, 1.0)


class EntityHistoryTool(BaseTool):
    """Tool for tracking how an entity has evolved over time."""
    
    name: str = "get_entity_history"
    description: str = "Track the historical evolution of an entity over time. Shows timeline of changes, events, and mentions."
    args_schema: Type[BaseModel] = EntityHistoryInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, entity_name: str, days_back: int = 365, event_types: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, entity_name: str, days_back: int = 365, event_types: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get historical timeline for an entity."""
        try:
            logger.info(f"Getting {days_back}-day history for entity: {entity_name}")
            
            # Build history search query
            history_keywords = ["history", "timeline", "evolution", "changes", "updates", "development"]
            if event_types:
                history_keywords.extend(event_types)
            
            search_query = f"{entity_name} " + " ".join(history_keywords)
            
            # Use episode mentions for better temporal tracking
            search_results = await self.client._search(
                query=search_query,
                config=EDGE_HYBRID_SEARCH_EPISODE_MENTIONS
            )
            
            # Extract results
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, 'nodes') and search_results.nodes:
                results.extend(search_results.nodes)
            
            if not results:
                return f"No historical information found for entity '{entity_name}'"
            
            # Process historical events
            historical_events = []
            for result in results:
                content = ""
                if hasattr(result, 'fact') and result.fact:
                    content = result.fact
                elif hasattr(result, 'summary') and result.summary:
                    content = result.summary
                
                if content and entity_name.lower() in content.lower():
                    # Extract event characteristics
                    event_info = self._extract_event_info(content, entity_name)
                    if event_info:
                        historical_events.append({
                            'content': content,
                            'event_type': event_info['type'],
                            'importance': event_info['importance'],
                            'temporal_indicators': event_info['temporal_indicators'],
                            'episodes': getattr(result, 'episodes', [])
                        })
            
            # Sort by importance and temporal indicators
            historical_events.sort(key=lambda x: (x['importance'], len(x['temporal_indicators'])), reverse=True)
            
            # Format historical timeline
            response = f"## Historical Timeline: {entity_name}\n\n"
            response += f"**Period**: Last {days_back} days\n"
            if event_types:
                response += f"**Focus**: {', '.join(event_types)}\n"
            response += f"**Events Found**: {len(historical_events)}\n\n"
            
            if historical_events:
                # Group by event type
                event_groups = {}
                for event in historical_events:
                    event_type = event['event_type']
                    if event_type not in event_groups:
                        event_groups[event_type] = []
                    event_groups[event_type].append(event)
                
                for event_type, events in event_groups.items():
                    response += f"### {event_type.title()} Events:\n"
                    for i, event in enumerate(events[:5], 1):  # Top 5 per category
                        response += f"{i}. {event['content'][:120]}...\n"
                        if event['temporal_indicators']:
                            response += f"   *Temporal markers: {', '.join(event['temporal_indicators'][:3])}*\n"
                    response += "\n"
                
                # Timeline summary
                response += "### Timeline Analysis:\n"
                total_events = len(historical_events)
                high_importance = len([e for e in historical_events if e['importance'] > 0.7])
                response += f"- **Total historical events**: {total_events}\n"
                response += f"- **High-importance events**: {high_importance}\n"
                response += f"- **Event types found**: {len(event_groups)}\n"
                
            else:
                response += f"No clear historical timeline found for {entity_name}.\n\n"
                response += "**Suggestions:**\n"
                response += "- Try using alternative entity names or acronyms\n"
                response += "- Expand the time period\n"
                response += "- Use more general search terms\n"
            
            logger.info(f"Found {len(historical_events)} historical events for {entity_name}")
            return response
            
        except Exception as e:
            logger.error(f"Error getting entity history: {e}")
            return f"Error retrieving history for {entity_name}: {str(e)}"
    
    def _extract_event_info(self, content: str, entity_name: str) -> Optional[Dict[str, Any]]:
        """Extract event type and importance from content."""
        content_lower = content.lower()
        
        # Event type classification
        event_types = {
            'regulatory': ['regulation', 'rule', 'compliance', 'enforcement', 'fine', 'penalty'],
            'policy': ['policy', 'law', 'act', 'directive', 'legislation', 'amendment'],
            'business': ['merger', 'acquisition', 'partnership', 'investment', 'funding'],
            'product': ['launch', 'release', 'announcement', 'update', 'version'],
            'legal': ['lawsuit', 'court', 'ruling', 'judgment', 'settlement', 'litigation'],
            'general': ['news', 'report', 'statement', 'comment', 'response']
        }
        
        detected_type = 'general'
        for event_type, keywords in event_types.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_type = event_type
                break
        
        # Importance scoring
        importance_indicators = {
            'high': ['major', 'significant', 'important', 'critical', 'breakthrough', 'landmark'],
            'medium': ['notable', 'substantial', 'considerable', 'meaningful'],
            'temporal': ['announced', 'released', 'published', 'enacted', 'implemented']
        }
        
        importance_score = 0.3  # Base score
        for level, indicators in importance_indicators.items():
            for indicator in indicators:
                if indicator in content_lower:
                    if level == 'high':
                        importance_score += 0.3
                    elif level == 'medium':
                        importance_score += 0.2
                    elif level == 'temporal':
                        importance_score += 0.1
        
        # Extract temporal indicators
        temporal_indicators = []
        temporal_keywords = ['announced', 'released', 'published', 'enacted', 'implemented', 
                           'updated', 'changed', 'effective', 'deadline', 'commenced']
        
        for keyword in temporal_keywords:
            if keyword in content_lower:
                temporal_indicators.append(keyword)
        
        return {
            'type': detected_type,
            'importance': min(importance_score, 1.0),
            'temporal_indicators': temporal_indicators
        }


class ConcurrentEventsTool(BaseTool):
    """Tool for finding events that happened around the same time."""
    
    name: str = "find_concurrent_events"
    description: str = "Find events that happened around the same time as a reference date. Useful for understanding context and related developments."
    args_schema: Type[BaseModel] = ConcurrentEventsInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, reference_date: datetime, window_days: int = 30, event_context: Optional[str] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, reference_date: datetime, window_days: int = 30, event_context: Optional[str] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Find concurrent events around a reference date."""
        try:
            logger.info(f"Finding concurrent events around {reference_date.date()} (±{window_days} days)")
            
            # Calculate date window
            start_date = reference_date - timedelta(days=window_days)
            end_date = reference_date + timedelta(days=window_days)
            
            # Build search query
            concurrent_keywords = ["announced", "released", "published", "enacted", "occurred", "happened"]
            if event_context:
                search_query = f"{event_context} " + " ".join(concurrent_keywords)
            else:
                search_query = " ".join(concurrent_keywords) + " events news policy regulation"
            
            # Search for concurrent events
            search_results = await self.client._search(
                query=search_query,
                config=EDGE_HYBRID_SEARCH_EPISODE_MENTIONS
            )
            
            # Extract results
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, 'nodes') and search_results.nodes:
                results.extend(search_results.nodes)
            
            if not results:
                return f"No concurrent events found around {reference_date.date()}"
            
            # Process and categorize concurrent events
            concurrent_events = []
            for result in results:
                content = ""
                if hasattr(result, 'fact') and result.fact:
                    content = result.fact
                elif hasattr(result, 'summary') and result.summary:
                    content = result.summary
                
                if content:
                    # Check temporal relevance to the reference period
                    temporal_relevance = self._check_temporal_proximity(content, reference_date, window_days)
                    if temporal_relevance > 0.3:
                        event_category = self._categorize_concurrent_event(content)
                        concurrent_events.append({
                            'content': content,
                            'category': event_category,
                            'temporal_relevance': temporal_relevance,
                            'episodes': getattr(result, 'episodes', [])
                        })
            
            # Sort by temporal relevance
            concurrent_events.sort(key=lambda x: x['temporal_relevance'], reverse=True)
            
            # Format concurrent events analysis
            response = f"## Concurrent Events Analysis\n\n"
            response += f"**Reference Date**: {reference_date.date()}\n"
            response += f"**Time Window**: ±{window_days} days ({start_date.date()} to {end_date.date()})\n"
            if event_context:
                response += f"**Context Filter**: {event_context}\n"
            response += f"**Events Found**: {len(concurrent_events)}\n\n"
            
            if concurrent_events:
                # Group by category
                categories = {}
                for event in concurrent_events:
                    category = event['category']
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(event)
                
                response += "### Concurrent Events by Category:\n\n"
                for category, events in categories.items():
                    response += f"#### {category.title()} ({len(events)} events):\n"
                    for i, event in enumerate(events[:3], 1):  # Top 3 per category
                        response += f"{i}. {event['content'][:100]}...\n"
                        response += f"   *Temporal relevance: {event['temporal_relevance']:.2f}*\n"
                    response += "\n"
                
                # Timeline context
                response += "### Timeline Context:\n"
                high_relevance = len([e for e in concurrent_events if e['temporal_relevance'] > 0.7])
                response += f"- **High temporal relevance**: {high_relevance} events\n"
                response += f"- **Event categories**: {len(categories)}\n"
                response += f"- **Peak activity period**: {window_days * 2} days around {reference_date.date()}\n"
                
            else:
                response += f"No significant concurrent events found around {reference_date.date()}.\n\n"
                response += "**Suggestions:**\n"
                response += "- Expand the time window\n"
                response += "- Try different event context keywords\n"
                response += "- Check for events in adjacent time periods\n"
            
            logger.info(f"Found {len(concurrent_events)} concurrent events")
            return response
            
        except Exception as e:
            logger.error(f"Error finding concurrent events: {e}")
            return f"Error finding concurrent events: {str(e)}"
    
    def _check_temporal_proximity(self, content: str, reference_date: datetime, window_days: int) -> float:
        """Check how temporally close content is to the reference date."""
        content_lower = content.lower()
        
        # Look for temporal indicators
        temporal_score = 0.0
        
        # Check for year mention
        if str(reference_date.year) in content:
            temporal_score += 0.4
        
        # Check for month mentions around reference date
        ref_month = reference_date.strftime("%B").lower()
        prev_month = (reference_date - timedelta(days=30)).strftime("%B").lower()
        next_month = (reference_date + timedelta(days=30)).strftime("%B").lower()
        
        if any(month in content_lower for month in [ref_month, prev_month, next_month]):
            temporal_score += 0.3
        
        # Look for temporal action words
        temporal_actions = ["announced", "released", "published", "enacted", "implemented"]
        if any(action in content_lower for action in temporal_actions):
            temporal_score += 0.3
        
        return min(temporal_score, 1.0)
    
    def _categorize_concurrent_event(self, content: str) -> str:
        """Categorize the type of concurrent event."""
        content_lower = content.lower()
        
        categories = {
            'regulatory': ['regulation', 'rule', 'compliance', 'enforcement', 'directive'],
            'policy': ['policy', 'law', 'act', 'legislation', 'government'],
            'business': ['company', 'business', 'corporate', 'merger', 'acquisition'],
            'technology': ['technology', 'tech', 'digital', 'ai', 'software'],
            'legal': ['court', 'lawsuit', 'ruling', 'legal', 'judgment'],
            'international': ['international', 'global', 'treaty', 'agreement'],
            'general': []  # Default category
        }
        
        for category, keywords in categories.items():
            if any(keyword in content_lower for keyword in keywords):
                return category
        
        return 'general'


class PolicyEvolutionTool(BaseTool):
    """Tool for tracking how policies and regulations evolve over time."""
    
    name: str = "track_policy_evolution"
    description: str = "Track how a specific policy or regulation has evolved over time. Shows amendments, changes, and implementation phases."
    args_schema: Type[BaseModel] = PolicyEvolutionInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, policy_name: str, evolution_period: int = 730, evolution_aspects: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, policy_name: str, evolution_period: int = 730, evolution_aspects: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Track policy evolution over time."""
        try:
            logger.info(f"Tracking evolution of policy: {policy_name} over {evolution_period} days")
            
            # Build evolution search query
            evolution_keywords = ["evolution", "amendment", "update", "revision", "change", "modification", "implementation"]
            if evolution_aspects:
                evolution_keywords.extend(evolution_aspects)
            
            search_query = f"{policy_name} " + " ".join(evolution_keywords)
            
            # Use comprehensive search for policy evolution
            search_results = await self.client._search(
                query=search_query,
                config=COMBINED_HYBRID_SEARCH_RRF
            )
            
            # Extract results
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, 'nodes') and search_results.nodes:
                results.extend(search_results.nodes)
            
            if not results:
                return f"No evolution information found for policy '{policy_name}'"
            
            # Process evolution timeline
            evolution_events = []
            for result in results:
                content = ""
                if hasattr(result, 'fact') and result.fact:
                    content = result.fact
                elif hasattr(result, 'summary') and result.summary:
                    content = result.summary
                
                if content and policy_name.lower() in content.lower():
                    evolution_info = self._analyze_policy_evolution(content, policy_name)
                    if evolution_info:
                        evolution_events.append({
                            'content': content,
                            'phase': evolution_info['phase'],
                            'impact_level': evolution_info['impact_level'],
                            'evolution_type': evolution_info['evolution_type'],
                            'stakeholders': evolution_info['stakeholders'],
                            'episodes': getattr(result, 'episodes', [])
                        })
            
            # Sort by impact level and phase
            evolution_events.sort(key=lambda x: (x['impact_level'], x['phase'] == 'implementation'), reverse=True)
            
            # Format policy evolution analysis
            response = f"## Policy Evolution Analysis: {policy_name}\n\n"
            response += f"**Evolution Period**: {evolution_period} days (~{evolution_period//365} years)\n"
            if evolution_aspects:
                response += f"**Focus Areas**: {', '.join(evolution_aspects)}\n"
            response += f"**Evolution Events**: {len(evolution_events)}\n\n"
            
            if evolution_events:
                # Group by evolution phase
                phases = {}
                for event in evolution_events:
                    phase = event['phase']
                    if phase not in phases:
                        phases[phase] = []
                    phases[phase].append(event)
                
                # Order phases logically
                phase_order = ['proposal', 'amendment', 'implementation', 'enforcement', 'review']
                ordered_phases = {phase: phases.get(phase, []) for phase in phase_order if phase in phases}
                
                response += "### Evolution Timeline by Phase:\n\n"
                for phase, events in ordered_phases.items():
                    response += f"#### {phase.title()} Phase ({len(events)} events):\n"
                    for i, event in enumerate(events[:4], 1):  # Top 4 per phase
                        response += f"{i}. **{event['evolution_type'].title()}**: {event['content'][:120]}...\n"
                        if event['stakeholders']:
                            response += f"   *Stakeholders: {', '.join(event['stakeholders'][:3])}*\n"
                        response += f"   *Impact level: {event['impact_level']:.2f}*\n"
                    response += "\n"
                
                # Evolution summary
                response += "### Evolution Summary:\n"
                high_impact = len([e for e in evolution_events if e['impact_level'] > 0.7])
                evolution_types = set(e['evolution_type'] for e in evolution_events)
                all_stakeholders = set()
                for event in evolution_events:
                    all_stakeholders.update(event['stakeholders'])
                
                response += f"- **High-impact changes**: {high_impact}\n"
                response += f"- **Evolution phases**: {len(ordered_phases)}\n"
                response += f"- **Change types**: {', '.join(evolution_types)}\n"
                response += f"- **Key stakeholders**: {', '.join(list(all_stakeholders)[:5])}\n"
                
            else:
                response += f"No clear evolution timeline found for {policy_name}.\n\n"
                response += "**Suggestions:**\n"
                response += "- Try alternative policy names or abbreviations\n"
                response += "- Expand the evolution period\n"
                response += "- Focus on specific evolution aspects\n"
            
            logger.info(f"Tracked {len(evolution_events)} evolution events for {policy_name}")
            return response
            
        except Exception as e:
            logger.error(f"Error tracking policy evolution: {e}")
            return f"Error tracking evolution for {policy_name}: {str(e)}"
    
    def _analyze_policy_evolution(self, content: str, policy_name: str) -> Optional[Dict[str, Any]]:
        """Analyze content for policy evolution indicators."""
        content_lower = content.lower()
        
        # Evolution phases
        phase_indicators = {
            'proposal': ['proposed', 'draft', 'proposal', 'suggest', 'recommend'],
            'amendment': ['amended', 'revised', 'updated', 'modified', 'changed'],
            'implementation': ['implemented', 'enacted', 'effective', 'came into force'],
            'enforcement': ['enforced', 'penalty', 'fine', 'violation', 'compliance'],
            'review': ['reviewed', 'evaluated', 'assessed', 'reconsidered']
        }
        
        detected_phase = 'general'
        for phase, indicators in phase_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                detected_phase = phase
                break
        
        # Evolution types
        evolution_types = {
            'amendment': ['amendment', 'revised', 'updated', 'modified'],
            'expansion': ['expanded', 'extended', 'broadened', 'increased'],
            'restriction': ['restricted', 'limited', 'reduced', 'narrowed'],
            'clarification': ['clarified', 'explained', 'defined', 'specified'],
            'enforcement': ['enforcement', 'penalty', 'fine', 'sanction']
        }
        
        detected_type = 'general'
        for evo_type, keywords in evolution_types.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_type = evo_type
                break
        
        # Impact level scoring
        impact_indicators = {
            'high': ['major', 'significant', 'substantial', 'critical', 'fundamental'],
            'medium': ['important', 'notable', 'considerable', 'meaningful'],
            'procedural': ['administrative', 'procedural', 'technical', 'minor']
        }
        
        impact_level = 0.3  # Base impact
        for level, indicators in impact_indicators.items():
            for indicator in indicators:
                if indicator in content_lower:
                    if level == 'high':
                        impact_level += 0.4
                    elif level == 'medium':
                        impact_level += 0.2
                    elif level == 'procedural':
                        impact_level += 0.1
        
        # Extract stakeholders
        stakeholder_patterns = [
            'commission', 'parliament', 'council', 'agency', 'authority',
            'company', 'companies', 'organization', 'industry', 'sector'
        ]
        
        stakeholders = []
        for pattern in stakeholder_patterns:
            if pattern in content_lower:
                stakeholders.append(pattern)
        
        return {
            'phase': detected_phase,
            'evolution_type': detected_type,
            'impact_level': min(impact_level, 1.0),
            'stakeholders': stakeholders
        }