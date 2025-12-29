"""FastAPI server for graph visualization with 2D/3D capabilities."""

import logging
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import AsyncGraphDatabase
from ray import serve

from src.config import settings

from .chat_sessions import (
    ChatSessionDetail,
    ChatSessionService,
    ChatSessionSummary,
    ChatSessionWithMessages,
)
from .reports import (
    ClaudeModel,
    CreateReportRequest,
    ReportDetail,
    ReportsService,
    ReportStatus,
    ReportSummary,
    ReportType,
    UpdateReportRequest,
)
from .assessments import (
    AssessmentDetail,
    AssessmentsService,
    AssessmentStatus,
    AssessmentSummary,
    AssessmentType,
    ChatMessageRequest,
    CreateAssessmentRequest,
    UpdateAssessmentRequest,
)
from .context_tracker import ChatContextTracker
from .models import (
    ChatContextRequest,
    ChatContextResponse,
    GraphEdge,
    GraphNode,
    HealthResponse,
    SchemaQuery,
    SchemaQueryRequest,
    SchemaQueryResponse,
    TextToCypherRequest,
    TextToCypherResponse,
)
from .schema_queries import get_default_parameters, get_schema_query, list_schema_queries
from .text_to_cypher import TextToCypherService

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Graph Visualization API",
    description="API for visualizing Neo4j knowledge graph with 2D/3D capabilities",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@serve.deployment(num_replicas=1)
@serve.ingress(app)
class GraphVizServer:
    """Ray Serve deployment for graph visualization service."""

    def __init__(self):
        self.neo4j_driver = None
        self.text_to_cypher_service = None
        self.context_tracker = None
        self.chat_session_service = None
        self.reports_service = None
        self.assessments_service = None
        logger.info("GraphVizServer initialized")

    async def _get_neo4j_driver(self):
        """Lazy initialization of Neo4j driver."""
        if self.neo4j_driver is None:
            self.neo4j_driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            )
            logger.info("Neo4j driver initialized")
        return self.neo4j_driver

    async def _get_text_to_cypher_service(self):
        """Lazy initialization of text-to-Cypher service."""
        if self.text_to_cypher_service is None:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")

            self.text_to_cypher_service = TextToCypherService(
                neo4j_uri=settings.NEO4J_URI,
                neo4j_user=settings.NEO4J_USERNAME,
                neo4j_password=settings.NEO4J_PASSWORD,
                openai_api_key=openai_key,
                database=settings.NEO4J_DATABASE,
            )
            logger.info("Text-to-Cypher service initialized")
        return self.text_to_cypher_service

    async def _get_context_tracker(self):
        """Lazy initialization of context tracker."""
        if self.context_tracker is None:
            driver = await self._get_neo4j_driver()
            self.context_tracker = ChatContextTracker(driver=driver, ttl_minutes=60)
            logger.info("Context tracker initialized")
        return self.context_tracker

    async def _get_chat_session_service(self):
        """Lazy initialization of chat session service."""
        if self.chat_session_service is None:
            driver = await self._get_neo4j_driver()
            self.chat_session_service = ChatSessionService(driver=driver)
            logger.info("Chat session service initialized")
        return self.chat_session_service

    async def _get_reports_service(self):
        """Lazy initialization of reports service."""
        if self.reports_service is None:
            driver = await self._get_neo4j_driver()
            self.reports_service = ReportsService(driver=driver)
            logger.info("Reports service initialized")
        return self.reports_service

    async def _get_assessments_service(self):
        """Lazy initialization of assessments service."""
        if self.assessments_service is None:
            driver = await self._get_neo4j_driver()
            self.assessments_service = AssessmentsService(driver=driver)
            logger.info("Assessments service initialized")
        return self.assessments_service

    @app.get("/api/graph/health")
    async def health_check(self) -> HealthResponse:
        """Health check endpoint."""
        neo4j_connected = False
        llm_available = False

        try:
            driver = await self._get_neo4j_driver()
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run("RETURN 1")
                await result.single()
            neo4j_connected = True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")

        try:
            # Just check if OpenAI API key is available, don't initialize the full service
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                # Service can be initialized when needed
                llm_available = True
            else:
                logger.warning("OPENAI_API_KEY not set - text-to-cypher will be unavailable")
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")

        return HealthResponse(
            status="healthy" if (neo4j_connected and llm_available) else "degraded",
            neo4j_connected=neo4j_connected,
            llm_available=llm_available,
            version="0.1.0",
        )

    @app.get("/api/graph/schema-queries")
    async def get_schema_queries(self) -> list[SchemaQuery]:
        """Get list of all available schema queries."""
        return list_schema_queries()

    @app.get("/api/graph/schema-query/{query_name}")
    async def execute_schema_query_get(self, query_name: str) -> SchemaQueryResponse:
        """Execute a predefined schema query with default parameters (GET method)."""
        return await self._execute_schema_query_with_params(query_name, {})

    @app.post("/api/graph/schema-query/{query_name}")
    async def execute_schema_query_post(
        self, query_name: str, request: SchemaQueryRequest
    ) -> SchemaQueryResponse:
        """Execute a predefined schema query with custom parameters (POST method)."""
        return await self._execute_schema_query_with_params(query_name, request.parameters)

    async def _execute_schema_query_with_params(
        self, query_name: str, user_params: dict
    ) -> SchemaQueryResponse:
        """Execute a schema query with merged default and user parameters."""
        query_def = get_schema_query(query_name)
        if not query_def:
            raise HTTPException(status_code=404, detail=f"Schema query '{query_name}' not found")

        # Get default parameters and merge with user-provided ones
        params = get_default_parameters(query_name)
        params.update(user_params)

        # Validate parameter types and ranges
        for param_def in query_def.parameters:
            if param_def.name in params:
                value = params[param_def.name]
                # Type validation
                if param_def.param_type == "integer":
                    try:
                        params[param_def.name] = int(value)
                    except (ValueError, TypeError):
                        params[param_def.name] = param_def.default
                    # Range validation
                    if param_def.min_value is not None:
                        params[param_def.name] = max(
                            int(param_def.min_value), params[param_def.name]
                        )
                    if param_def.max_value is not None:
                        params[param_def.name] = min(
                            int(param_def.max_value), params[param_def.name]
                        )
                elif param_def.param_type == "float":
                    try:
                        params[param_def.name] = float(value)
                    except (ValueError, TypeError):
                        params[param_def.name] = param_def.default
                elif param_def.param_type == "boolean":
                    if isinstance(value, str):
                        params[param_def.name] = value.lower() in ("true", "1", "yes")
                    else:
                        params[param_def.name] = bool(value)

        start_time = time.time()

        try:
            driver = await self._get_neo4j_driver()
            nodes, links = await self._execute_cypher_query_with_params(
                query_def.cypher, driver, params
            )

            execution_time = time.time() - start_time

            return SchemaQueryResponse(
                query_info=query_def,
                nodes=nodes,
                links=links,
                execution_time=execution_time,
                stats={
                    "node_count": len(nodes),
                    "edge_count": len(links),
                    "query_name": query_name,
                    "parameters_used": params,
                },
            )

        except Exception as e:
            logger.error(f"Error executing schema query '{query_name}': {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/graph/text-to-cypher")
    async def text_to_cypher(self, request: TextToCypherRequest) -> TextToCypherResponse:
        """Convert natural language to Cypher and execute the query."""
        try:
            service = await self._get_text_to_cypher_service()
            driver = await self._get_neo4j_driver()

            result = await service.convert_and_execute(
                text=request.text, limit=request.limit, driver=driver
            )

            return TextToCypherResponse(**result)

        except Exception as e:
            logger.error(f"Error in text-to-Cypher: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/graph/chat-context")
    async def get_chat_context(self, request: ChatContextRequest) -> ChatContextResponse:
        """Get graph context from a chat session."""
        try:
            logger.warning(f"📥 Received chat context request for session: {request.session_id}")
            context_tracker = await self._get_context_tracker()

            context_data = await context_tracker.get_context_graph(
                session_id=request.session_id, query_text=request.query
            )

            logger.warning(
                f"📤 Returning context: {len(context_data['nodes'])} nodes, {len(context_data['links'])} links"
            )

            # Check if there's an error in metadata
            if "error" in context_data.get("metadata", {}):
                logger.error(f"⚠️  Context has error: {context_data['metadata']['error']}")

            # Deep sanitize metadata to ensure no Neo4j types remain
            sanitized_metadata = self._deep_sanitize(context_data["metadata"])

            return ChatContextResponse(
                nodes=context_data["nodes"],
                links=context_data["links"],
                metadata=sanitized_metadata,
            )

        except Exception as e:
            logger.error(
                f"❌ Error getting chat context for session {request.session_id}: {e}",
                exc_info=True,
            )
            # Return an error response instead of raising HTTPException
            return ChatContextResponse(
                nodes=[],
                links=[],
                metadata={
                    "session_id": request.session_id,
                    "error": f"Server error: {str(e)}",
                    "error_type": type(e).__name__,
                },
            )

    # ============== Chat Session Endpoints ==============

    @app.get("/api/chat/sessions")
    async def list_chat_sessions(self, limit: int = 50) -> list[ChatSessionSummary]:
        """List recent chat sessions."""
        try:
            service = await self._get_chat_session_service()
            return await service.list_sessions(limit=limit)
        except Exception as e:
            logger.error(f"Error listing chat sessions: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/chat/sessions/{session_id}")
    async def get_chat_session(self, session_id: str) -> ChatSessionDetail:
        """Get details of a specific chat session."""
        try:
            service = await self._get_chat_session_service()
            session = await service.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            return session
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting chat session {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/chat/sessions/{session_id}/messages")
    async def get_chat_session_messages(self, session_id: str) -> ChatSessionWithMessages:
        """Get a chat session with all messages."""
        try:
            service = await self._get_chat_session_service()
            session = await service.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

            messages = await service.get_session_messages(session_id)

            return ChatSessionWithMessages(
                session_id=session.session_id,
                title=session.title,
                created_at=session.created_at,
                last_updated=session.last_updated,
                messages=messages,
                entity_count=len(session.entity_uuids),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting chat session messages {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/chat/sessions/{session_id}")
    async def delete_chat_session(self, session_id: str) -> dict:
        """Delete a chat session."""
        try:
            service = await self._get_chat_session_service()
            deleted = await service.delete_session(session_id)
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            return {"status": "deleted", "session_id": session_id}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting chat session {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.patch("/api/chat/sessions/{session_id}/title")
    async def update_chat_session_title(self, session_id: str, title: str) -> dict:
        """Update the title of a chat session."""
        try:
            service = await self._get_chat_session_service()
            updated = await service.update_session_title(session_id, title)
            if not updated:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            return {"status": "updated", "session_id": session_id, "title": title}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating chat session title {session_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # ============== Reports Endpoints ==============

    @app.get("/api/reports")
    async def list_reports(
        self,
        limit: int = 50,
        status: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> list[ReportSummary]:
        """List reports with optional filters."""
        try:
            service = await self._get_reports_service()

            # Convert string params to enums if provided
            status_enum = ReportStatus(status) if status else None
            type_enum = ReportType(report_type) if report_type else None

            return await service.list_reports(
                limit=limit,
                status=status_enum,
                report_type=type_enum
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid filter value: {e}")
        except Exception as e:
            logger.error(f"Error listing reports: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/reports/{report_id}")
    async def get_report(self, report_id: str) -> ReportDetail:
        """Get details of a specific report."""
        try:
            service = await self._get_reports_service()
            report = await service.get_report(report_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            return report
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/reports")
    async def create_report(self, request: CreateReportRequest) -> ReportDetail:
        """Create a new report."""
        try:
            service = await self._get_reports_service()
            report = await service.create_report(request)
            if not report:
                raise HTTPException(status_code=500, detail="Failed to create report")
            return report
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating report: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.patch("/api/reports/{report_id}")
    async def update_report(
        self,
        report_id: str,
        request: UpdateReportRequest
    ) -> ReportDetail:
        """Update a report."""
        try:
            service = await self._get_reports_service()
            report = await service.update_report(report_id, request)
            if not report:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            return report
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating report {report_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/reports/{report_id}")
    async def delete_report(self, report_id: str) -> dict:
        """Delete a report."""
        try:
            service = await self._get_reports_service()
            deleted = await service.delete_report(report_id)
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            return {"status": "deleted", "report_id": report_id}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/reports/{report_id}/generate")
    async def generate_report(self, report_id: str) -> dict:
        """Start generating a report."""
        try:
            service = await self._get_reports_service()
            started = await service.generate_report(report_id)
            if not started:
                raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
            return {"status": "generating", "report_id": report_id}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating report {report_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # ============== Assessments Endpoints ==============

    @app.get("/api/assessments")
    async def list_assessments(
        self,
        limit: int = 50,
        status: Optional[str] = None,
        assessment_type: Optional[str] = None
    ) -> list[AssessmentSummary]:
        """List assessments with optional filters."""
        try:
            service = await self._get_assessments_service()

            # Convert string params to enums if provided
            status_enum = AssessmentStatus(status) if status else None
            type_enum = AssessmentType(assessment_type) if assessment_type else None

            return await service.list_assessments(
                limit=limit,
                status=status_enum,
                assessment_type=type_enum
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid filter value: {e}")
        except Exception as e:
            logger.error(f"Error listing assessments: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/assessments/{assessment_id}")
    async def get_assessment(self, assessment_id: str) -> AssessmentDetail:
        """Get details of a specific assessment."""
        try:
            service = await self._get_assessments_service()
            assessment = await service.get_assessment(assessment_id)
            if not assessment:
                raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
            return assessment
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting assessment {assessment_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/assessments")
    async def create_assessment(self, request: CreateAssessmentRequest) -> AssessmentDetail:
        """Create a new assessment."""
        try:
            service = await self._get_assessments_service()
            assessment = await service.create_assessment(request)
            if not assessment:
                raise HTTPException(status_code=500, detail="Failed to create assessment")
            return assessment
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating assessment: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.patch("/api/assessments/{assessment_id}")
    async def update_assessment(
        self,
        assessment_id: str,
        request: UpdateAssessmentRequest
    ) -> AssessmentDetail:
        """Update an assessment."""
        try:
            service = await self._get_assessments_service()
            assessment = await service.update_assessment(assessment_id, request)
            if not assessment:
                raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
            return assessment
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating assessment {assessment_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/assessments/{assessment_id}")
    async def delete_assessment(self, assessment_id: str) -> dict:
        """Delete an assessment."""
        try:
            service = await self._get_assessments_service()
            deleted = await service.delete_assessment(assessment_id)
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
            return {"status": "deleted", "assessment_id": assessment_id}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting assessment {assessment_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/assessments/{assessment_id}/run")
    async def run_assessment(self, assessment_id: str) -> dict:
        """Start running an assessment."""
        try:
            service = await self._get_assessments_service()
            started = await service.run_assessment(assessment_id)
            if not started:
                raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
            return {"status": "running", "assessment_id": assessment_id}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error running assessment {assessment_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/assessments/{assessment_id}/chat")
    async def assessment_chat(self, assessment_id: str, request: ChatMessageRequest) -> dict:
        """Send a follow-up chat message for an assessment."""
        try:
            service = await self._get_assessments_service()
            result = await service.process_chat_followup(assessment_id, request)
            if not result:
                raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing chat for assessment {assessment_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    def _deep_sanitize(self, obj):
        """Recursively sanitize any object to remove Neo4j types."""
        if hasattr(obj, "isoformat"):
            # Neo4j DateTime or Python datetime
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._deep_sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._deep_sanitize(item) for item in obj]
        else:
            return obj

    async def _execute_cypher_query_with_params(
        self, cypher: str, driver, params: dict | None = None
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Execute a Cypher query with parameters and convert results to graph format."""
        nodes_dict = {}
        links = []
        params = params or {}

        try:
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run(cypher, params)
                records = await result.data()

                for record in records:
                    for key, value in record.items():
                        # Handle nodes (dictionaries with 'labels' key and uuid)
                        if isinstance(value, dict) and "labels" in value and "uuid" in value:
                            node_id = str(value.get("uuid"))
                            if node_id not in nodes_dict:
                                # Get node properties (exclude metadata keys) and convert Neo4j types
                                node_props = {}
                                for k, v in value.items():
                                    if k not in ["labels", "uuid", "name_embedding"]:
                                        # Convert Neo4j DateTime to ISO string
                                        if hasattr(v, "isoformat"):
                                            node_props[k] = v.isoformat()
                                        else:
                                            node_props[k] = v

                                labels = value.get("labels", [])
                                nodes_dict[node_id] = GraphNode(
                                    id=node_id,
                                    name=node_props.get(
                                        "name",
                                        node_props.get(
                                            "politician_name",
                                            node_props.get("company_name", f"Node-{node_id[:8]}"),
                                        ),
                                    ),
                                    type=labels[0] if labels else "Entity",
                                    properties=node_props,
                                )

                        # Handle relationships (tuples containing (start_node, rel_type_string, end_node))
                        elif isinstance(value, tuple) and len(value) == 3:
                            start_node, rel_type, end_node = value

                            # Extract node information from tuple
                            if isinstance(start_node, dict) and "uuid" in start_node:
                                source_id = str(start_node.get("uuid"))
                                # Add start node if not already present
                                if source_id not in nodes_dict:
                                    labels = start_node.get("labels", [])
                                    node_props = {}
                                    for k, v in start_node.items():
                                        if k not in ["labels", "uuid", "name_embedding"]:
                                            # Convert Neo4j DateTime to ISO string
                                            if hasattr(v, "isoformat"):
                                                node_props[k] = v.isoformat()
                                            else:
                                                node_props[k] = v
                                    nodes_dict[source_id] = GraphNode(
                                        id=source_id,
                                        name=node_props.get(
                                            "name",
                                            node_props.get(
                                                "politician_name",
                                                node_props.get(
                                                    "company_name", f"Node-{source_id[:8]}"
                                                ),
                                            ),
                                        ),
                                        type=labels[0] if labels else "Entity",
                                        properties=node_props,
                                    )

                            if isinstance(end_node, dict) and "uuid" in end_node:
                                target_id = str(end_node.get("uuid"))
                                # Add end node if not already present
                                if target_id not in nodes_dict:
                                    labels = end_node.get("labels", [])
                                    node_props = {}
                                    for k, v in end_node.items():
                                        if k not in ["labels", "uuid", "name_embedding"]:
                                            # Convert Neo4j DateTime to ISO string
                                            if hasattr(v, "isoformat"):
                                                node_props[k] = v.isoformat()
                                            else:
                                                node_props[k] = v
                                    nodes_dict[target_id] = GraphNode(
                                        id=target_id,
                                        name=node_props.get(
                                            "name",
                                            node_props.get(
                                                "politician_name",
                                                node_props.get(
                                                    "company_name", f"Node-{target_id[:8]}"
                                                ),
                                            ),
                                        ),
                                        type=labels[0] if labels else "Entity",
                                        properties=node_props,
                                    )

                            # Extract relationship type (it's a string in the tuple)
                            if isinstance(rel_type, str) and source_id and target_id:
                                links.append(
                                    GraphEdge(
                                        source=source_id,
                                        target=target_id,
                                        type=rel_type,
                                        properties={},  # No properties available from tuple format
                                    )
                                )

        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            raise

        nodes = list(nodes_dict.values())
        return nodes, links


# Create the Ray Serve deployment
graph_viz_app = GraphVizServer.bind()


# Deployment function for standalone usage
async def deploy_graph_viz_server():
    """Deploy the graph visualization server standalone (for testing)."""
    import ray

    if not ray.is_initialized():
        ray.init()

    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 8001})
    serve.run(GraphVizServer.bind(), name="graph-viz-server", route_prefix="/graph-viz")

    logger.info("Graph visualization server deployed at http://0.0.0.0:8001/graph-viz/")


if __name__ == "__main__":
    import asyncio

    asyncio.run(deploy_graph_viz_server())
