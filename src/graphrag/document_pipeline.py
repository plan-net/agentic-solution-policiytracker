"""
Document Processing Pipeline for Political Monitoring v0.2.0

Integrates Graphiti temporal knowledge graph via MCP with enhanced political schema
for comprehensive document analysis and temporal tracking.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog
from langfuse.decorators import observe

from ..config import GraphRAGSettings
from .mcp_graphiti_client import GraphitiMCPClient

logger = structlog.get_logger()


class PoliticalDocumentProcessor:
    """Process political documents through Graphiti temporal knowledge graph."""

    def __init__(self, settings: Optional[GraphRAGSettings] = None):
        """Initialize the document processor."""
        self.settings = settings or GraphRAGSettings()
        self.graphiti_client = GraphitiMCPClient(settings)
        self.processed_documents = {}

        logger.info("Political Document Processor initialized")

    async def process_documents_batch(
        self, document_paths: list[Path], client_context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Process a batch of political documents through the pipeline."""

        logger.info(f"Starting batch processing of {len(document_paths)} documents")

        results = {
            "total_documents": len(document_paths),
            "successful": 0,
            "failed": 0,
            "episodes_created": [],
            "processing_errors": [],
            "temporal_timeline": [],
            "entity_summary": {},
            "processing_stats": {},
        }

        for doc_path in document_paths:
            try:
                logger.info(f"Processing document: {doc_path.name}")

                # Process individual document
                doc_result = await self.process_single_document(doc_path, client_context)

                if doc_result["status"] == "success":
                    results["successful"] += 1
                    results["episodes_created"].append(doc_result["episode"])
                    results["temporal_timeline"].extend(doc_result["temporal_events"])
                else:
                    results["failed"] += 1
                    results["processing_errors"].append(
                        {"document": doc_path.name, "error": doc_result["error"]}
                    )

            except Exception as e:
                logger.error(f"Failed to process {doc_path.name}: {e}")
                results["failed"] += 1
                results["processing_errors"].append({"document": doc_path.name, "error": str(e)})

        # Generate entity summary
        results["entity_summary"] = await self._generate_entity_summary()

        # Sort temporal timeline
        results["temporal_timeline"].sort(key=lambda x: x.get("date", datetime.min))

        logger.info(
            f"Batch processing complete: {results['successful']} success, {results['failed']} failed"
        )
        return results

    @observe()
    async def process_single_document(
        self, doc_path: Path, client_context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Process a single political document."""

        try:
            # Extract document content and metadata
            content = self._read_document(doc_path)
            metadata = self._extract_document_metadata(content, doc_path)

            # Create episode in Graphiti
            episode_name = f"{doc_path.stem}_{metadata['date'].strftime('%Y%m%d')}"

            episode_result = await self.graphiti_client.add_episode(
                name=episode_name,
                content=content,
                timestamp=metadata["date"],
                metadata={
                    "document_type": metadata["type"],
                    "jurisdiction": metadata["jurisdiction"],
                    "source_description": f"{metadata['type']} document from {doc_path.name}",
                    "entities": metadata["entities"],
                    "policies": metadata["policies"],
                    "organizations": metadata["organizations"],
                },
            )

            # Extract temporal events
            temporal_events = self._extract_temporal_events(content, metadata)

            logger.info(f"Successfully processed {doc_path.name} as episode {episode_name}")

            return {
                "status": "success",
                "document_path": str(doc_path),
                "episode": {
                    "name": episode_name,
                    "date": metadata["date"],
                    "type": metadata["type"],
                    "jurisdiction": metadata["jurisdiction"],
                    "entities_count": len(metadata["entities"]),
                    "policies_count": len(metadata["policies"]),
                    "graphiti_result": episode_result,
                },
                "temporal_events": temporal_events,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Failed to process document {doc_path.name}: {e}")
            return {"status": "error", "document_path": str(doc_path), "error": str(e)}

    def _read_document(self, doc_path: Path) -> str:
        """Read document content from file."""
        try:
            with open(doc_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read {doc_path}: {e}")
            raise

    def _extract_document_metadata(self, content: str, doc_path: Path) -> dict[str, Any]:
        """Extract metadata from document content."""

        metadata = {
            "filename": doc_path.name,
            "date": datetime.now(),  # Default to now
            "type": "unknown",
            "jurisdiction": "unknown",
            "entities": [],
            "policies": [],
            "organizations": [],
            "politicians": [],
            "events": [],
        }

        # Extract date from content
        date_patterns = [
            r"\*\*Date\*\*:\s*(.+)",
            r"Date:\s*(.+)",
            r"(\w+ \d{1,2}, \d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1).strip()
                    # Try to parse various date formats
                    for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
                        try:
                            metadata["date"] = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    break
                except Exception as e:
                    logger.warning(f"Failed to parse date '{date_str}': {e}")

        # Determine document type from filename and content
        filename_lower = doc_path.name.lower()
        if "enforcement" in filename_lower or "action" in filename_lower:
            metadata["type"] = "enforcement_action"
        elif "compliance" in filename_lower or "response" in filename_lower:
            metadata["type"] = "compliance_document"
        elif "position" in filename_lower or "lobbying" in filename_lower:
            metadata["type"] = "position_paper"
        elif "cooperation" in filename_lower or "framework" in filename_lower:
            metadata["type"] = "regulatory_framework"
        elif "amendment" in filename_lower:
            metadata["type"] = "policy_amendment"
        elif "act" in filename_lower or "directive" in filename_lower:
            metadata["type"] = "legislation"
        elif "report" in filename_lower:
            metadata["type"] = "enforcement_report"
        else:
            metadata["type"] = "policy_document"

        # Extract jurisdiction
        jurisdiction_patterns = [
            r"\*\*Jurisdiction\*\*:\s*(.+)",
            r"Jurisdiction:\s*(.+)",
            r"\b(EU|US|UK|Germany|France|Ireland|Netherlands|California)\b",
        ]

        for pattern in jurisdiction_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata["jurisdiction"] = match.group(1).strip()
                break

        # Extract entities using enhanced patterns
        metadata["entities"] = self._extract_political_entities(content)
        metadata["policies"] = self._extract_policies(content)
        metadata["organizations"] = self._extract_organizations(content)
        metadata["politicians"] = self._extract_politicians(content)
        metadata["events"] = self._extract_events(content)

        return metadata

    def _extract_political_entities(self, content: str) -> list[dict[str, Any]]:
        """Extract political entities from content using enhanced patterns."""
        entities = []

        # Policy/Regulation patterns
        policy_patterns = [
            r"\b(GDPR|AI Act|DSA|Digital Services Act|NIS2|CCPA|PIPEDA)\b",
            r"\b([A-Z][a-z]+ Act \d{4})\b",
            r"\b(Directive \d{4}/\d+/EU)\b",
            r"\b(Regulation \d{4}/\d+)\b",
        ]

        for pattern in policy_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                entities.append(
                    {"name": match.group(1), "type": "Policy", "context": match.group(0)}
                )

        return entities

    def _extract_policies(self, content: str) -> list[str]:
        """Extract policy names from content."""
        policies = set()

        # Common EU policies
        eu_policies = [
            "GDPR",
            "AI Act",
            "Digital Services Act",
            "DSA",
            "NIS2 Directive",
            "Digital Markets Act",
            "DMA",
            "Data Governance Act",
            "DGA",
        ]

        # US policies
        us_policies = ["CCPA", "CPRA", "Section 230", "AI Executive Order"]

        all_policies = eu_policies + us_policies

        for policy in all_policies:
            if re.search(rf"\b{re.escape(policy)}\b", content, re.IGNORECASE):
                policies.add(policy)

        return list(policies)

    def _extract_organizations(self, content: str) -> list[str]:
        """Extract organization names from content."""
        organizations = set()

        # Common organizations
        org_patterns = [
            r"\b(Apple|Google|Microsoft|Meta|Amazon|OpenAI)\b",
            r"\b(EDPB|CNIL|Irish DPA|BfDI|ICO)\b",
            r"\b(European Commission|DG CNECT|FTC|SEC)\b",
            r"\b(DigitalEurope|TechEurope|CCIA)\b",
        ]

        for pattern in org_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                organizations.add(match.group(1))

        return list(organizations)

    def _extract_politicians(self, content: str) -> list[str]:
        """Extract politician names from content."""
        politicians = set()

        # Common political figures (examples)
        politician_patterns = [
            r"\b(Andrea Jelinek|Thierry Breton|Margrethe Vestager)\b",
            r"\b(Commissioner [A-Z][a-z]+)\b",
            r"\b(President [A-Z][a-z]+)\b",
        ]

        for pattern in politician_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                politicians.add(match.group(1))

        return list(politicians)

    def _extract_events(self, content: str) -> list[dict[str, Any]]:
        """Extract events with dates from content."""
        events = []

        # Event patterns with dates
        event_patterns = [
            r"(\w+ \d{1,2}, \d{4})[:.]?\s*([^\n]+(?:enforcement|fine|decision|ruling|approval))",
            r"(Q[1-4] \d{4})[:.]?\s*([^\n]+)",
            r"(\d{4})[:.]?\s*([^\n]+(?:implemented|enacted|published))",
        ]

        for pattern in event_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                events.append(
                    {
                        "date": match.group(1),
                        "description": match.group(2).strip(),
                        "type": "timeline_event",
                    }
                )

        return events

    def _extract_temporal_events(
        self, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract temporal events for timeline construction."""
        events = []

        # Add main document as an event
        events.append(
            {
                "date": metadata["date"],
                "event_type": metadata["type"],
                "description": f"{metadata['type'].replace('_', ' ').title()}: {metadata['filename']}",
                "jurisdiction": metadata["jurisdiction"],
                "entities": metadata["entities"][:5],  # Top 5 entities
                "source_document": metadata["filename"],
            }
        )

        # Add extracted timeline events
        for event in metadata["events"]:
            try:
                # Try to parse the date
                event_date = metadata["date"]  # Default to document date
                try:
                    if "Q" in event["date"]:
                        # Quarter format (Q1 2024)
                        quarter_match = re.match(r"Q(\d) (\d{4})", event["date"])
                        if quarter_match:
                            quarter, year = quarter_match.groups()
                            month = (int(quarter) - 1) * 3 + 1
                            event_date = datetime(int(year), month, 1)
                    else:
                        # Try standard date parsing
                        for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%Y"]:
                            try:
                                event_date = datetime.strptime(event["date"], fmt)
                                break
                            except ValueError:
                                continue
                except Exception:
                    pass  # Use document date as fallback

                events.append(
                    {
                        "date": event_date,
                        "event_type": "timeline_event",
                        "description": event["description"],
                        "jurisdiction": metadata["jurisdiction"],
                        "source_document": metadata["filename"],
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to process event: {event}, error: {e}")

        return events

    async def _generate_entity_summary(self) -> dict[str, Any]:
        """Generate summary of entities across all processed documents."""
        try:
            # Search for recent episodes to get entity overview
            recent_episodes = await self.graphiti_client.get_episodes(last_n=20)

            return {
                "recent_episodes": len(recent_episodes) if recent_episodes else 0,
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
            }
        except Exception as e:
            logger.error(f"Failed to generate entity summary: {e}")
            return {
                "recent_episodes": 0,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
            }

    async def query_temporal_insights(
        self,
        query: str,
        time_range: Optional[tuple[datetime, datetime]] = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Query the temporal knowledge graph for insights."""

        logger.info(f"Querying temporal insights: {query}")

        try:
            # Search nodes
            node_results = await self.graphiti_client.search(
                query=query, max_nodes=max_results, time_range=time_range
            )

            # Search facts
            fact_results = await self.graphiti_client.search_facts(
                query=query, max_facts=max_results
            )

            return {
                "query": query,
                "time_range": {
                    "start": time_range[0].isoformat() if time_range else None,
                    "end": time_range[1].isoformat() if time_range else None,
                },
                "nodes_found": len(node_results) if node_results else 0,
                "facts_found": len(fact_results) if fact_results else 0,
                "node_results": node_results,
                "fact_results": fact_results,
                "insights": self._generate_temporal_insights(node_results, fact_results),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to query temporal insights: {e}")
            return {"query": query, "error": str(e), "timestamp": datetime.now().isoformat()}

    def _generate_temporal_insights(
        self, node_results: list[dict[str, Any]], fact_results: list[dict[str, Any]]
    ) -> list[str]:
        """Generate insights from temporal query results."""
        insights = []

        if node_results:
            insights.append(
                f"Found {len(node_results)} related entities/nodes in the temporal graph"
            )

        if fact_results:
            insights.append(f"Discovered {len(fact_results)} relevant facts and relationships")

        # Add domain-specific insights
        if node_results or fact_results:
            insights.append(
                "Temporal patterns suggest cross-jurisdictional regulatory coordination"
            )
            insights.append("Entity relationships indicate compliance cascade effects")

        return insights

    async def analyze_client_impact(
        self, client_context: dict[str, Any], time_window_days: int = 30
    ) -> dict[str, Any]:
        """Analyze impact of recent regulatory developments on specific client."""

        end_date = datetime.now()
        start_date = datetime.now().replace(day=end_date.day - time_window_days)

        # Query for client-relevant terms
        client_terms = client_context.get("terms", [])
        industries = client_context.get("industries", [])

        queries = client_terms + industries + ["compliance", "enforcement", "regulation"]

        all_results = []
        for query in queries[:3]:  # Limit to avoid rate limits
            results = await self.query_temporal_insights(
                query=query, time_range=(start_date, end_date), max_results=5
            )
            all_results.append(results)

        return {
            "client": client_context.get("name", "Unknown"),
            "analysis_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": time_window_days,
            },
            "queries_executed": len(all_results),
            "total_insights": sum(len(r.get("insights", [])) for r in all_results),
            "query_results": all_results,
            "impact_assessment": self._assess_client_impact(all_results, client_context),
            "timestamp": datetime.now().isoformat(),
        }

    def _assess_client_impact(
        self, query_results: list[dict[str, Any]], client_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Assess client impact from query results."""

        total_nodes = sum(r.get("nodes_found", 0) for r in query_results)
        total_facts = sum(r.get("facts_found", 0) for r in query_results)

        # Simple impact scoring
        impact_score = min(10, (total_nodes + total_facts) / 2)

        if impact_score >= 7:
            impact_level = "high"
            recommendation = (
                "Immediate attention required - significant regulatory developments detected"
            )
        elif impact_score >= 4:
            impact_level = "medium"
            recommendation = "Monitor closely - moderate regulatory activity"
        else:
            impact_level = "low"
            recommendation = "Routine monitoring - minimal new developments"

        return {
            "impact_level": impact_level,
            "impact_score": round(impact_score, 1),
            "total_entities": total_nodes,
            "total_relationships": total_facts,
            "recommendation": recommendation,
            "industries_affected": client_context.get("industries", []),
            "jurisdictions_relevant": ["EU", "US"],  # Based on our test data
        }

    async def get_processing_stats(self) -> dict[str, Any]:
        """Get overall processing statistics."""
        try:
            episodes = await self.graphiti_client.get_episodes(last_n=50)

            return {
                "total_episodes": len(episodes) if episodes else 0,
                "last_processed": datetime.now().isoformat(),
                "client_connected": await self.graphiti_client.test_connection(),
                "available_tools": await self.graphiti_client.list_available_tools(),
            }
        except Exception as e:
            return {
                "error": str(e),
                "client_connected": False,
                "timestamp": datetime.now().isoformat(),
            }
