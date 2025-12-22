"""FastAPI server with Ray Serve deployment for Claude PolicyTracker Agent.

This server provides an OpenAI-compatible chat completions API that includes
session_id in responses for graph visualization integration.
"""

import logging
import time
import uuid
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ray import serve

from src.config import settings

from .agent import PolicyTrackerAgent

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
    """OpenAI-compatible chat completion response with session_id."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    session_id: str = Field(
        description="Session ID for graph visualization. Use with /api/graph/chat-context endpoint."
    )


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
            response_text, final_session_id = await agent.query(user_message, session_id)

            # Append session info footer for graph visualization
            graph_viz_url = f"http://localhost:5174/chat-context?session={final_session_id}&mode=3d"
            session_footer = f"\n\n---\n📊 **Session ID**: `{final_session_id}`\n🔗 [View Graph Context]({graph_viz_url})"

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
            )

    async def _stream_response(
        self,
        model: str,
        user_message: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Handle streaming chat completion."""
        import json

        chat_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created = int(time.time())
        final_session_id = None

        try:
            agent = await self._get_agent()

            async for chunk, chunk_session_id in agent.stream_query(user_message, session_id):
                if chunk_session_id:
                    # Final chunk with session ID
                    final_session_id = chunk_session_id

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
            session_footer = f"\n\n---\n📊 **Session ID**: `{final_session_id}`\n🔗 [View Graph Context]({graph_viz_url})"

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


# Ray Serve app binding
app = ClaudeAgentServer.bind()
