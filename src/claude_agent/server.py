"""FastAPI server with Ray Serve deployment for Claude PolicyTracker Agent.

This server provides an OpenAI-compatible chat completions API that includes
session_id in responses for graph visualization integration.

Features:
- OpenAI-compatible chat completions API
- Session management endpoints for multi-turn context
- Streaming support
- Graph visualization integration
"""

import logging
import time
import uuid
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ray import serve

from src.config import settings
from src.shared.context_manager import sdk_context_manager

# Use SDK-based agent for automatic agentic loop and native MCP support
from .agent_sdk import PolicyTrackerSDKAgent as PolicyTrackerAgent

# Configure logging
log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


# Request/Response Models (OpenAI-compatible with session_id extension)
class Message(BaseModel):
    """Chat message."""

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request with session_id support."""

    model: str = "claude-policytracker"
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for graph visualization. Generated if not provided."
    )


class ChatCompletionChoice(BaseModel):
    """Chat completion choice."""

    index: int
    message: Message
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response with session_id and metadata."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    session_id: str = Field(
        description="Session ID for graph visualization. Use with /api/graph/chat-context endpoint."
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional metadata including reflection confidence scores"
    )


class SessionMetadata(BaseModel):
    """Session metadata response."""

    session_id: str
    message_count: int
    entity_count: int
    tool_calls: int
    is_continuation: bool
    created_at: Optional[str] = None


class SessionMessagesResponse(BaseModel):
    """Session messages response."""

    status: str
    session_id: str
    messages: list[dict[str, Any]]
    total: int


class StreamChoice(BaseModel):
    """Streaming choice."""

    index: int
    delta: dict
    finish_reason: str | None = None


class StreamResponse(BaseModel):
    """Streaming response chunk."""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[StreamChoice]
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID included in final chunk"
    )


# FastAPI app
fastapi_app = FastAPI(
    title="Claude PolicyTracker Agent API",
    description="""Claude-based agent for political monitoring knowledge graph queries.

## Features
- OpenAI-compatible chat completions API
- Session tracking for graph visualization
- Streaming support

## Graph Visualization
Use the returned `session_id` with the `/api/graph/chat-context` endpoint
to visualize entities and relationships referenced in the conversation.
""",
    version="1.0.0",
)

# CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@serve.deployment(num_replicas=1)
@serve.ingress(fastapi_app)
class ClaudeAgentServer:
    """Ray Serve deployment for Claude PolicyTracker Agent."""

    def __init__(self):
        self._agent: PolicyTrackerAgent | None = None
        logger.info("ClaudeAgentServer initialized")

    async def _get_agent(self) -> PolicyTrackerAgent:
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = PolicyTrackerAgent()
            logger.info("PolicyTracker Agent initialized")
        return self._agent

    @fastapi_app.get("/health")
    async def health_check(self) -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "claude-policytracker-agent",
            "model": "claude-sonnet-4-20250514",
            "features": ["session_tracking", "graph_visualization"],
        }

    @fastapi_app.get("/v1/models")
    async def list_models(self) -> dict:
        """List available models (OpenAI-compatible)."""
        return {
            "object": "list",
            "data": [
                {
                    "id": "claude-policytracker",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "policytracker",
                    "description": "Claude-based policy tracking agent with knowledge graph access",
                }
            ],
        }

    @fastapi_app.post("/v1/chat/completions")
    async def chat_completions(self, request: ChatCompletionRequest):
        """OpenAI-compatible chat completions endpoint.

        Supports both streaming and non-streaming responses.
        Returns session_id for graph visualization integration.
        """
        # Extract the user message (last user message in the conversation)
        user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            user_message = "Hello"

        logger.info(f"Chat request: stream={request.stream}, message='{user_message[:50]}...'")

        if request.stream:
            return StreamingResponse(
                self._stream_response(request.model, user_message, request.session_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            return await self._non_streaming_response(
                request.model, user_message, request.session_id
            )

    async def _non_streaming_response(
        self,
        model: str,
        user_message: str,
        session_id: Optional[str] = None
    ) -> ChatCompletionResponse:
        """Handle non-streaming chat completion."""
        try:
            agent = await self._get_agent()
            # query() now returns (response_text, session_id, metadata)
            response_text, final_session_id, metadata = await agent.query(user_message, session_id)

            # Append session info footer for graph visualization
            graph_viz_url = f"http://localhost:5174/chat-context?session={final_session_id}&mode=3d"
            confidence = metadata.get("avg_confidence", 1.0)
            confidence_indicator = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"
            session_footer = f"\n\n---\n📊 **Session ID**: `{final_session_id}` {confidence_indicator}\n🔗 [View Graph Context]({graph_viz_url})"

            return ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                created=int(time.time()),
                model=model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=Message(role="assistant", content=response_text + session_footer),
                        finish_reason="stop",
                    )
                ],
                session_id=final_session_id,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            # Generate a session ID even for errors
            error_session_id = session_id or f"error_{uuid.uuid4().hex[:16]}"
            return ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                created=int(time.time()),
                model=model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=Message(
                            role="assistant",
                            content=f"Error processing request: {str(e)}"
                        ),
                        finish_reason="stop",
                    )
                ],
                session_id=error_session_id,
                metadata={"error": str(e)},
            )

    async def _stream_response(
        self,
        model: str,
        user_message: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Handle streaming chat completion."""
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created = int(time.time())
        final_session_id = None
        final_metadata: dict[str, Any] = {}

        try:
            agent = await self._get_agent()

            # stream_query() now returns (chunk, session_id, metadata)
            async for chunk, chunk_session_id, metadata in agent.stream_query(user_message, session_id):
                if chunk_session_id:
                    # Final chunk with session ID and metadata
                    final_session_id = chunk_session_id
                    final_metadata = metadata

                if chunk:
                    response = StreamResponse(
                        id=chat_id,
                        created=created,
                        model=model,
                        choices=[
                            StreamChoice(
                                index=0,
                                delta={"content": chunk},
                                finish_reason=None,
                            )
                        ],
                        session_id=None,  # Only include in final chunk
                    )
                    yield f"data: {response.model_dump_json()}\n\n"

            # Send session footer before final chunk
            graph_viz_url = f"http://localhost:5174/chat-context?session={final_session_id}&mode=3d"
            confidence = final_metadata.get("avg_confidence", 1.0)
            confidence_indicator = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"
            session_footer = f"\n\n---\n📊 **Session ID**: `{final_session_id}` {confidence_indicator}\n🔗 [View Graph Context]({graph_viz_url})"

            footer_response = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": session_footer},
                        finish_reason=None,
                    )
                ],
                session_id=None,
            )
            yield f"data: {footer_response.model_dump_json()}\n\n"

            # Send final chunk with session_id
            final_response = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={},
                        finish_reason="stop",
                    )
                ],
                session_id=final_session_id,
            )
            yield f"data: {final_response.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            error_response = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": f"\n\nError: {str(e)}"},
                        finish_reason="stop",
                    )
                ],
                session_id=session_id or f"error_{uuid.uuid4().hex[:16]}",
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

    @fastapi_app.get("/v1/sessions/{session_id}")
    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get session metadata and context summary.

        Returns:
            Session metadata including message count, entities tracked, etc.
        """
        try:
            metadata = sdk_context_manager.get_session_metadata(session_id)
            return {
                "status": "success",
                "session": metadata,
            }
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @fastapi_app.get("/v1/sessions/{session_id}/messages")
    async def get_session_messages(
        self, session_id: str, limit: int = 20
    ) -> SessionMessagesResponse:
        """Get conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return (default 20)

        Returns:
            Session messages with total count
        """
        try:
            context = await sdk_context_manager.get_session_context(session_id)
            messages = context.get("messages", [])[-limit:]
            return SessionMessagesResponse(
                status="success",
                session_id=session_id,
                messages=messages,
                total=len(context.get("messages", [])),
            )
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @fastapi_app.delete("/v1/sessions/{session_id}")
    async def clear_session(self, session_id: str) -> dict[str, str]:
        """Clear session context (for starting fresh).

        Note: This only clears the in-memory cache, not Neo4j persistence.

        Args:
            session_id: Session identifier to clear

        Returns:
            Confirmation message
        """
        try:
            sdk_context_manager.clear_session(session_id)
            return {
                "status": "success",
                "message": f"Session {session_id} cleared from cache",
            }
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @fastapi_app.get("/v1/sessions")
    async def list_sessions(self, limit: int = 50) -> dict[str, Any]:
        """List all active sessions in the cache.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session IDs with basic metadata
        """
        try:
            # Get sessions from the context manager cache
            sessions = []
            for session_id in list(sdk_context_manager._cache.keys())[:limit]:
                metadata = sdk_context_manager.get_session_metadata(session_id)
                sessions.append(metadata)

            return {
                "status": "success",
                "sessions": sessions,
                "total": len(sdk_context_manager._cache),
            }
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# Ray Serve app binding
app = ClaudeAgentServer.bind()
