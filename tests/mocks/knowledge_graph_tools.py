"""Mock implementations of knowledge graph tools for testing multi-agent system."""

import asyncio
import random
from datetime import datetime
from typing import Any, Optional


class MockKnowledgeGraphTools:
    """Mock implementation of all knowledge graph tools for testing."""

    def __init__(self):
        self.call_history: list[dict[str, Any]] = []
        self.mock_data = self._create_mock_data()
        self.execution_delays = {
            "search": 0.1,
            "entity_lookup": 0.05,
            "relationship_analysis": 0.08,
            "traverse_from_entity": 0.12,
            "find_paths_between_entities": 0.15,
            "get_entity_neighbors": 0.06,
            "temporal_query": 0.10,
            "search_by_date_range": 0.13,
            "get_entity_history": 0.11,
            "find_concurrent_events": 0.14,
            "get_communities": 0.20,
            "get_community_members": 0.08,
            "get_policy_clusters": 0.16,
            "analyze_entity_impact": 0.18,
        }

    def _create_mock_data(self) -> dict[str, Any]:
        """Create realistic mock data for political/regulatory domain."""
        return {
            "entities": {
                "EU AI Act": {
                    "type": "Policy",
                    "status": "enacted",
                    "jurisdiction": "EU",
                    "effective_date": "2024-08-01",
                    "description": "Comprehensive AI regulation framework",
                },
                "European Commission": {
                    "type": "Organization",
                    "jurisdiction": "EU",
                    "role": "regulatory_authority",
                    "description": "Executive branch of the European Union",
                },
                "Meta": {
                    "type": "Company",
                    "industry": "technology",
                    "headquarters": "US",
                    "description": "Social media and technology company",
                },
                "GDPR": {
                    "type": "Policy",
                    "status": "active",
                    "jurisdiction": "EU",
                    "effective_date": "2018-05-25",
                    "description": "General Data Protection Regulation",
                },
                "Digital Services Act": {
                    "type": "Policy",
                    "status": "active",
                    "jurisdiction": "EU",
                    "effective_date": "2024-02-17",
                    "description": "Regulation on digital services and platforms",
                },
                "Thierry Breton": {
                    "type": "Person",
                    "role": "Commissioner",
                    "organization": "European Commission",
                    "description": "EU Commissioner for Internal Market",
                },
            },
            "relationships": [
                {
                    "source": "European Commission",
                    "target": "EU AI Act",
                    "type": "AUTHORED",
                    "context": "Proposed and developed the regulation",
                },
                {
                    "source": "EU AI Act",
                    "target": "Meta",
                    "type": "AFFECTS",
                    "context": "Regulates AI systems used by the company",
                },
                {
                    "source": "GDPR",
                    "target": "Meta",
                    "type": "REGULATES",
                    "context": "Data protection compliance requirements",
                },
                {
                    "source": "Thierry Breton",
                    "target": "Digital Services Act",
                    "type": "ENFORCES",
                    "context": "Oversees implementation and enforcement",
                },
            ],
            "facts": [
                {
                    "content": "The EU AI Act introduces risk-based classification for AI systems",
                    "entities": ["EU AI Act"],
                    "source": "Official EU legislation",
                    "date": "2024-07-12",
                },
                {
                    "content": "Meta faces potential fines under the Digital Services Act for content moderation failures",
                    "entities": ["Meta", "Digital Services Act"],
                    "source": "EU enforcement action",
                    "date": "2024-05-15",
                },
                {
                    "content": "GDPR has resulted in over €4.5 billion in fines since implementation",
                    "entities": ["GDPR"],
                    "source": "DPA enforcement statistics",
                    "date": "2024-06-01",
                },
            ],
            "communities": [
                {
                    "id": "eu_ai_regulation",
                    "name": "EU AI Regulation Ecosystem",
                    "members": ["EU AI Act", "European Commission", "Thierry Breton"],
                    "description": "Entities involved in EU AI regulation",
                },
                {
                    "id": "big_tech_compliance",
                    "name": "Big Tech EU Compliance",
                    "members": ["Meta", "GDPR", "Digital Services Act"],
                    "description": "Major tech companies and EU regulations",
                },
            ],
        }

    def _log_call(self, tool_name: str, parameters: dict[str, Any]) -> None:
        """Log tool call for testing verification."""
        self.call_history.append(
            {"tool": tool_name, "parameters": parameters, "timestamp": datetime.now().isoformat()}
        )

    async def _simulate_delay(self, tool_name: str) -> None:
        """Simulate realistic execution delays."""
        delay = self.execution_delays.get(tool_name, 0.1)
        await asyncio.sleep(delay)

    # Core Search Tools

    async def search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Mock semantic search for facts and relationships."""
        self._log_call("search", {"query": query, "limit": limit})
        await self._simulate_delay("search")

        # Simple keyword matching for mock results
        query_lower = query.lower()
        matching_facts = []

        for fact in self.mock_data["facts"]:
            if any(term in fact["content"].lower() for term in query_lower.split()):
                matching_facts.append(fact)

        matching_entities = []
        for entity_name, entity_data in self.mock_data["entities"].items():
            if any(
                term in entity_name.lower() or term in entity_data["description"].lower()
                for term in query_lower.split()
            ):
                matching_entities.append(
                    {
                        "name": entity_name,
                        "type": entity_data["type"],
                        "description": entity_data["description"],
                        "relevance_score": random.uniform(0.7, 1.0),
                    }
                )

        return {
            "facts": matching_facts[:limit],
            "entities": matching_entities[:limit],
            "total_results": len(matching_facts) + len(matching_entities),
            "execution_time": self.execution_delays["search"],
        }

    async def entity_lookup(self, entity_name: str) -> dict[str, Any]:
        """Mock detailed entity information lookup."""
        self._log_call("entity_lookup", {"entity_name": entity_name})
        await self._simulate_delay("entity_lookup")

        if entity_name in self.mock_data["entities"]:
            entity_data = self.mock_data["entities"][entity_name].copy()

            # Add related entities
            related_entities = []
            for rel in self.mock_data["relationships"]:
                if rel["source"] == entity_name:
                    related_entities.append(
                        {
                            "entity": rel["target"],
                            "relationship": rel["type"],
                            "context": rel["context"],
                        }
                    )
                elif rel["target"] == entity_name:
                    related_entities.append(
                        {
                            "entity": rel["source"],
                            "relationship": f"INVERSE_{rel['type']}",
                            "context": rel["context"],
                        }
                    )

            entity_data["related_entities"] = related_entities
            entity_data["fact_count"] = len(
                [f for f in self.mock_data["facts"] if entity_name in f["entities"]]
            )

            return {
                "entity": entity_data,
                "success": True,
                "execution_time": self.execution_delays["entity_lookup"],
            }
        else:
            return {
                "entity": None,
                "success": False,
                "error": f"Entity '{entity_name}' not found",
                "execution_time": self.execution_delays["entity_lookup"],
            }

    async def relationship_analysis(self, entity1: str, entity2: str) -> dict[str, Any]:
        """Mock relationship analysis between two entities."""
        self._log_call("relationship_analysis", {"entity1": entity1, "entity2": entity2})
        await self._simulate_delay("relationship_analysis")

        # Find direct relationships
        direct_relationships = []
        for rel in self.mock_data["relationships"]:
            if (rel["source"] == entity1 and rel["target"] == entity2) or (
                rel["source"] == entity2 and rel["target"] == entity1
            ):
                direct_relationships.append(rel)

        # Find shared connections (entities connected to both)
        entity1_connections = set()
        entity2_connections = set()

        for rel in self.mock_data["relationships"]:
            if rel["source"] == entity1:
                entity1_connections.add(rel["target"])
            elif rel["target"] == entity1:
                entity1_connections.add(rel["source"])

            if rel["source"] == entity2:
                entity2_connections.add(rel["target"])
            elif rel["target"] == entity2:
                entity2_connections.add(rel["source"])

        shared_connections = list(entity1_connections.intersection(entity2_connections))

        return {
            "direct_relationships": direct_relationships,
            "shared_connections": shared_connections,
            "relationship_strength": len(direct_relationships) + len(shared_connections) * 0.5,
            "path_exists": len(direct_relationships) > 0 or len(shared_connections) > 0,
            "execution_time": self.execution_delays["relationship_analysis"],
        }

    # Advanced Analysis Tools

    async def traverse_from_entity(
        self, entity_name: str, direction: str = "both", max_hops: int = 2
    ) -> dict[str, Any]:
        """Mock multi-hop relationship traversal."""
        self._log_call(
            "traverse_from_entity",
            {"entity_name": entity_name, "direction": direction, "max_hops": max_hops},
        )
        await self._simulate_delay("traverse_from_entity")

        visited = set()
        paths = []

        def traverse(current_entity: str, path: list[str], hops_remaining: int):
            if hops_remaining <= 0 or current_entity in visited:
                return

            visited.add(current_entity)

            for rel in self.mock_data["relationships"]:
                next_entity = None
                if direction in ["both", "outgoing"] and rel["source"] == current_entity:
                    next_entity = rel["target"]
                elif direction in ["both", "incoming"] and rel["target"] == current_entity:
                    next_entity = rel["source"]

                if next_entity and next_entity not in visited:
                    new_path = path + [next_entity]
                    paths.append(
                        {"path": new_path, "relationship": rel["type"], "hops": len(new_path) - 1}
                    )

                    if hops_remaining > 1:
                        traverse(next_entity, new_path, hops_remaining - 1)

        traverse(entity_name, [entity_name], max_hops)

        return {
            "starting_entity": entity_name,
            "paths_found": paths,
            "entities_discovered": list(visited),
            "max_hops": max_hops,
            "execution_time": self.execution_delays["traverse_from_entity"],
        }

    async def find_paths_between_entities(
        self, entity1: str, entity2: str, max_path_length: int = 3
    ) -> dict[str, Any]:
        """Mock path discovery between entities."""
        self._log_call(
            "find_paths_between_entities",
            {"entity1": entity1, "entity2": entity2, "max_path_length": max_path_length},
        )
        await self._simulate_delay("find_paths_between_entities")

        # Simple BFS to find paths
        from collections import deque

        queue = deque([(entity1, [entity1])])
        visited = set()
        paths_found = []

        while queue and len(paths_found) < 5:  # Limit to 5 paths for performance
            current_entity, path = queue.popleft()

            if len(path) > max_path_length:
                continue

            if current_entity == entity2 and len(path) > 1:
                paths_found.append(
                    {
                        "path": path,
                        "length": len(path) - 1,
                        "relationships": self._get_path_relationships(path),
                    }
                )
                continue

            if current_entity in visited:
                continue
            visited.add(current_entity)

            # Find neighbors
            for rel in self.mock_data["relationships"]:
                next_entity = None
                if rel["source"] == current_entity:
                    next_entity = rel["target"]
                elif rel["target"] == current_entity:
                    next_entity = rel["source"]

                if next_entity and next_entity not in path:
                    queue.append((next_entity, path + [next_entity]))

        return {
            "entity1": entity1,
            "entity2": entity2,
            "paths_found": paths_found,
            "shortest_path_length": min([p["length"] for p in paths_found])
            if paths_found
            else None,
            "connection_exists": len(paths_found) > 0,
            "execution_time": self.execution_delays["find_paths_between_entities"],
        }

    def _get_path_relationships(self, path: list[str]) -> list[dict[str, str]]:
        """Get relationships along a path."""
        relationships = []
        for i in range(len(path) - 1):
            source, target = path[i], path[i + 1]
            for rel in self.mock_data["relationships"]:
                if (rel["source"] == source and rel["target"] == target) or (
                    rel["source"] == target and rel["target"] == source
                ):
                    relationships.append(
                        {
                            "from": source,
                            "to": target,
                            "type": rel["type"],
                            "context": rel["context"],
                        }
                    )
                    break
        return relationships

    async def get_entity_neighbors(
        self, entity_name: str, relationship_types: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Mock immediate entity connections."""
        self._log_call(
            "get_entity_neighbors",
            {"entity_name": entity_name, "relationship_types": relationship_types},
        )
        await self._simulate_delay("get_entity_neighbors")

        neighbors = []
        for rel in self.mock_data["relationships"]:
            if relationship_types and rel["type"] not in relationship_types:
                continue

            if rel["source"] == entity_name:
                neighbors.append(
                    {
                        "entity": rel["target"],
                        "relationship": rel["type"],
                        "direction": "outgoing",
                        "context": rel["context"],
                    }
                )
            elif rel["target"] == entity_name:
                neighbors.append(
                    {
                        "entity": rel["source"],
                        "relationship": rel["type"],
                        "direction": "incoming",
                        "context": rel["context"],
                    }
                )

        return {
            "entity": entity_name,
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
            "relationship_types_found": list(set(n["relationship"] for n in neighbors)),
            "execution_time": self.execution_delays["get_entity_neighbors"],
        }

    # Temporal Tools

    async def temporal_query(self, entity: str, time_range: tuple) -> dict[str, Any]:
        """Mock temporal entity analysis."""
        self._log_call("temporal_query", {"entity": entity, "time_range": time_range})
        await self._simulate_delay("temporal_query")

        start_date, end_date = time_range

        # Find facts within time range
        relevant_facts = []
        for fact in self.mock_data["facts"]:
            if entity in fact["entities"]:
                fact_date = datetime.fromisoformat(fact["date"])
                if start_date <= fact_date <= end_date:
                    relevant_facts.append(fact)

        # Simulate temporal changes
        changes = (
            [
                {
                    "date": "2024-03-15",
                    "change_type": "status_update",
                    "description": f"{entity} regulatory status updated",
                    "impact": "medium",
                },
                {
                    "date": "2024-06-20",
                    "change_type": "enforcement_action",
                    "description": f"New enforcement action affecting {entity}",
                    "impact": "high",
                },
            ]
            if entity in ["Meta", "GDPR"]
            else []
        )

        return {
            "entity": entity,
            "time_range": time_range,
            "facts_in_period": relevant_facts,
            "temporal_changes": changes,
            "activity_level": "high" if len(relevant_facts) > 1 else "medium",
            "execution_time": self.execution_delays["temporal_query"],
        }

    async def search_by_date_range(
        self, start_date: str, end_date: str, entity_filter: Optional[str] = None
    ) -> dict[str, Any]:
        """Mock time-scoped search."""
        self._log_call(
            "search_by_date_range",
            {"start_date": start_date, "end_date": end_date, "entity_filter": entity_filter},
        )
        await self._simulate_delay("search_by_date_range")

        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        filtered_facts = []
        for fact in self.mock_data["facts"]:
            fact_date = datetime.fromisoformat(fact["date"])
            if start_dt <= fact_date <= end_dt:
                if not entity_filter or entity_filter in fact["entities"]:
                    filtered_facts.append(fact)

        return {
            "date_range": {"start": start_date, "end": end_date},
            "entity_filter": entity_filter,
            "facts_found": filtered_facts,
            "total_events": len(filtered_facts),
            "execution_time": self.execution_delays["search_by_date_range"],
        }

    # Community and Pattern Tools

    async def get_communities(self, entity_type: Optional[str] = None) -> dict[str, Any]:
        """Mock community detection."""
        self._log_call("get_communities", {"entity_type": entity_type})
        await self._simulate_delay("get_communities")

        communities = self.mock_data["communities"].copy()

        if entity_type:
            # Filter communities by entity type
            filtered_communities = []
            for community in communities:
                relevant_members = []
                for member in community["members"]:
                    if (
                        member in self.mock_data["entities"]
                        and self.mock_data["entities"][member]["type"] == entity_type
                    ):
                        relevant_members.append(member)

                if relevant_members:
                    community_copy = community.copy()
                    community_copy["members"] = relevant_members
                    filtered_communities.append(community_copy)

            communities = filtered_communities

        return {
            "communities": communities,
            "total_communities": len(communities),
            "entity_type_filter": entity_type,
            "execution_time": self.execution_delays["get_communities"],
        }

    async def get_community_members(self, community_id: str) -> dict[str, Any]:
        """Mock community member exploration."""
        self._log_call("get_community_members", {"community_id": community_id})
        await self._simulate_delay("get_community_members")

        community = None
        for comm in self.mock_data["communities"]:
            if comm["id"] == community_id:
                community = comm
                break

        if not community:
            return {
                "community_id": community_id,
                "found": False,
                "error": f"Community '{community_id}' not found",
                "execution_time": self.execution_delays["get_community_members"],
            }

        # Get detailed member information
        member_details = []
        for member_name in community["members"]:
            if member_name in self.mock_data["entities"]:
                member_info = self.mock_data["entities"][member_name].copy()
                member_info["name"] = member_name
                member_details.append(member_info)

        return {
            "community": community,
            "members": member_details,
            "member_count": len(member_details),
            "execution_time": self.execution_delays["get_community_members"],
        }

    # Test Utilities

    def reset_call_history(self) -> None:
        """Reset call history for testing."""
        self.call_history.clear()

    def get_call_count(self, tool_name: Optional[str] = None) -> int:
        """Get number of calls made."""
        if tool_name:
            return len([call for call in self.call_history if call["tool"] == tool_name])
        return len(self.call_history)

    def get_last_call(self) -> Optional[dict[str, Any]]:
        """Get the last tool call made."""
        return self.call_history[-1] if self.call_history else None

    def set_execution_delay(self, tool_name: str, delay: float) -> None:
        """Set custom execution delay for testing."""
        self.execution_delays[tool_name] = delay

    def add_mock_entity(self, name: str, entity_data: dict[str, Any]) -> None:
        """Add a mock entity for testing."""
        self.mock_data["entities"][name] = entity_data

    def add_mock_relationship(
        self, source: str, target: str, rel_type: str, context: str = ""
    ) -> None:
        """Add a mock relationship for testing."""
        self.mock_data["relationships"].append(
            {"source": source, "target": target, "type": rel_type, "context": context}
        )

    def add_mock_fact(
        self, content: str, entities: list[str], source: str = "test", date: str = None
    ) -> None:
        """Add a mock fact for testing."""
        if not date:
            date = datetime.now().isoformat()

        self.mock_data["facts"].append(
            {"content": content, "entities": entities, "source": source, "date": date}
        )


# Global instance for testing
mock_kg_tools = MockKnowledgeGraphTools()
