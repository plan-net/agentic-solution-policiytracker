"""Community detection tools for identifying clusters and networks in the knowledge graph."""

import logging
from typing import Any, Optional

from graphiti_core import Graphiti
from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_RRF,
    COMMUNITY_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_RRF,
)
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GetCommunitiesInput(BaseModel):
    """Input schema for getting communities tool."""

    topic_focus: Optional[str] = Field(
        default=None, description="Topic to focus communities on (e.g., 'AI regulation', 'privacy')"
    )
    max_communities: int = Field(default=5, description="Maximum number of communities to return")
    min_community_size: int = Field(
        default=3, description="Minimum number of entities per community"
    )


class CommunityMembersInput(BaseModel):
    """Input schema for getting community members tool."""

    community_topic: str = Field(description="Topic or theme that defines the community")
    max_members: int = Field(
        default=10, description="Maximum number of community members to return"
    )
    member_types: Optional[list[str]] = Field(
        default=None, description="Types of entities to focus on (e.g., ['Policy', 'Company'])"
    )


class RelatedCommunitiesInput(BaseModel):
    """Input schema for finding related communities tool."""

    entity_name: str = Field(description="Entity to find related communities for")
    max_communities: int = Field(
        default=5, description="Maximum number of related communities to return"
    )
    relationship_types: Optional[list[str]] = Field(
        default=None, description="Types of relationships to consider for community detection"
    )


class PolicyClustersInput(BaseModel):
    """Input schema for policy clusters tool."""

    policy_area: Optional[str] = Field(
        default=None, description="Policy area to focus on (e.g., 'digital', 'environmental')"
    )
    cluster_method: str = Field(
        default="thematic",
        description="Clustering method: 'thematic', 'jurisdictional', or 'temporal'",
    )
    max_clusters: int = Field(default=5, description="Maximum number of policy clusters to return")


class OrganizationNetworkInput(BaseModel):
    """Input schema for organization network tool."""

    organization_type: Optional[str] = Field(
        default=None, description="Type of organizations to focus on (e.g., 'regulatory', 'tech')"
    )
    network_depth: int = Field(default=2, description="Depth of network connections to explore")
    min_connections: int = Field(
        default=2, description="Minimum connections to include organization in network"
    )


class GetCommunitiesTool(BaseTool):
    """Tool for discovering communities and clusters in the knowledge graph."""

    name: str = "get_communities"
    description: str = "Discover communities and clusters of related entities. Shows groups of policies, organizations, or topics that are closely connected."
    args_schema: type[BaseModel] = GetCommunitiesInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        topic_focus: Optional[str] = None,
        max_communities: int = 5,
        min_community_size: int = 3,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        topic_focus: Optional[str] = None,
        max_communities: int = 5,
        min_community_size: int = 3,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Discover communities in the knowledge graph."""
        try:
            logger.info(f"Discovering communities (focus: {topic_focus}, max: {max_communities})")

            # Build community search query
            if topic_focus:
                search_query = (
                    f"{topic_focus} communities groups clusters networks related connected"
                )
            else:
                search_query = (
                    "communities groups clusters networks related connected policy organization"
                )

            # Use community-focused search configuration
            search_results = await self.client._search(
                query=search_query, config=COMMUNITY_HYBRID_SEARCH_RRF
            )

            # Extract results
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, "nodes") and search_results.nodes:
                results.extend(search_results.nodes)

            if not results:
                return f"No communities found for topic: {topic_focus or 'general'}"

            # Detect communities through co-occurrence analysis
            communities = self._detect_communities(results, topic_focus, min_community_size)

            # Limit to max communities
            communities = communities[:max_communities]

            # Format community analysis
            response = "## Community Detection Analysis\n\n"
            if topic_focus:
                response += f"**Topic Focus**: {topic_focus}\n"
            response += f"**Communities Found**: {len(communities)}\n"
            response += f"**Minimum Community Size**: {min_community_size} entities\n\n"

            if communities:
                response += "### Discovered Communities:\n\n"
                for i, community in enumerate(communities, 1):
                    response += f"#### Community {i}: {community['theme'].title()}\n"
                    response += f"**Size**: {len(community['members'])} entities\n"
                    response += f"**Cohesion**: {community['cohesion']:.2f}\n"
                    response += f"**Key Members**: {', '.join(community['members'][:5])}\n"
                    if len(community["members"]) > 5:
                        response += f" (and {len(community['members']) - 5} more)\n"
                    else:
                        response += "\n"

                    if community["connections"]:
                        response += (
                            f"**Main Connections**: {', '.join(community['connections'][:3])}\n"
                        )
                    response += "\n"

                # Community insights
                response += "### Community Insights:\n"
                total_entities = sum(len(c["members"]) for c in communities)
                avg_size = total_entities / len(communities) if communities else 0
                high_cohesion = len([c for c in communities if c["cohesion"] > 0.7])

                response += f"- **Average community size**: {avg_size:.1f} entities\n"
                response += f"- **High-cohesion communities**: {high_cohesion}\n"
                response += f"- **Network density**: {'High' if high_cohesion > len(communities)/2 else 'Medium' if high_cohesion > 0 else 'Low'}\n"

            else:
                response += "No clear communities detected for the given criteria.\n\n"
                response += "**Suggestions:**\n"
                response += "- Try broader topic focus\n"
                response += "- Reduce minimum community size\n"
                response += "- Use more general search terms\n"

            logger.info(f"Detected {len(communities)} communities")
            return response

        except Exception as e:
            logger.error(f"Error detecting communities: {e}")
            return f"Error detecting communities: {str(e)}"

    def _detect_communities(
        self, results: list[Any], topic_focus: Optional[str], min_size: int
    ) -> list[dict[str, Any]]:
        """Detect communities from search results using co-occurrence analysis."""
        # Extract entities and their co-occurrences
        entity_cooccurrence = {}
        entity_contexts = {}

        for result in results:
            content = ""
            if hasattr(result, "fact") and result.fact:
                content = result.fact
            elif hasattr(result, "summary") and result.summary:
                content = result.summary

            if content:
                # Extract entities from content (simplified NER)
                entities = self._extract_entities_from_content(content)

                # Record co-occurrences
                for i, entity1 in enumerate(entities):
                    if entity1 not in entity_contexts:
                        entity_contexts[entity1] = []
                    entity_contexts[entity1].append(content)

                    if entity1 not in entity_cooccurrence:
                        entity_cooccurrence[entity1] = {}

                    for j, entity2 in enumerate(entities):
                        if i != j:
                            if entity2 not in entity_cooccurrence[entity1]:
                                entity_cooccurrence[entity1][entity2] = 0
                            entity_cooccurrence[entity1][entity2] += 1

        # Build communities using co-occurrence strength
        communities = []
        processed_entities = set()

        for entity, cooccurrences in entity_cooccurrence.items():
            if entity in processed_entities:
                continue

            # Find strongly connected entities
            community_members = [entity]
            community_connections = []

            # Sort by co-occurrence strength
            sorted_cooccurrences = sorted(cooccurrences.items(), key=lambda x: x[1], reverse=True)

            for related_entity, strength in sorted_cooccurrences[:10]:  # Top 10 related
                if (
                    related_entity not in processed_entities and strength >= 2
                ):  # Minimum co-occurrence
                    community_members.append(related_entity)
                    community_connections.append(f"{entity}-{related_entity}")

            # Only keep communities above minimum size
            if len(community_members) >= min_size:
                # Calculate community cohesion
                cohesion = self._calculate_community_cohesion(
                    community_members, entity_cooccurrence
                )

                # Determine community theme
                theme = self._determine_community_theme(
                    community_members, entity_contexts, topic_focus
                )

                communities.append(
                    {
                        "theme": theme,
                        "members": community_members,
                        "connections": community_connections,
                        "cohesion": cohesion,
                    }
                )

                # Mark entities as processed
                processed_entities.update(community_members)

        # Sort by cohesion
        communities.sort(key=lambda x: x["cohesion"], reverse=True)

        return communities

    def _extract_entities_from_content(self, content: str) -> list[str]:
        """Extract potential entities from content using simple patterns."""
        import re

        # Extract capitalized phrases (potential entity names)
        entity_patterns = re.findall(r"\b[A-Z][a-zA-Z\s&.-]{2,30}(?:[A-Z][a-zA-Z]{2,}|\b)", content)

        # Filter and clean entities
        entities = []
        for entity in entity_patterns:
            entity = entity.strip()
            if len(entity) > 2 and len(entity) < 50:
                # Remove common non-entity words
                if not any(
                    word in entity.lower() for word in ["the", "and", "or", "but", "this", "that"]
                ):
                    entities.append(entity)

        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)

        return unique_entities[:20]  # Limit to top 20 entities per content

    def _calculate_community_cohesion(
        self, members: list[str], cooccurrence_matrix: dict[str, dict[str, int]]
    ) -> float:
        """Calculate how tightly connected community members are."""
        if len(members) < 2:
            return 0.0

        total_possible_connections = len(members) * (len(members) - 1)
        actual_connections = 0
        connection_strength = 0

        for member1 in members:
            for member2 in members:
                if member1 != member2 and member1 in cooccurrence_matrix:
                    if member2 in cooccurrence_matrix[member1]:
                        actual_connections += 1
                        connection_strength += cooccurrence_matrix[member1][member2]

        # Calculate cohesion as combination of connection ratio and strength
        connection_ratio = (
            actual_connections / total_possible_connections if total_possible_connections > 0 else 0
        )
        avg_strength = connection_strength / actual_connections if actual_connections > 0 else 0

        # Normalize strength (assuming max reasonable co-occurrence is 10)
        normalized_strength = min(avg_strength / 10.0, 1.0)

        return (connection_ratio + normalized_strength) / 2

    def _determine_community_theme(
        self, members: list[str], contexts: dict[str, list[str]], topic_focus: Optional[str]
    ) -> str:
        """Determine the main theme of a community."""
        # Collect all contexts for community members
        all_contexts = []
        for member in members:
            if member in contexts:
                all_contexts.extend(contexts[member])

        # Extract common themes
        combined_text = " ".join(all_contexts).lower()

        # Predefined themes for political/regulatory content
        theme_keywords = {
            "ai_regulation": ["artificial intelligence", "ai", "machine learning", "algorithm"],
            "data_privacy": ["privacy", "data protection", "gdpr", "personal data"],
            "digital_services": ["digital", "platform", "online", "internet", "digital services"],
            "financial_regulation": ["financial", "banking", "payment", "fintech", "money"],
            "competition": ["competition", "antitrust", "monopoly", "market", "dominant"],
            "cybersecurity": ["cyber", "security", "breach", "attack", "protection"],
            "environmental": ["environment", "climate", "carbon", "sustainability", "green"],
            "trade": ["trade", "import", "export", "tariff", "commerce"],
            "general_policy": ["policy", "regulation", "law", "rule", "governance"],
        }

        # Score themes based on keyword frequency
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(combined_text.count(keyword) for keyword in keywords)
            if score > 0:
                theme_scores[theme] = score

        # Use topic focus if provided and relevant
        if topic_focus and any(
            focus_word in combined_text for focus_word in topic_focus.lower().split()
        ):
            return topic_focus.lower().replace(" ", "_")

        # Return highest scoring theme
        if theme_scores:
            return max(theme_scores.items(), key=lambda x: x[1])[0]

        return "general"


class CommunityMembersTool(BaseTool):
    """Tool for exploring members of a specific community."""

    name: str = "get_community_members"
    description: str = "Get the members of a specific community or cluster. Shows entities that belong to the same thematic group."
    args_schema: type[BaseModel] = CommunityMembersInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        community_topic: str,
        max_members: int = 10,
        member_types: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        community_topic: str,
        max_members: int = 10,
        member_types: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get members of a specific community."""
        try:
            logger.info(f"Getting community members for: {community_topic}")

            # Build community member search query
            search_query = (
                f"{community_topic} members organizations companies policies entities related"
            )
            if member_types:
                search_query += " " + " ".join(member_types)

            # Use comprehensive search for community members
            search_results = await self.client._search(
                query=search_query, config=COMBINED_HYBRID_SEARCH_RRF
            )

            # Extract results
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, "nodes") and search_results.nodes:
                results.extend(search_results.nodes)

            if not results:
                return f"No community members found for topic: {community_topic}"

            # Extract and categorize community members
            members = self._extract_community_members(results, community_topic, member_types)

            # Limit to max members
            members = members[:max_members]

            # Format community members analysis
            response = f"## Community Members: {community_topic.title()}\n\n"
            if member_types:
                response += f"**Member Types Filter**: {', '.join(member_types)}\n"
            response += f"**Members Found**: {len(members)}\n\n"

            if members:
                # Group by member type
                member_groups = {}
                for member in members:
                    member_type = member["type"]
                    if member_type not in member_groups:
                        member_groups[member_type] = []
                    member_groups[member_type].append(member)

                response += "### Community Members by Type:\n\n"
                for member_type, type_members in member_groups.items():
                    response += f"#### {member_type.title()} ({len(type_members)} members):\n"
                    for i, member in enumerate(type_members, 1):
                        response += f"{i}. **{member['name']}**\n"
                        response += f"   Relevance: {member['relevance']:.2f}\n"
                        response += f"   Context: {member['context'][:100]}...\n"
                        if member["connections"]:
                            response += f"   Connected to: {', '.join(member['connections'][:3])}\n"
                        response += "\n"

                # Community analysis
                response += "### Community Analysis:\n"
                total_relevance = sum(m["relevance"] for m in members)
                avg_relevance = total_relevance / len(members) if members else 0
                high_relevance = len([m for m in members if m["relevance"] > 0.7])

                response += f"- **Member types**: {len(member_groups)}\n"
                response += f"- **Average relevance**: {avg_relevance:.2f}\n"
                response += f"- **High-relevance members**: {high_relevance}\n"
                response += f"- **Community cohesion**: {'Strong' if high_relevance > len(members)/2 else 'Moderate' if high_relevance > 0 else 'Weak'}\n"

            else:
                response += f"No clear community members found for {community_topic}.\n\n"
                response += "**Suggestions:**\n"
                response += "- Try broader topic terms\n"
                response += "- Remove member type filters\n"
                response += "- Use alternative topic names\n"

            logger.info(f"Found {len(members)} community members")
            return response

        except Exception as e:
            logger.error(f"Error getting community members: {e}")
            return f"Error getting community members for {community_topic}: {str(e)}"

    def _extract_community_members(
        self, results: list[Any], community_topic: str, member_types: Optional[list[str]]
    ) -> list[dict[str, Any]]:
        """Extract and score community members from search results."""
        members = []
        processed_names = set()

        for result in results:
            content = ""
            if hasattr(result, "fact") and result.fact:
                content = result.fact
            elif hasattr(result, "summary") and result.summary:
                content = result.summary

            if content:
                # Extract potential member entities
                entities = self._extract_entities_from_content(content)

                for entity in entities:
                    if entity not in processed_names:
                        # Score relevance to community topic
                        relevance = self._calculate_member_relevance(
                            entity, content, community_topic
                        )

                        if relevance > 0.3:  # Minimum relevance threshold
                            # Determine member type
                            member_type = self._classify_member_type(entity, content)

                            # Filter by member types if specified
                            if member_types and member_type not in [
                                mt.lower() for mt in member_types
                            ]:
                                continue

                            # Extract connections
                            connections = self._extract_member_connections(entity, content)

                            members.append(
                                {
                                    "name": entity,
                                    "type": member_type,
                                    "relevance": relevance,
                                    "context": content,
                                    "connections": connections,
                                }
                            )

                            processed_names.add(entity)

        # Sort by relevance
        members.sort(key=lambda x: x["relevance"], reverse=True)

        return members

    def _extract_entities_from_content(self, content: str) -> list[str]:
        """Extract potential entities from content using simple patterns."""
        import re

        # Extract capitalized phrases (potential entity names)
        entity_patterns = re.findall(r"\b[A-Z][a-zA-Z\s&.-]{2,30}(?:[A-Z][a-zA-Z]{2,}|\b)", content)

        # Filter and clean entities
        entities = []
        for entity in entity_patterns:
            entity = entity.strip()
            if len(entity) > 2 and len(entity) < 50:
                # Remove common non-entity words
                if not any(
                    word in entity.lower()
                    for word in ["the", "and", "or", "but", "this", "that", "which", "what"]
                ):
                    entities.append(entity)

        return list(set(entities))[:15]  # Remove duplicates and limit

    def _calculate_member_relevance(self, entity: str, content: str, community_topic: str) -> float:
        """Calculate how relevant an entity is to the community topic."""
        content_lower = content.lower()
        entity_lower = entity.lower()
        topic_lower = community_topic.lower()

        relevance_score = 0.0

        # Base score for entity mention
        relevance_score += 0.3

        # Score for topic keywords in same context
        topic_words = topic_lower.split()
        for word in topic_words:
            if word in content_lower:
                relevance_score += 0.2

        # Score for co-occurrence strength
        entity_pos = content_lower.find(entity_lower)
        if entity_pos != -1:
            # Check proximity to topic keywords
            for word in topic_words:
                word_pos = content_lower.find(word)
                if word_pos != -1:
                    distance = abs(entity_pos - word_pos)
                    if distance < 100:  # Close proximity
                        relevance_score += 0.2

        # Score for relationship indicators
        relationship_words = ["related", "connected", "involved", "part of", "member", "associated"]
        for rel_word in relationship_words:
            if rel_word in content_lower:
                relevance_score += 0.1

        return min(relevance_score, 1.0)

    def _classify_member_type(self, entity: str, content: str) -> str:
        """Classify the type of community member."""
        entity_lower = entity.lower()
        content_lower = content.lower()

        # Classification keywords
        type_keywords = {
            "policy": ["act", "law", "regulation", "directive", "policy", "rule"],
            "company": ["company", "corporation", "inc", "ltd", "gmbh", "ag", "firm"],
            "organization": ["organization", "agency", "authority", "commission", "committee"],
            "politician": ["minister", "commissioner", "president", "director", "ceo", "official"],
            "jurisdiction": ["union", "country", "state", "nation", "jurisdiction", "territory"],
            "technology": ["platform", "system", "technology", "service", "software", "app"],
        }

        # Check entity name
        for entity_type, keywords in type_keywords.items():
            if any(keyword in entity_lower for keyword in keywords):
                return entity_type

        # Check context
        for entity_type, keywords in type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return entity_type

        return "entity"

    def _extract_member_connections(self, entity: str, content: str) -> list[str]:
        """Extract other entities connected to this member."""
        # Simple extraction of other capitalized entities in the same content
        import re

        entities = re.findall(r"\b[A-Z][a-zA-Z\s&.-]{2,30}(?:[A-Z][a-zA-Z]{2,}|\b)", content)
        connections = []

        for other_entity in entities:
            other_entity = other_entity.strip()
            if (
                other_entity != entity
                and len(other_entity) > 2
                and len(other_entity) < 50
                and not any(word in other_entity.lower() for word in ["the", "and", "or", "but"])
            ):
                connections.append(other_entity)

        return list(set(connections))[:5]  # Remove duplicates and limit


class PolicyClustersTool(BaseTool):
    """Tool for identifying clusters of related policies."""

    name: str = "get_policy_clusters"
    description: str = "Identify clusters of related policies and regulations. Groups policies by theme, jurisdiction, or time period."
    args_schema: type[BaseModel] = PolicyClustersInput

    client: Graphiti = None

    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client

    class Config:
        arbitrary_types_allowed = True

    def _run(
        self,
        policy_area: Optional[str] = None,
        cluster_method: str = "thematic",
        max_clusters: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        policy_area: Optional[str] = None,
        cluster_method: str = "thematic",
        max_clusters: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Identify policy clusters."""
        try:
            logger.info(
                f"Identifying policy clusters (area: {policy_area}, method: {cluster_method})"
            )

            # Build policy search query
            if policy_area:
                search_query = f"{policy_area} policy regulation law directive act legislation"
            else:
                search_query = "policy regulation law directive act legislation rules"

            # Use node search for better policy entity detection
            search_results = await self.client._search(
                query=search_query, config=NODE_HYBRID_SEARCH_RRF
            )

            # Extract results
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, "nodes") and search_results.nodes:
                results.extend(search_results.nodes)

            if not results:
                return f"No policies found for area: {policy_area or 'general'}"

            # Extract and cluster policies
            policy_clusters = self._cluster_policies(results, cluster_method, policy_area)

            # Limit to max clusters
            policy_clusters = policy_clusters[:max_clusters]

            # Format policy clusters analysis
            response = "## Policy Clusters Analysis\n\n"
            if policy_area:
                response += f"**Policy Area**: {policy_area}\n"
            response += f"**Clustering Method**: {cluster_method}\n"
            response += f"**Clusters Found**: {len(policy_clusters)}\n\n"

            if policy_clusters:
                response += "### Policy Clusters:\n\n"
                for i, cluster in enumerate(policy_clusters, 1):
                    response += f"#### Cluster {i}: {cluster['name'].title()}\n"
                    response += f"**Theme**: {cluster['theme']}\n"
                    response += f"**Policies**: {len(cluster['policies'])}\n"
                    response += f"**Cohesion**: {cluster['cohesion']:.2f}\n"

                    response += "**Key Policies**:\n"
                    for j, policy in enumerate(cluster["policies"][:5], 1):
                        response += f"  {j}. {policy['name']}\n"
                        if policy["jurisdiction"]:
                            response += f"     Jurisdiction: {policy['jurisdiction']}\n"

                    if len(cluster["policies"]) > 5:
                        response += f"  ... and {len(cluster['policies']) - 5} more policies\n"

                    if cluster["relationships"]:
                        response += (
                            f"**Common Relationships**: {', '.join(cluster['relationships'][:3])}\n"
                        )
                    response += "\n"

                # Cluster insights
                response += "### Cluster Insights:\n"
                total_policies = sum(len(c["policies"]) for c in policy_clusters)
                avg_cluster_size = total_policies / len(policy_clusters) if policy_clusters else 0
                high_cohesion = len([c for c in policy_clusters if c["cohesion"] > 0.7])

                response += f"- **Total policies clustered**: {total_policies}\n"
                response += f"- **Average cluster size**: {avg_cluster_size:.1f} policies\n"
                response += f"- **High-cohesion clusters**: {high_cohesion}\n"
                response += f"- **Policy landscape complexity**: {'High' if len(policy_clusters) > 3 else 'Medium' if len(policy_clusters) > 1 else 'Low'}\n"

            else:
                response += "No clear policy clusters found.\n\n"
                response += "**Suggestions:**\n"
                response += "- Try broader policy area terms\n"
                response += "- Use different clustering method\n"
                response += "- Expand search to include related terms\n"

            logger.info(f"Found {len(policy_clusters)} policy clusters")
            return response

        except Exception as e:
            logger.error(f"Error clustering policies: {e}")
            return f"Error clustering policies: {str(e)}"

    def _cluster_policies(
        self, results: list[Any], cluster_method: str, policy_area: Optional[str]
    ) -> list[dict[str, Any]]:
        """Cluster policies based on the specified method."""
        # Extract policies from results
        policies = []
        for result in results:
            content = ""
            if hasattr(result, "fact") and result.fact:
                content = result.fact
            elif hasattr(result, "summary") and result.summary:
                content = result.summary

            if content:
                extracted_policies = self._extract_policies_from_content(content, policy_area)
                policies.extend(extracted_policies)

        # Remove duplicates
        unique_policies = []
        seen_names = set()
        for policy in policies:
            if policy["name"] not in seen_names:
                unique_policies.append(policy)
                seen_names.add(policy["name"])

        policies = unique_policies

        if not policies:
            return []

        # Apply clustering method
        if cluster_method == "thematic":
            return self._cluster_by_theme(policies)
        elif cluster_method == "jurisdictional":
            return self._cluster_by_jurisdiction(policies)
        elif cluster_method == "temporal":
            return self._cluster_by_temporal_period(policies)
        else:
            return self._cluster_by_theme(policies)  # Default to thematic

    def _extract_policies_from_content(
        self, content: str, policy_area: Optional[str]
    ) -> list[dict[str, Any]]:
        """Extract policy information from content."""
        import re

        policies = []

        # Look for policy patterns
        policy_patterns = [
            r"([A-Z][a-zA-Z\s]+(?:Act|Regulation|Directive|Law|Policy|Rule))",
            r"((?:EU|European|US|American|UK|British)\s+[A-Z][a-zA-Z\s]+(?:Act|Regulation|Directive))",
            r"([A-Z][A-Z]{2,}\s*(?:Act|Regulation|Directive))",  # Acronyms
        ]

        for pattern in policy_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                policy_name = match.strip()
                if len(policy_name) > 5 and len(policy_name) < 100:
                    # Extract additional information
                    jurisdiction = self._extract_jurisdiction(content, policy_name)
                    theme = self._extract_policy_theme(content, policy_name, policy_area)

                    policies.append(
                        {
                            "name": policy_name,
                            "content": content,
                            "jurisdiction": jurisdiction,
                            "theme": theme,
                            "context": content[:200] + "..." if len(content) > 200 else content,
                        }
                    )

        return policies

    def _extract_jurisdiction(self, content: str, policy_name: str) -> str:
        """Extract jurisdiction for a policy."""
        content_lower = content.lower()

        jurisdictions = {
            "EU": ["european union", "eu", "europe", "european"],
            "US": ["united states", "us", "america", "american", "federal"],
            "UK": ["united kingdom", "uk", "britain", "british"],
            "Germany": ["germany", "german", "deutschland"],
            "France": ["france", "french"],
            "International": ["international", "global", "worldwide"],
        }

        for jurisdiction, keywords in jurisdictions.items():
            if any(keyword in content_lower for keyword in keywords):
                return jurisdiction

        return "Unknown"

    def _extract_policy_theme(
        self, content: str, policy_name: str, policy_area: Optional[str]
    ) -> str:
        """Extract theme for a policy."""
        content_lower = content.lower()
        policy_lower = policy_name.lower()

        themes = {
            "data_privacy": ["privacy", "data protection", "gdpr", "personal data"],
            "ai_regulation": ["artificial intelligence", "ai", "machine learning", "algorithm"],
            "digital_services": ["digital", "platform", "online", "internet"],
            "competition": ["competition", "antitrust", "monopoly", "market"],
            "financial": ["financial", "banking", "payment", "money"],
            "environmental": ["environment", "climate", "carbon", "green"],
            "cybersecurity": ["cyber", "security", "breach", "protection"],
            "trade": ["trade", "import", "export", "commerce"],
        }

        # Use policy area as primary theme if provided
        if policy_area:
            return policy_area.lower().replace(" ", "_")

        # Score themes
        theme_scores = {}
        for theme, keywords in themes.items():
            score = sum(
                content_lower.count(keyword) + policy_lower.count(keyword) for keyword in keywords
            )
            if score > 0:
                theme_scores[theme] = score

        if theme_scores:
            return max(theme_scores.items(), key=lambda x: x[1])[0]

        return "general"

    def _cluster_by_theme(self, policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Cluster policies by theme."""
        theme_clusters = {}

        for policy in policies:
            theme = policy["theme"]
            if theme not in theme_clusters:
                theme_clusters[theme] = []
            theme_clusters[theme].append(policy)

        clusters = []
        for theme, theme_policies in theme_clusters.items():
            if len(theme_policies) >= 2:  # Minimum cluster size
                cohesion = self._calculate_policy_cohesion(theme_policies, "theme")
                relationships = self._extract_cluster_relationships(theme_policies)

                clusters.append(
                    {
                        "name": theme.replace("_", " "),
                        "theme": theme,
                        "policies": theme_policies,
                        "cohesion": cohesion,
                        "relationships": relationships,
                    }
                )

        return sorted(clusters, key=lambda x: x["cohesion"], reverse=True)

    def _cluster_by_jurisdiction(self, policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Cluster policies by jurisdiction."""
        jurisdiction_clusters = {}

        for policy in policies:
            jurisdiction = policy["jurisdiction"]
            if jurisdiction not in jurisdiction_clusters:
                jurisdiction_clusters[jurisdiction] = []
            jurisdiction_clusters[jurisdiction].append(policy)

        clusters = []
        for jurisdiction, juris_policies in jurisdiction_clusters.items():
            if len(juris_policies) >= 2:
                cohesion = self._calculate_policy_cohesion(juris_policies, "jurisdiction")
                relationships = self._extract_cluster_relationships(juris_policies)

                clusters.append(
                    {
                        "name": jurisdiction,
                        "theme": "jurisdictional",
                        "policies": juris_policies,
                        "cohesion": cohesion,
                        "relationships": relationships,
                    }
                )

        return sorted(clusters, key=lambda x: x["cohesion"], reverse=True)

    def _cluster_by_temporal_period(self, policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Cluster policies by temporal periods."""
        # Simple temporal clustering based on years mentioned
        import re

        temporal_clusters = {}

        for policy in policies:
            years = re.findall(r"\b(20\d{2})\b", policy["content"])
            if years:
                decade = f"{years[0][:3]}0s"
                if decade not in temporal_clusters:
                    temporal_clusters[decade] = []
                temporal_clusters[decade].append(policy)
            else:
                if "unknown" not in temporal_clusters:
                    temporal_clusters["unknown"] = []
                temporal_clusters["unknown"].append(policy)

        clusters = []
        for period, period_policies in temporal_clusters.items():
            if len(period_policies) >= 2:
                cohesion = self._calculate_policy_cohesion(period_policies, "temporal")
                relationships = self._extract_cluster_relationships(period_policies)

                clusters.append(
                    {
                        "name": period,
                        "theme": "temporal",
                        "policies": period_policies,
                        "cohesion": cohesion,
                        "relationships": relationships,
                    }
                )

        return sorted(clusters, key=lambda x: x["cohesion"], reverse=True)

    def _calculate_policy_cohesion(
        self, policies: list[dict[str, Any]], cluster_type: str
    ) -> float:
        """Calculate cohesion within a policy cluster."""
        if len(policies) < 2:
            return 0.0

        # Calculate based on shared characteristics
        if cluster_type == "theme":
            # All policies share the same theme
            return 0.8 + (0.2 * min(len(policies) / 10, 1))  # Bonus for larger clusters
        elif cluster_type == "jurisdiction":
            # Check theme diversity within jurisdiction
            themes = set(p["theme"] for p in policies)
            diversity_penalty = len(themes) / len(policies)
            return max(0.6 - diversity_penalty, 0.3)
        elif cluster_type == "temporal":
            # Check theme and jurisdiction diversity within time period
            themes = set(p["theme"] for p in policies)
            jurisdictions = set(p["jurisdiction"] for p in policies)
            diversity_score = (len(themes) + len(jurisdictions)) / (2 * len(policies))
            return max(0.7 - diversity_score, 0.3)

        return 0.5

    def _extract_cluster_relationships(self, policies: list[dict[str, Any]]) -> list[str]:
        """Extract common relationships within a policy cluster."""
        # Extract common terms that might indicate relationships
        all_content = " ".join(p["content"] for p in policies).lower()

        relationship_terms = [
            "implements",
            "amends",
            "supersedes",
            "complements",
            "enforces",
            "requires",
            "mandates",
            "prohibits",
            "regulates",
            "governs",
        ]

        found_relationships = []
        for term in relationship_terms:
            if term in all_content:
                found_relationships.append(term)

        return found_relationships
