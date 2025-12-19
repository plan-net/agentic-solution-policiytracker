"""
MCP Context Retriever for Knowledge Graph Queries.

This module implements the four-stage context retrieval pipeline:
1. Query Analysis - Extract intent, entities, temporal scope
2. Tool Planning - Select and sequence retrieval tools
3. MCP Execution - Execute tools via Graphiti/Neo4j
4. Context Building - Structure results for response synthesis
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password123"
    database: str = "politicalmonitoring.v3"


# =============================================================================
# Enums and Types
# =============================================================================

class QueryIntent(str, Enum):
    """Classified query intent types."""
    INFORMATION_SEEKING = "information_seeking"
    RELATIONSHIP_ANALYSIS = "relationship_analysis"
    TEMPORAL_ANALYSIS = "temporal_analysis"
    IMPACT_ANALYSIS = "impact_analysis"
    STAKEHOLDER_MAPPING = "stakeholder_mapping"
    COMPARISON = "comparison"


class StrategyType(str, Enum):
    """Tool execution strategy types."""
    FOCUSED = "focused"
    COMPREHENSIVE = "comprehensive"


class TemporalFilterStrategy(str, Enum):
    """Temporal filtering strategies for Graphiti searches."""
    COMPREHENSIVE = "comprehensive"
    VALID_ONLY = "valid_only"
    CREATED_ONLY = "created_only"
    CHANGES = "changes"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class QueryAnalysis:
    """Result of query analysis."""
    original_query: str
    intent: QueryIntent
    entities: list[str]
    temporal_scope: Optional[dict] = None
    complexity: str = "simple"
    domain_hints: list[str] = field(default_factory=list)


@dataclass
class ToolPlan:
    """Execution plan for retrieval tools."""
    strategy: StrategyType
    tools: list[dict[str, Any]]
    estimated_time: float = 0.0


@dataclass
class RetrievedContext:
    """Structured retrieval results."""
    query_understanding: dict
    execution_summary: dict
    facts: list[dict]
    entities: list[dict]
    relationships: list[dict]
    sources: list[dict]
    metadata: dict


# =============================================================================
# Query Analyzer
# =============================================================================

class QueryAnalyzer:
    """Analyzes user queries to extract structured understanding."""
    
    INTENT_PATTERNS = {
        QueryIntent.INFORMATION_SEEKING: [
            r"what is", r"tell me about", r"explain", r"describe", 
            r"overview", r"summary", r"define"
        ],
        QueryIntent.RELATIONSHIP_ANALYSIS: [
            r"how.+related", r"connection", r"relationship", r"link between",
            r"associated", r"connected to"
        ],
        QueryIntent.TEMPORAL_ANALYSIS: [
            r"when", r"timeline", r"evolution", r"history", r"changes",
            r"recent", r"over time", r"since", r"before"
        ],
        QueryIntent.IMPACT_ANALYSIS: [
            r"affect", r"impact", r"consequence", r"result", r"effect",
            r"implications", r"influence"
        ],
        QueryIntent.STAKEHOLDER_MAPPING: [
            r"who", r"players", r"stakeholders", r"involved", r"champions",
            r"opposes", r"supports"
        ],
        QueryIntent.COMPARISON: [
            r"compare", r"difference", r"versus", r" vs ", r"contrast",
            r"similar to", r"different from"
        ]
    }
    
    TEMPORAL_PATTERNS = {
        r"recent|latest": {"days_back": 30},
        r"last week": {"days_back": 7},
        r"last month": {"days_back": 30},
        r"last quarter": {"days_back": 90},
        r"this year": {"year": "current"},
        r"past year|last year": {"days_back": 365},
    }
    
    KNOWN_ENTITIES = [
        "GDPR", "DSA", "DMA", "AI Act", "Digital Services Act", 
        "Digital Markets Act", "European Commission", "FTC",
        "European Parliament", "Bundestag", "CCPA"
    ]

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze a user query and extract structured components."""
        query_lower = query.lower()
        
        intent = self._classify_intent(query_lower)
        entities = self._extract_entities(query)
        temporal_scope = self._extract_temporal_scope(query_lower)
        complexity = self._assess_complexity(query, entities, intent)
        domain_hints = self._extract_domain_hints(query_lower)
        
        return QueryAnalysis(
            original_query=query,
            intent=intent,
            entities=entities,
            temporal_scope=temporal_scope,
            complexity=complexity,
            domain_hints=domain_hints
        )
    
    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify the primary intent of the query."""
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return intent
        return QueryIntent.INFORMATION_SEEKING
    
    def _extract_entities(self, query: str) -> list[str]:
        """Extract named entities from query."""
        entities = []
        query_upper = query.upper()
        
        # Check known entities
        for entity in self.KNOWN_ENTITIES:
            if entity.upper() in query_upper:
                entities.append(entity)
        
        # Extract capitalized phrases (potential entities)
        words = query.split()
        i = 0
        while i < len(words):
            if words[i][0].isupper() and words[i] not in ["What", "Who", "How", "When", "Where", "Why", "The", "A", "An"]:
                phrase = [words[i]]
                j = i + 1
                while j < len(words) and (words[j][0].isupper() or words[j] in ["of", "and", "the"]):
                    phrase.append(words[j])
                    j += 1
                entity = " ".join(phrase).strip("?.,!")
                if entity and entity not in entities:
                    entities.append(entity)
                i = j
            else:
                i += 1
        
        return entities
    
    def _extract_temporal_scope(self, query: str) -> Optional[dict]:
        """Extract temporal scope from query."""
        for pattern, scope in self.TEMPORAL_PATTERNS.items():
            if re.search(pattern, query):
                if "days_back" in scope:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=scope["days_back"])
                    return {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d"),
                        "type": "relative"
                    }
        
        # Check for quarter references
        quarter_match = re.search(r"q([1-4])\s*(\d{4})?", query)
        if quarter_match:
            q = int(quarter_match.group(1))
            year = int(quarter_match.group(2)) if quarter_match.group(2) else datetime.now().year
            start_month = (q - 1) * 3 + 1
            return {
                "start": f"{year}-{start_month:02d}-01",
                "end": f"{year}-{start_month + 2:02d}-30",
                "type": "quarter"
            }
        
        return None
    
    def _assess_complexity(self, query: str, entities: list, intent: QueryIntent) -> str:
        """Assess query complexity."""
        # Multi-entity or comparison queries are more complex
        if len(entities) > 1 or intent == QueryIntent.COMPARISON:
            return "medium"
        # Impact and stakeholder queries often need comprehensive search
        if intent in [QueryIntent.IMPACT_ANALYSIS, QueryIntent.STAKEHOLDER_MAPPING]:
            if len(query.split()) > 8:
                return "medium"
        return "simple"
    
    def _extract_domain_hints(self, query: str) -> list[str]:
        """Extract domain-specific hints from query."""
        hints = []
        domain_terms = {
            "regulation": ["regulation", "law", "legislation", "act", "directive"],
            "technology": ["ai", "tech", "digital", "data", "platform"],
            "politics": ["parliament", "bundestag", "commission", "minister"],
            "business": ["company", "business", "enterprise", "market"]
        }
        for domain, terms in domain_terms.items():
            if any(term in query for term in terms):
                hints.append(domain)
        return hints


# =============================================================================
# Tool Planner
# =============================================================================

class ToolPlanner:
    """Plans tool execution strategy based on query analysis."""
    
    TOOL_MAPPINGS = {
        QueryIntent.INFORMATION_SEEKING: {
            "focused": ["search", "get_entity_details"],
            "comprehensive": ["search", "get_entity_details", "get_entity_relationships", "find_similar_entities"]
        },
        QueryIntent.RELATIONSHIP_ANALYSIS: {
            "focused": ["find_paths_between_entities", "search"],
            "comprehensive": ["find_paths_between_entities", "get_entity_relationships", "search", "traverse_from_entity"]
        },
        QueryIntent.TEMPORAL_ANALYSIS: {
            "focused": ["search", "get_entity_details"],
            "comprehensive": ["search", "get_entity_details", "get_entity_relationships"]
        },
        QueryIntent.IMPACT_ANALYSIS: {
            "focused": ["analyze_entity_impact", "search"],
            "comprehensive": ["analyze_entity_impact", "traverse_from_entity", "get_entity_relationships", "search"]
        },
        QueryIntent.STAKEHOLDER_MAPPING: {
            "focused": ["search", "get_entity_relationships"],
            "comprehensive": ["search", "get_entity_relationships", "traverse_from_entity", "find_similar_entities"]
        },
        QueryIntent.COMPARISON: {
            "focused": ["search", "search"],
            "comprehensive": ["search", "search", "find_paths_between_entities", "find_similar_entities"]
        }
    }

    def create_plan(self, analysis: QueryAnalysis) -> ToolPlan:
        """Create execution plan based on analysis."""
        strategy = StrategyType.COMPREHENSIVE if analysis.complexity == "medium" else StrategyType.FOCUSED
        
        tool_names = self.TOOL_MAPPINGS.get(
            analysis.intent, 
            self.TOOL_MAPPINGS[QueryIntent.INFORMATION_SEEKING]
        )[strategy.value]
        
        tools = []
        for tool_name in tool_names:
            tool_config = self._configure_tool(tool_name, analysis)
            if tool_config:
                tools.append(tool_config)
        
        return ToolPlan(
            strategy=strategy,
            tools=tools,
            estimated_time=len(tools) * 1.5
        )
    
    def _configure_tool(self, tool_name: str, analysis: QueryAnalysis) -> Optional[dict]:
        """Configure a tool with appropriate parameters."""
        primary_entity = analysis.entities[0] if analysis.entities else analysis.original_query
        
        configs = {
            "search": {
                "tool_name": "search",
                "parameters": {"query": analysis.original_query, "limit": 10},
                "priority": "high",
                "purpose": "Search for relevant information"
            },
            "get_entity_details": {
                "tool_name": "get_entity_details",
                "parameters": {"entity_name": primary_entity},
                "priority": "high",
                "purpose": f"Get details about {primary_entity}"
            },
            "get_entity_relationships": {
                "tool_name": "get_entity_relationships",
                "parameters": {"entity_name": primary_entity, "max_relationships": 10},
                "priority": "medium",
                "purpose": f"Explore relationships of {primary_entity}"
            },
            "find_paths_between_entities": {
                "tool_name": "find_paths_between_entities",
                "parameters": {
                    "start_entity": analysis.entities[0] if analysis.entities else "",
                    "end_entity": analysis.entities[1] if len(analysis.entities) > 1 else ""
                },
                "priority": "high",
                "purpose": "Find connection paths between entities"
            },
            "analyze_entity_impact": {
                "tool_name": "analyze_entity_impact",
                "parameters": {"entity_name": primary_entity, "max_hops": 2},
                "priority": "high",
                "purpose": f"Analyze impact of {primary_entity}"
            },
            "traverse_from_entity": {
                "tool_name": "traverse_from_entity",
                "parameters": {"entity_name": primary_entity, "max_depth": 2},
                "priority": "low",
                "purpose": "Execute traverse_from_entity"
            },
            "find_similar_entities": {
                "tool_name": "find_similar_entities",
                "parameters": {"entity_name": primary_entity},
                "priority": "low",
                "purpose": f"Find entities similar to {primary_entity}"
            }
        }
        
        return configs.get(tool_name)


# =============================================================================
# MCP Executor
# =============================================================================

class MCPExecutor:
    """Executes tools via MCP/Graphiti connection."""
    
    def __init__(self, config: Neo4jConfig):
        self.config = config
        self.driver = None
        self.tools: dict = {}
    
    async def initialize(self):
        """Initialize Neo4j driver."""
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password)
            )
            logger.info(f"Connected to Neo4j at {self.config.uri}, database: {self.config.database}")
    
    async def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            await self.driver.close()
            self.driver = None
    
    async def execute_plan(self, plan: ToolPlan) -> list[dict]:
        """Execute all tools in the plan."""
        await self.initialize()
        
        results = []
        for tool_config in plan.tools:
            try:
                result = await self._execute_tool(tool_config)
                results.append({
                    "tool": tool_config["tool_name"],
                    "success": True,
                    "result": result
                })
            except Exception as e:
                logger.error(f"Tool {tool_config['tool_name']} failed: {e}")
                results.append({
                    "tool": tool_config["tool_name"],
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_tool(self, tool_config: dict) -> Any:
        """Execute a single tool."""
        tool_name = tool_config["tool_name"]
        params = tool_config["parameters"]
        
        if tool_name == "search":
            return await self._search(params)
        elif tool_name == "get_entity_details":
            return await self._get_entity_details(params)
        elif tool_name == "get_entity_relationships":
            return await self._get_entity_relationships(params)
        elif tool_name == "find_paths_between_entities":
            return await self._find_paths(params)
        elif tool_name == "analyze_entity_impact":
            return await self._analyze_impact(params)
        elif tool_name == "get_communities":
            return await self._get_communities(params)
        elif tool_name == "get_community_members":
            return await self._get_community_members(params)
        elif tool_name == "traverse_from_entity":
            return await self._traverse_from_entity(params)
        elif tool_name == "find_similar_entities":
            return await self._find_similar_entities(params)
        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return None
    
    async def _get_session(self):
        """Get a database session with correct database name."""
        return self.driver.session(database=self.config.database)
    
    async def _search(self, params: dict) -> dict:
        """Execute hybrid search using direct Cypher queries."""
        query_text = params["query"]
        limit = params.get("limit", 10)
        
        # Search entities
        entity_query = """
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS toLower($query)
           OR toLower(n.summary) CONTAINS toLower($query)
        RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary, labels(n) AS labels
        ORDER BY CASE WHEN toLower(n.name) CONTAINS toLower($query) THEN 0 ELSE 1 END
        LIMIT $limit
        """
        
        # Search relationships/facts
        edge_query = """
        MATCH (a:Entity)-[r]->(b:Entity)
        WHERE toLower(r.fact) CONTAINS toLower($query)
           OR toLower(a.name) CONTAINS toLower($query)
           OR toLower(b.name) CONTAINS toLower($query)
        RETURN r.uuid AS uuid, r.fact AS fact, type(r) AS relationship_type,
               a.uuid AS source_uuid, b.uuid AS target_uuid,
               a.name AS source_name, b.name AS target_name
        LIMIT $limit
        """
        
        nodes = []
        edges = []
        
        async with await self._get_session() as session:
            # Get entities
            result = await session.run(entity_query, {"query": query_text, "limit": limit})
            node_records = await result.data()
            for r in node_records:
                nodes.append({
                    "uuid": r["uuid"],
                    "name": r["name"],
                    "summary": r.get("summary", ""),
                    "labels": r.get("labels", [])
                })
            
            # Get relationships
            result = await session.run(edge_query, {"query": query_text, "limit": limit})
            edge_records = await result.data()
            for r in edge_records:
                edges.append({
                    "uuid": r["uuid"],
                    "fact": r["fact"],
                    "relationship_type": r["relationship_type"],
                    "source_uuid": r["source_uuid"],
                    "target_uuid": r["target_uuid"],
                    "source_name": r.get("source_name", ""),
                    "target_name": r.get("target_name", "")
                })
        
        return {"edges": edges, "nodes": nodes}
    
    async def _get_entity_details(self, params: dict) -> dict:
        """Get entity details by name."""
        entity_name = params["entity_name"]
        
        query = """
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS toLower($name)
        RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary, labels(n) AS labels
        LIMIT 1
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {"name": entity_name})
            records = await result.data()
            
            if records:
                return records[0]
            return {"error": f"Entity '{entity_name}' not found"}
    
    async def _get_entity_relationships(self, params: dict) -> dict:
        """Get relationships for an entity."""
        entity_name = params["entity_name"]
        limit = params.get("max_relationships", 10)
        
        query = """
        MATCH (n:Entity)-[r]->(m:Entity)
        WHERE toLower(n.name) CONTAINS toLower($name)
        RETURN n.name AS source, n.uuid AS source_uuid, type(r) AS relationship,
               m.name AS target, m.uuid AS target_uuid, r.fact AS fact
        LIMIT $limit
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {"name": entity_name, "limit": limit})
            records = await result.data()
            return {"relationships": records}
    
    async def _find_paths(self, params: dict) -> dict:
        """Find paths between two entities."""
        query = """
        MATCH path = shortestPath((a:Entity)-[*..3]-(b:Entity))
        WHERE toLower(a.name) CONTAINS toLower($start)
        AND toLower(b.name) CONTAINS toLower($end)
        RETURN [n IN nodes(path) | n.name] AS path_nodes,
               [r IN relationships(path) | type(r)] AS path_rels
        LIMIT 5
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {
                "start": params["start_entity"],
                "end": params["end_entity"]
            })
            records = await result.data()
            return {"paths": records}
    
    async def _analyze_impact(self, params: dict) -> dict:
        """Analyze entity impact network."""
        entity_name = params["entity_name"]
        
        query = """
        MATCH path = (n:Entity)-[*1..2]-(m:Entity)
        WHERE toLower(n.name) CONTAINS toLower($name)
        WITH m, length(path) AS distance
        RETURN m.name AS entity, labels(m) AS types, min(distance) AS hops_away
        ORDER BY hops_away
        LIMIT 20
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {"name": entity_name})
            records = await result.data()
            return {"impacted_entities": records}
    
    async def _get_communities(self, params: dict) -> dict:
        """Get communities related to entity."""
        entity_name = params["entity_name"]
        
        query = """
        MATCH (n:Entity)-[:MEMBER_OF]->(c:Community)
        WHERE toLower(n.name) CONTAINS toLower($name)
        RETURN c.uuid AS community_id, c.name AS community_name,
               COUNT { (c)<-[:MEMBER_OF]-() } AS member_count
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {"name": entity_name})
            records = await result.data()
            return {"communities": records}
    
    async def _get_community_members(self, params: dict) -> dict:
        """Get members of a community."""
        entity_name = params.get("entity_name", "")
        
        query = """
        MATCH (n:Entity)-[:MEMBER_OF]->(c:Community)<-[:MEMBER_OF]-(m:Entity)
        WHERE toLower(n.name) CONTAINS toLower($name)
        RETURN DISTINCT m.name AS member_name, labels(m) AS member_types, m.uuid AS uuid
        LIMIT 20
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {"name": entity_name})
            records = await result.data()
            return {"members": records}
    
    async def _traverse_from_entity(self, params: dict) -> dict:
        """Traverse relationships from an entity."""
        entity_name = params["entity_name"]
        
        query = """
        MATCH path = (n:Entity)-[*1..2]-(m:Entity)
        WHERE toLower(n.name) CONTAINS toLower($name)
        WITH m, relationships(path) AS rels
        UNWIND rels AS r
        RETURN DISTINCT m.name AS entity, labels(m) AS types,
               type(r) AS relationship, r.fact AS fact
        LIMIT 20
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {"name": entity_name})
            records = await result.data()
            return {"traversed_entities": records}
    
    async def _find_similar_entities(self, params: dict) -> dict:
        """Find entities similar to the given one."""
        entity_name = params["entity_name"]
        
        query = """
        MATCH (n:Entity)-[r]-(shared)-[r2]-(similar:Entity)
        WHERE toLower(n.name) CONTAINS toLower($name)
        AND n <> similar
        WITH similar, count(*) AS shared_connections, labels(similar) AS types
        ORDER BY shared_connections DESC
        RETURN DISTINCT similar.name AS name, types, shared_connections
        LIMIT 10
        """
        
        async with await self._get_session() as session:
            result = await session.run(query, {"name": entity_name})
            records = await result.data()
            return {"similar_entities": records}


# =============================================================================
# Context Builder
# =============================================================================

class ContextBuilder:
    """Builds structured context from tool results."""
    
    def build(self, analysis: QueryAnalysis, plan: ToolPlan, results: list[dict]) -> RetrievedContext:
        """Build structured context from results."""
        facts = []
        entities = []
        relationships = []
        sources = []
        
        success_count = sum(1 for r in results if r["success"])
        
        for result in results:
            if not result["success"] or not result["result"]:
                continue
            
            data = result["result"]
            
            # Extract edges as facts
            if "edges" in data:
                for edge in data["edges"]:
                    if edge.get("fact"):
                        facts.append({
                            "content": edge["fact"],
                            "type": edge.get("relationship_type", ""),
                            "confidence": 0.8,
                            "source_uuid": edge.get("source_uuid"),
                            "target_uuid": edge.get("target_uuid")
                        })
                    if edge.get("source_name") and edge.get("target_name"):
                        relationships.append({
                            "source": edge["source_name"],
                            "target": edge["target_name"],
                            "type": edge.get("relationship_type", "RELATED"),
                            "fact": edge.get("fact", "")
                        })
            
            # Extract nodes as entities
            if "nodes" in data:
                for node in data["nodes"]:
                    entities.append({
                        "name": node.get("name", "Unknown"),
                        "type": ", ".join(node.get("labels", [])),
                        "summary": node.get("summary", ""),
                        "uuid": node.get("uuid")
                    })
            
            # Extract relationships
            if "relationships" in data:
                for rel in data["relationships"]:
                    relationships.append({
                        "source": rel.get("source", ""),
                        "target": rel.get("target", ""),
                        "type": rel.get("relationship", ""),
                        "fact": rel.get("fact", "")
                    })
            
            # Extract paths
            if "paths" in data:
                for path in data["paths"]:
                    path_str = " → ".join(path.get("path_nodes", []))
                    facts.append({
                        "content": f"Path: {path_str}",
                        "type": "path",
                        "confidence": 0.9
                    })
            
            # Extract impact analysis
            if "impacted_entities" in data:
                for entity in data["impacted_entities"]:
                    entities.append({
                        "name": entity.get("entity", ""),
                        "type": ", ".join(entity.get("types", [])),
                        "summary": f"Impact distance: {entity.get('hops_away', 'N/A')} hops"
                    })
            
            # Extract traversed entities
            if "traversed_entities" in data:
                for item in data["traversed_entities"]:
                    entities.append({
                        "name": item.get("entity", ""),
                        "type": ", ".join(item.get("types", [])),
                        "summary": item.get("fact", "")
                    })
                    if item.get("fact"):
                        facts.append({
                            "content": item["fact"],
                            "type": item.get("relationship", ""),
                            "confidence": 0.7
                        })
            
            # Extract similar entities
            if "similar_entities" in data:
                for item in data["similar_entities"]:
                    entities.append({
                        "name": item.get("name", ""),
                        "type": ", ".join(item.get("types", [])),
                        "summary": f"Shared connections: {item.get('shared_connections', 0)}"
                    })
            
            # Extract community members
            if "members" in data:
                for member in data["members"]:
                    entities.append({
                        "name": member.get("member_name", ""),
                        "type": ", ".join(member.get("member_types", [])),
                        "summary": "Community member"
                    })
            
            # Extract communities
            if "communities" in data:
                for community in data["communities"]:
                    entities.append({
                        "name": community.get("community_name", ""),
                        "type": "Community",
                        "summary": f"Members: {community.get('member_count', 0)}"
                    })
            
            # Handle single entity result
            if "uuid" in data and "name" in data and "nodes" not in data:
                entities.append({
                    "name": data.get("name", "Unknown"),
                    "type": ", ".join(data.get("labels", [])),
                    "summary": data.get("summary", ""),
                    "uuid": data.get("uuid")
                })
        
        # Deduplicate entities
        seen_entities = set()
        unique_entities = []
        for e in entities:
            if e["name"] and e["name"] not in seen_entities:
                seen_entities.add(e["name"])
                unique_entities.append(e)
        
        # Deduplicate facts
        seen_facts = set()
        unique_facts = []
        for f in facts:
            content_key = f["content"][:100] if f["content"] else ""
            if content_key and content_key not in seen_facts:
                seen_facts.add(content_key)
                unique_facts.append(f)
        
        return RetrievedContext(
            query_understanding={
                "original_query": analysis.original_query,
                "intent": analysis.intent.value,
                "entities_identified": analysis.entities,
                "temporal_scope": analysis.temporal_scope,
                "complexity": analysis.complexity
            },
            execution_summary={
                "strategy": plan.strategy.value,
                "tools_planned": len(plan.tools),
                "tools_succeeded": success_count,
                "success_rate": success_count / max(len(results), 1)
            },
            facts=unique_facts,
            entities=unique_entities,
            relationships=relationships,
            sources=sources,
            metadata={
                "total_facts": len(unique_facts),
                "total_entities": len(unique_entities),
                "total_relationships": len(relationships),
                "confidence_assessment": self._assess_confidence(unique_facts, unique_entities)
            }
        )
    
    def _assess_confidence(self, facts: list, entities: list) -> str:
        """Assess overall confidence in retrieved context."""
        if len(facts) > 10 and len(entities) > 5:
            return "high"
        elif len(facts) > 3 or len(entities) > 2:
            return "medium"
        return "low"


# =============================================================================
# Main Pipeline
# =============================================================================

class GraphContextRetriever:
    """Main context retrieval pipeline."""
    
    def __init__(self, config: Optional[Neo4jConfig] = None):
        self.config = config or Neo4jConfig()
        self.analyzer = QueryAnalyzer()
        self.planner = ToolPlanner()
        self.executor = MCPExecutor(self.config)
        self.builder = ContextBuilder()
    
    async def retrieve(self, query: str) -> RetrievedContext:
        """Execute full retrieval pipeline."""
        logger.info(f"Starting retrieval for: {query}")
        
        # Step 1: Analyze query
        analysis = self.analyzer.analyze(query)
        logger.info(f"Query analysis: intent={analysis.intent.value}, entities={analysis.entities}")
        
        # Step 2: Create tool plan
        plan = self.planner.create_plan(analysis)
        logger.info(f"Execution plan: strategy={plan.strategy.value}, tools={len(plan.tools)}")
        
        # Step 3: Execute tools
        results = await self.executor.execute_plan(plan)
        logger.info(f"Execution complete: {sum(1 for r in results if r['success'])}/{len(results)} succeeded")
        
        # Step 4: Build context
        context = self.builder.build(analysis, plan, results)
        logger.info(f"Context built: {context.metadata['total_facts']} facts, {context.metadata['total_entities']} entities")
        
        return context
    
    async def close(self):
        """Close connections."""
        await self.executor.close()
    
    def to_dict(self, context: RetrievedContext) -> dict:
        """Convert context to dictionary for JSON serialization."""
        return {
            "query_understanding": context.query_understanding,
            "execution_summary": context.execution_summary,
            "retrieved_context": {
                "facts": context.facts,
                "entities": context.entities,
                "relationships": context.relationships
            },
            "sources": context.sources,
            "metadata": context.metadata
        }
