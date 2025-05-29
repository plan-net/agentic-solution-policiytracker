"""Minimal Ray Serve chat server."""

import ray
from ray import serve
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, AsyncGenerator
import logging
import os
import json
import time
import uuid
import asyncio
from graphiti_core import Graphiti
from src.config import settings
from ..agent.simple_agent import SimplePoliticalAgent

logger = logging.getLogger(__name__)

# Request/Response models for OpenAI compatibility
class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "political-monitoring-agent"
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 1000
    stream: bool = False  # Let Open WebUI control streaming

class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]

class StreamChoice(BaseModel):
    index: int
    delta: Dict[str, Any]
    finish_reason: str | None = None

class StreamResponse(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[StreamChoice]

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "political-monitoring"

class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]

# FastAPI app
app = FastAPI(title="Political Monitoring Chat API")

@serve.deployment(num_replicas=1)
@serve.ingress(app)
class ChatServer:
    """Minimal chat server for testing."""
    
    def __init__(self):
        self.graphiti_client = None
        self.agent = None
        logger.info("ChatServer initialized")
    
    async def _get_graphiti_client(self):
        """Lazy initialization of Graphiti client."""
        if self.graphiti_client is None:
            self.graphiti_client = Graphiti(
                settings.NEO4J_URI,
                settings.NEO4J_USERNAME, 
                settings.NEO4J_PASSWORD
            )
            await self.graphiti_client.build_indices_and_constraints()
            logger.info("Graphiti client initialized")
        return self.graphiti_client
    
    async def _get_agent(self):
        """Lazy initialization of the LLM agent."""
        if self.agent is None:
            # Get Graphiti client first
            graphiti_client = await self._get_graphiti_client()
            
            # Get OpenAI API key
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            # Initialize agent
            self.agent = SimplePoliticalAgent(graphiti_client, openai_api_key)
            logger.info("LLM agent initialized")
            
        return self.agent
    
    
    @app.get("/health")
    async def health_check(self) -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "chat-server"}
    
    @app.get("/v1/models")
    async def list_models(self) -> ModelsResponse:
        """OpenAI-compatible models endpoint."""
        import time
        return ModelsResponse(
            data=[
                ModelInfo(
                    id="political-monitoring-agent",
                    created=int(time.time()),
                    owned_by="political-monitoring"
                )
            ]
        )
    
    @app.post("/v1/chat/completions")
    async def chat_completions(self, request: ChatCompletionRequest):
        """OpenAI-compatible chat completions endpoint with streaming support."""
        
        # Get the last user message
        user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        if not user_message:
            user_message = "Please provide a message."
        
        # Handle streaming vs non-streaming properly
        if request.stream:
            return StreamingResponse(
                self._stream_with_enhanced_agent(request.model, user_message),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache", 
                    "Connection": "keep-alive"
                }
            )
        else:
            return await self._non_streaming_response(request.model, user_message)
    
    async def _non_streaming_response(self, model: str, user_message: str) -> ChatCompletionResponse:
        """Handle non-streaming response (existing logic)."""
        try:
            # Use LLM agent for processing
            agent = await self._get_agent()
            response_content = await agent.process_query(user_message)
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            response_content = f"Sorry, I encountered an error: {str(e)}"
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
            created=int(time.time()),
            model=model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content=response_content),
                    finish_reason="stop"
                )
            ]
        )
    
    async def _stream_chat_response(self, model: str, user_message: str) -> AsyncGenerator[str, None]:
        """Stream chat response with thinking output."""
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created = int(time.time())
        
        try:
            # Get streaming agent for intelligent thinking
            agent = await self._get_streaming_agent()
            
            # Use streaming agent's capability
            async for chunk in agent.stream_query(user_message):
                # Format as OpenAI streaming chunk
                stream_chunk = StreamResponse(
                    id=chat_id,
                    created=created,
                    model=model,
                    choices=[
                        StreamChoice(
                            index=0,
                            delta={"content": chunk},
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {stream_chunk.model_dump_json()}\n\n"
            
            # Send final chunk
            final_chunk = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={},
                        finish_reason="stop"
                    )
                ]
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            # Send error as stream chunk
            error_chunk = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": f"Sorry, I encountered an error: {str(e)}"},
                        finish_reason="stop"
                    )
                ]
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
    
    async def _simple_test_stream(self, model: str, user_message: str) -> AsyncGenerator[str, None]:
        """Simple test stream to understand thinking format."""
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created = int(time.time())
        
        try:
            # Simulate thinking
            await asyncio.sleep(1)
            
            # Send thinking content
            thinking_chunk = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": "<think>\nAnalyzing your query...\nUsing graph analysis\n</think>\n\n"},
                        finish_reason=None
                    )
                ]
            )
            yield f"data: {thinking_chunk.model_dump_json()}\n\n"
            
            # Send response
            response_chunk = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": f"Response to: '{user_message}'"},
                        finish_reason=None
                    )
                ]
            )
            yield f"data: {response_chunk.model_dump_json()}\n\n"
            
            # Send final chunk
            final_chunk = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={},
                        finish_reason="stop"
                    )
                ]
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Simple test stream error: {e}")
            yield f"data: [DONE]\n\n"
    
    async def _stream_with_enhanced_agent(self, model: str, user_message: str) -> AsyncGenerator[str, None]:
        """Stream with the enhanced SimplePoliticalAgent real-time thinking."""
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created = int(time.time())
        
        try:
            # Get the enhanced agent
            agent = await self._get_agent()
            
            # Stream the agent's thinking and response
            async for thinking_chunk in agent.stream_query(user_message):
                # Wrap each chunk in OpenAI streaming format
                chunk = StreamResponse(
                    id=chat_id,
                    created=created,
                    model=model,
                    choices=[
                        StreamChoice(
                            index=0,
                            delta={"content": thinking_chunk},
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
            
            # Send final chunk
            final = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={},
                        finish_reason="stop"
                    )
                ]
            )
            yield f"data: {final.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Enhanced agent stream error: {e}")
            # Send error as final chunk
            error_chunk = StreamResponse(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta={"content": f"I encountered an error: {str(e)}"},
                        finish_reason="stop"
                    )
                ]
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

# Deployment function
def deploy_chat_server():
    """Deploy the chat server."""
    if not ray.is_initialized():
        ray.init()
    
    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 8001})
    serve.run(ChatServer.bind(), name="chat-server", route_prefix="/")
    
    logger.info("Chat server deployed at http://0.0.0.0:8001/")

if __name__ == "__main__":
    deploy_chat_server()