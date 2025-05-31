"""OpenAI-compatible Ray Serve chat server for multi-agent political monitoring."""

import ray
from ray import serve
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, AsyncGenerator, List
import logging
import os
import json
import time
import uuid
import asyncio
from graphiti_core import Graphiti
from langchain_openai import ChatOpenAI
from src.config import settings
from ..agent.orchestrator import MultiAgentOrchestrator, MultiAgentStreamingOrchestrator
from ..agent.tool_integration import ToolIntegrationManager

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
    """OpenAI-compatible chat server with multi-agent orchestration."""
    
    def __init__(self):
        self.graphiti_client = None
        self.tool_integration_manager = None
        self.orchestrator = None
        self.streaming_orchestrator = None
        self.llm = None
        logger.info("Multi-agent ChatServer initialized")
    
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
    
    async def _get_llm(self):
        """Lazy initialization of LLM."""
        if self.llm is None:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            self.llm = ChatOpenAI(
                api_key=openai_api_key,
                model="gpt-4o-mini",
                temperature=0.1,
                streaming=True
            )
            logger.info("LLM initialized")
        return self.llm
    
    async def _get_tool_integration_manager(self):
        """Lazy initialization of tool integration manager."""
        if self.tool_integration_manager is None:
            graphiti_client = await self._get_graphiti_client()
            self.tool_integration_manager = ToolIntegrationManager(graphiti_client)
            logger.info("Tool integration manager initialized")
        return self.tool_integration_manager
    
    async def _get_orchestrator(self):
        """Lazy initialization of multi-agent orchestrator."""
        if self.orchestrator is None:
            llm = await self._get_llm()
            tool_manager = await self._get_tool_integration_manager()
            
            # Create tools dictionary from tool integration manager
            tools = tool_manager.tools
            
            # Initialize orchestrator
            self.orchestrator = MultiAgentOrchestrator(llm=llm, tools=tools)
            
            # Set up tool integration manager
            self.orchestrator.tool_integration_manager = tool_manager
            self.orchestrator.planning_agent.set_tool_integration_manager(tool_manager)
            self.orchestrator.execution_agent.set_tool_integration_manager(tool_manager)
            
            logger.info("Multi-agent orchestrator initialized with knowledge graph tools")
        return self.orchestrator
    
    async def _get_streaming_orchestrator(self):
        """Lazy initialization of streaming orchestrator."""
        if self.streaming_orchestrator is None:
            llm = await self._get_llm()
            tool_manager = await self._get_tool_integration_manager()
            
            # Create tools dictionary from tool integration manager
            tools = tool_manager.tools
            
            # Initialize streaming orchestrator
            self.streaming_orchestrator = MultiAgentStreamingOrchestrator(llm=llm, tools=tools)
            
            # Set up tool integration manager
            self.streaming_orchestrator.tool_integration_manager = tool_manager
            self.streaming_orchestrator.planning_agent.set_tool_integration_manager(tool_manager)
            self.streaming_orchestrator.execution_agent.set_tool_integration_manager(tool_manager)
            
            logger.info("Streaming multi-agent orchestrator initialized")
        return self.streaming_orchestrator
    
    
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
                self._stream_chat_response(request.model, user_message),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache", 
                    "Connection": "keep-alive"
                }
            )
        else:
            return await self._non_streaming_response(request.model, user_message)
    
    async def _non_streaming_response(self, model: str, user_message: str) -> ChatCompletionResponse:
        """Handle non-streaming response using multi-agent orchestrator."""
        try:
            # Use multi-agent orchestrator for processing
            orchestrator = await self._get_orchestrator()
            
            # Generate unique session ID for this request
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            # Process query through multi-agent system
            result = await orchestrator.process_query(
                query=user_message,
                session_id=session_id,
                user_id="server_user"  # Could be extracted from auth headers
            )
            
            # Extract response content
            if result["success"]:
                response_content = result["response"]
                if not response_content:
                    response_content = "I've processed your query, but no specific response was generated. Please try rephrasing your question."
            else:
                error_messages = "; ".join(result.get("errors", ["Unknown error"]))
                response_content = f"I encountered an issue processing your query: {error_messages}"
            
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
        """Stream chat response using multi-agent streaming orchestrator."""
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created = int(time.time())
        
        try:
            # Get streaming orchestrator for multi-agent processing
            streaming_orchestrator = await self._get_streaming_orchestrator()
            
            # Generate unique session ID for this request
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            # Use streaming orchestrator's capability
            async for chunk in streaming_orchestrator.process_query_with_streaming(
                query=user_message,
                session_id=session_id,
                user_id="server_user"  # Could be extracted from auth headers
            ):
                # Extract content from streaming chunk
                content = ""
                if chunk.get("type") == "workflow_update":
                    # Format workflow updates as thinking output
                    content = f"<thinking>\n{chunk.get('data', {})}\n</thinking>\n"
                elif chunk.get("type") == "final_result":
                    # Extract final response content
                    result = chunk.get("data", {})
                    if result.get("success") and result.get("response"):
                        content = result["response"]
                    else:
                        error_messages = "; ".join(result.get("errors", ["Unknown error"]))
                        content = f"I encountered an issue: {error_messages}"
                elif chunk.get("type") == "error":
                    content = f"Error: {chunk.get('error', 'Unknown error')}"
                else:
                    # Handle other chunk types as thinking updates
                    content = f"<thinking>\n{str(chunk)}\n</thinking>\n"
                
                # Only send non-empty content
                if content:
                    stream_chunk = StreamResponse(
                        id=chat_id,
                        created=created,
                        model=model,
                        choices=[
                            StreamChoice(
                                index=0,
                                delta={"content": content},
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
        """Stream with the enhanced LangGraph agent real-time thinking."""
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

# Create the Ray Serve deployment for config.yaml
chat_app = ChatServer.bind()

# Deployment function for standalone usage
def deploy_chat_server():
    """Deploy the chat server standalone (for testing)."""
    if not ray.is_initialized():
        ray.init()
    
    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 8001})
    serve.run(ChatServer.bind(), name="chat-server", route_prefix="/")
    
    logger.info("Chat server deployed at http://0.0.0.0:8001/")

if __name__ == "__main__":
    deploy_chat_server()