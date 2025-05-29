"""Query parsing utilities for understanding user intent and extracting entities."""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the agent can handle."""
    ENTITY_DETAILS = "entity_details"
    RELATIONSHIP_EXPLORATION = "relationship_exploration"
    TIMELINE_ANALYSIS = "timeline_analysis"
    IMPACT_ANALYSIS = "impact_analysis"
    PATH_FINDING = "path_finding"
    SIMILARITY_SEARCH = "similarity_search"
    COMMUNITY_ANALYSIS = "community_analysis"
    TEMPORAL_SEARCH = "temporal_search"
    GENERAL_SEARCH = "general_search"
    TRAVERSAL = "traversal"
    NEIGHBOR_ANALYSIS = "neighbor_analysis"


@dataclass
class ParsedQuery:
    """Structured representation of a parsed query."""
    query_type: QueryType
    primary_entity: Optional[str] = None
    secondary_entity: Optional[str] = None
    entities: List[str] = None
    time_range: Optional[Tuple[str, str]] = None
    relationship_types: List[str] = None
    filters: Dict[str, Any] = None
    intent_confidence: float = 0.0
    raw_query: str = ""
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.relationship_types is None:
            self.relationship_types = []
        if self.filters is None:
            self.filters = {}


class QueryParser:
    """Parser for understanding user queries and extracting structured information."""
    
    def __init__(self):
        """Initialize the query parser with patterns and keywords."""
        self._entity_patterns = [
            r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\b',  # Capitalized phrases
            r'\b[A-Z]{2,}\b',  # Acronyms
            r'"([^"]*)"',  # Quoted strings
            r"'([^']*)'",  # Single quoted strings
        ]
        
        self._relationship_keywords = {
            'affects': ['affects', 'impacts', 'influences', 'changes'],
            'governs': ['governs', 'regulates', 'controls', 'oversees'],
            'requires': ['requires', 'mandates', 'demands', 'needs'],
            'supports': ['supports', 'backs', 'endorses', 'promotes'],
            'opposes': ['opposes', 'against', 'rejects', 'blocks'],
            'implements': ['implements', 'executes', 'carries out', 'applies'],
            'supersedes': ['supersedes', 'replaces', 'overrides', 'updates']
        }
        
        self._temporal_keywords = [
            'when', 'timeline', 'history', 'evolution', 'over time',
            'recently', 'latest', 'current', 'past', 'future',
            'before', 'after', 'during', 'since', 'until',
            'last week', 'last month', 'last year', 'this year'
        ]
        
        self._intent_patterns = {
            QueryType.ENTITY_DETAILS: [
                r'what is (?:the )?(.+?)(?:\?|$)',
                r'tell me about (.+?)(?:\?|$)',
                r'describe (.+?)(?:\?|$)',
                r'information about (.+?)(?:\?|$)',
                r'details (?:on|about) (.+?)(?:\?|$)'
            ],
            QueryType.RELATIONSHIP_EXPLORATION: [
                r'(?:what|how) (?:does|is) (.+?) (?:related to|connected to|linked to) (.+?)(?:\?|$)',
                r'relationship between (.+?) and (.+?)(?:\?|$)',
                r'how (?:are|is) (.+?) (?:and|related to) (.+?)(?:\?|$)',
                r'connections? (?:between|of) (.+?)(?:\?|$)'
            ],
            QueryType.TIMELINE_ANALYSIS: [
                r'(?:timeline|history|evolution) (?:of|for) (.+?)(?:\?|$)',
                r'how (?:has|did) (.+?) (?:change|evolve|develop)(?:\?|$)',
                r'when (?:did|was) (.+?)(?:\?|$)',
                r'(?:track|trace) (.+?) over time(?:\?|$)'
            ],
            QueryType.IMPACT_ANALYSIS: [
                r'(?:what|how) (?:does|is) (.+?) (?:affect|impact|influence) (.+?)(?:\?|$)',
                r'impact (?:of|from) (.+?)(?:\?|$)',
                r'(?:who|what) (?:is|are) affected by (.+?)(?:\?|$)',
                r'consequences (?:of|from) (.+?)(?:\?|$)'
            ],
            QueryType.PATH_FINDING: [
                r'(?:path|connection|link) (?:from|between) (.+?) (?:to|and) (.+?)(?:\?|$)',
                r'how (?:is|are) (.+?) connected to (.+?)(?:\?|$)',
                r'route from (.+?) to (.+?)(?:\?|$)'
            ],
            QueryType.SIMILARITY_SEARCH: [
                r'(?:similar|like|comparable) (?:to|as) (.+?)(?:\?|$)',
                r'(?:what|who) (?:else )?(?:is|are) like (.+?)(?:\?|$)',
                r'entities similar to (.+?)(?:\?|$)'
            ],
            QueryType.COMMUNITY_ANALYSIS: [
                r'(?:cluster|group|community|network) (?:of|containing|with) (.+?)(?:\?|$)',
                r'policy (?:areas|domains|clusters)(?:\?|$)',
                r'(?:who|what) (?:works together|collaborates)(?:\?|$)'
            ],
            QueryType.TEMPORAL_SEARCH: [
                r'(?:recent|latest|current) (.+?)(?:\?|$)',
                r'(?:what happened|events) (?:in|during|over) (.+?)(?:\?|$)',
                r'(.+?) (?:this|last) (?:week|month|year)(?:\?|$)'
            ]
        }
    
    def parse(self, query: str) -> ParsedQuery:
        """Parse a user query into structured components."""
        logger.info(f"Parsing query: {query}")
        
        # Clean the query
        clean_query = self._clean_query(query)
        
        # Detect query type and extract entities
        query_type, confidence = self._detect_intent(clean_query)
        entities = self._extract_entities(clean_query)
        primary_entity, secondary_entity = self._identify_primary_entities(entities, clean_query)
        
        # Extract specific components
        relationship_types = self._extract_relationship_types(clean_query)
        time_range = self._extract_time_range(clean_query)
        filters = self._extract_filters(clean_query)
        
        parsed = ParsedQuery(
            query_type=query_type,
            primary_entity=primary_entity,
            secondary_entity=secondary_entity,
            entities=entities,
            time_range=time_range,
            relationship_types=relationship_types,
            filters=filters,
            intent_confidence=confidence,
            raw_query=query
        )
        
        logger.info(f"Parsed as {query_type.value} with confidence {confidence:.2f}")
        return parsed
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query text."""
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Convert to lowercase for pattern matching (keep original for entity extraction)
        return query
    
    def _detect_intent(self, query: str) -> Tuple[QueryType, float]:
        """Detect the intent of the query."""
        query_lower = query.lower()
        best_match = (QueryType.GENERAL_SEARCH, 0.0)
        
        # Check each intent pattern
        for intent_type, patterns in self._intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_pattern_confidence(pattern, match, query_lower)
                    if confidence > best_match[1]:
                        best_match = (intent_type, confidence)
        
        # Additional heuristics for better classification
        best_match = self._apply_heuristics(query_lower, best_match)
        
        return best_match
    
    def _calculate_pattern_confidence(self, pattern: str, match: re.Match, query: str) -> float:
        """Calculate confidence score for a pattern match."""
        # Base confidence
        confidence = 0.6
        
        # Bonus for specific keywords
        if any(keyword in query for keyword in ['timeline', 'history', 'evolution']):
            confidence += 0.2
        if any(keyword in query for keyword in ['impact', 'affect', 'influence']):
            confidence += 0.2
        if any(keyword in query for keyword in ['relationship', 'connection', 'related']):
            confidence += 0.2
        if any(keyword in query for keyword in ['similar', 'like', 'comparable']):
            confidence += 0.2
        
        # Bonus for captured groups (entities)
        if match.groups():
            confidence += 0.1 * len(match.groups())
        
        return min(confidence, 1.0)
    
    def _apply_heuristics(self, query: str, current_best: Tuple[QueryType, float]) -> Tuple[QueryType, float]:
        """Apply additional heuristics to improve intent detection."""
        
        # Temporal analysis heuristics
        if any(keyword in query for keyword in self._temporal_keywords):
            if 'timeline' in query or 'history' in query or 'evolution' in query:
                return (QueryType.TIMELINE_ANALYSIS, max(current_best[1], 0.8))
            else:
                return (QueryType.TEMPORAL_SEARCH, max(current_best[1], 0.7))
        
        # Relationship heuristics
        if ' and ' in query and ('between' in query or 'relationship' in query):
            return (QueryType.RELATIONSHIP_EXPLORATION, max(current_best[1], 0.8))
        
        # Path finding heuristics
        if ('path' in query or 'connection' in query) and ' to ' in query:
            return (QueryType.PATH_FINDING, max(current_best[1], 0.8))
        
        # Impact analysis heuristics
        if any(word in query for word in ['impact', 'affect', 'influence', 'consequence']):
            return (QueryType.IMPACT_ANALYSIS, max(current_best[1], 0.7))
        
        # Community analysis heuristics
        if any(word in query for word in ['cluster', 'group', 'community', 'network']):
            return (QueryType.COMMUNITY_ANALYSIS, max(current_best[1], 0.7))
        
        return current_best
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential entity names from the query."""
        entities = []
        
        # Extract using each pattern
        for pattern in self._entity_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)
        
        # Clean and filter entities
        cleaned_entities = []
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'what', 'when', 'where', 'who', 'why', 'how', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can'
        }
        
        for entity in entities:
            entity = entity.strip()
            if (len(entity) > 1 and 
                entity.lower() not in stop_words and
                not entity.isdigit()):
                cleaned_entities.append(entity)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in cleaned_entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)
        
        return unique_entities[:10]  # Limit to top 10 entities
    
    def _identify_primary_entities(self, entities: List[str], query: str) -> Tuple[Optional[str], Optional[str]]:
        """Identify the primary and secondary entities from the list."""
        if not entities:
            return None, None
        
        # Score entities by position in query and capitalization
        scored_entities = []
        query_lower = query.lower()
        
        for entity in entities:
            score = 0
            
            # Position bonus (earlier = higher score)
            position = query_lower.find(entity.lower())
            if position != -1:
                score += (len(query) - position) / len(query) * 10
            
            # Capitalization bonus
            if entity[0].isupper():
                score += 5
            
            # Length bonus (longer names often more specific)
            score += len(entity.split()) * 2
            
            # Acronym bonus
            if entity.isupper() and len(entity) >= 2:
                score += 3
            
            scored_entities.append((entity, score))
        
        # Sort by score
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        
        primary = scored_entities[0][0] if scored_entities else None
        secondary = scored_entities[1][0] if len(scored_entities) > 1 else None
        
        return primary, secondary
    
    def _extract_relationship_types(self, query: str) -> List[str]:
        """Extract relationship types mentioned in the query."""
        query_lower = query.lower()
        found_types = []
        
        for rel_type, keywords in self._relationship_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                found_types.append(rel_type.upper())
        
        return found_types
    
    def _extract_time_range(self, query: str) -> Optional[Tuple[str, str]]:
        """Extract time range information from the query."""
        query_lower = query.lower()
        
        # Simple time range patterns
        time_patterns = {
            r'last (\d+) days?': lambda m: (f"-{m.group(1)}d", "now"),
            r'last (\d+) weeks?': lambda m: (f"-{int(m.group(1))*7}d", "now"),
            r'last (\d+) months?': lambda m: (f"-{int(m.group(1))*30}d", "now"),
            r'this year': lambda m: ("2024-01-01", "now"),
            r'last year': lambda m: ("2023-01-01", "2023-12-31"),
            r'recent': lambda m: ("-30d", "now"),
            r'recently': lambda m: ("-30d", "now"),
        }
        
        for pattern, converter in time_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                try:
                    return converter(match)
                except Exception as e:
                    logger.warning(f"Error parsing time range: {e}")
                    continue
        
        return None
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract filters and constraints from the query."""
        filters = {}
        query_lower = query.lower()
        
        # Entity type filters
        entity_types = ['policy', 'company', 'politician', 'organization', 'regulation']
        for entity_type in entity_types:
            if entity_type in query_lower:
                filters['entity_type'] = entity_type
        
        # Jurisdiction filters
        jurisdictions = ['eu', 'us', 'uk', 'global', 'international']
        for jurisdiction in jurisdictions:
            if jurisdiction in query_lower:
                filters['jurisdiction'] = jurisdiction
        
        # Limit filters
        limit_match = re.search(r'(?:top|first|limit) (\d+)', query_lower)
        if limit_match:
            filters['limit'] = int(limit_match.group(1))
        
        return filters
    
    def suggest_tools(self, parsed_query: ParsedQuery) -> List[str]:
        """Suggest which tools to use based on the parsed query."""
        tools = []
        
        if parsed_query.query_type == QueryType.ENTITY_DETAILS:
            tools.append("get_entity_details")
            if parsed_query.primary_entity:
                tools.append("get_entity_relationships")
        
        elif parsed_query.query_type == QueryType.RELATIONSHIP_EXPLORATION:
            tools.append("get_entity_relationships")
            if parsed_query.primary_entity and parsed_query.secondary_entity:
                tools.append("find_paths_between_entities")
        
        elif parsed_query.query_type == QueryType.TIMELINE_ANALYSIS:
            tools.append("get_entity_timeline")
            tools.append("search_by_date_range")
        
        elif parsed_query.query_type == QueryType.IMPACT_ANALYSIS:
            tools.append("analyze_entity_impact")
            tools.append("traverse_from_entity")
        
        elif parsed_query.query_type == QueryType.PATH_FINDING:
            tools.append("find_paths_between_entities")
            tools.append("get_entity_neighbors")
        
        elif parsed_query.query_type == QueryType.SIMILARITY_SEARCH:
            tools.append("find_similar_entities")
            tools.append("detect_communities")
        
        elif parsed_query.query_type == QueryType.COMMUNITY_ANALYSIS:
            tools.append("detect_communities")
            tools.append("analyze_policy_clusters")
        
        elif parsed_query.query_type == QueryType.TEMPORAL_SEARCH:
            tools.append("search_by_date_range")
            tools.append("find_concurrent_events")
        
        elif parsed_query.query_type == QueryType.TRAVERSAL:
            tools.append("traverse_from_entity")
            tools.append("get_entity_neighbors")
        
        else:  # GENERAL_SEARCH
            tools.append("search_knowledge_graph")
        
        return tools


# Global parser instance
parser = QueryParser()