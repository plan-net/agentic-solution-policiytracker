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
    
    @app.get("/debug/test-stream")
    async def debug_test_stream(self, query: str = "What is GDPR?"):
        """Debug endpoint to test streaming without OpenAI compatibility layer."""
        logger.info(f"Debug test stream with query: {query}")
        
        try:
            streaming_orchestrator = await self._get_streaming_orchestrator()
            session_id = f"debug_{uuid.uuid4().hex[:8]}"
            
            chunks = []
            async for chunk in streaming_orchestrator.process_query_with_streaming(
                query=query,
                session_id=session_id,
                user_id="debug_user"
            ):
                chunk_info = {
                    "chunk_number": len(chunks) + 1,
                    "type": chunk.get("type"),
                    "timestamp": chunk.get("timestamp"),
                    "data_type": type(chunk.get("data")).__name__ if "data" in chunk else "N/A",
                    "data_keys": list(chunk.get("data", {}).keys()) if isinstance(chunk.get("data"), dict) else "N/A",
                    "data_preview": str(chunk.get("data", ""))[:200] + "..." if chunk.get("data") else "None"
                }
                chunks.append(chunk_info)
                logger.info(f"Debug chunk {len(chunks)}: {chunk_info}")
            
            return {
                "status": "completed", 
                "query": query,
                "session_id": session_id,
                "total_chunks": len(chunks),
                "chunks": chunks
            }
            
        except Exception as e:
            logger.error(f"Debug stream error: {e}")
            return {"status": "error", "error": str(e)}
    
    @app.post("/debug/simple-stream")
    async def debug_simple_stream(self, query: str = "What is GDPR?"):
        """Ultra-simple streaming test that bypasses multi-agent system."""
        return StreamingResponse(
            self._simple_test_stream("debug-model", query),
            media_type="text/event-stream"
        )
    
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
        
        logger.info(f"Chat request: stream={request.stream}, message='{user_message[:50]}...'")
        
        # Handle streaming vs non-streaming properly
        if request.stream:
            logger.info("Using streaming response")
            return StreamingResponse(
                self._stream_chat_response(request.model, user_message),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache", 
                    "Connection": "keep-alive"
                }
            )
        else:
            logger.info("Using non-streaming response")
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
        """Stream chat response with proper single thinking block and reasoning."""
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created = int(time.time())
        
        try:
            logger.info(f"Starting streaming response for message: {user_message[:50]}...")
            
            # Get streaming orchestrator
            streaming_orchestrator = await self._get_streaming_orchestrator()
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            # Create initial state
            initial_state = {
                "original_query": user_message,
                "processed_query": "",
                "query_analysis": None,
                "tool_plan": None,
                "tool_results": [],
                "final_response": "",
                "current_agent": "query_understanding",
                "agent_sequence": [],
                "execution_metadata": {},
                "session_id": session_id,
                "conversation_history": [],
                "user_preferences": {},
                "learned_patterns": {},
                "is_streaming": True,
                "thinking_updates": [],
                "progress_indicators": [],
                "errors": [],
                "warnings": [],
                "messages": []
            }
            
            # Start single thinking block
            yield self._create_chunk(chat_id, created, model, f"<think>\nAnalyzing query: '{user_message}'\n\n")
            
            # Stream using LangGraph's native streaming
            thread_config = {"configurable": {"thread_id": session_id}}
            
            async for chunk in streaming_orchestrator.graph.astream(initial_state, config=thread_config, stream_mode=["updates", "custom"]):
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk
                    
                    if mode == "updates":
                        # Convert LangGraph updates to reasoning
                        reasoning = await self._convert_update_to_reasoning(data)
                        if reasoning:
                            yield self._create_chunk(chat_id, created, model, reasoning)
                    
                    elif mode == "custom":
                        # Direct reasoning output from agents
                        yield self._create_chunk(chat_id, created, model, data.get("reasoning", ""))
                
                else:
                    # Handle single mode output
                    reasoning = await self._convert_update_to_reasoning(chunk)
                    if reasoning:
                        yield self._create_chunk(chat_id, created, model, reasoning)
            
            # Get final state and close thinking
            final_state = await streaming_orchestrator.graph.aget_state(thread_config)
            final_response = final_state.values.get("final_response", "")
            
            # Close thinking and provide response
            yield self._create_chunk(chat_id, created, model, "\nAnalysis complete.\n</think>\n\n")
            
            if final_response:
                yield self._create_chunk(chat_id, created, model, final_response)
            else:
                errors = final_state.values.get("errors", [])
                if errors:
                    error_msg = "; ".join(errors)
                    yield self._create_chunk(chat_id, created, model, f"I encountered an issue: {error_msg}")
                else:
                    yield self._create_chunk(chat_id, created, model, "I was unable to generate a response for your query.")
            
            logger.info(f"Streaming complete for session: {session_id}")
            
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
    
    def _create_chunk(self, chat_id: str, created: int, model: str, content: str) -> str:
        """Create a streaming chunk in OpenAI format."""
        chunk = StreamResponse(
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
        return f"data: {chunk.model_dump_json()}\n\n"
    
    async def _convert_update_to_reasoning(self, data: Dict[str, Any]) -> str:
        """Convert LangGraph state updates to intelligent reasoning."""
        if not isinstance(data, dict):
            return ""
        
        reasoning_parts = []
        
        # Process each node update
        for node_name, node_state in data.items():
            if node_name == "query_understanding" and "query_analysis" in node_state:
                analysis = node_state["query_analysis"]
                reasoning_parts.append(
                    f"🔍 Understanding Query: Identified '{analysis.get('intent', 'unknown')}' intent "
                    f"with {analysis.get('confidence', 0):.0%} confidence. "
                    f"Primary focus: {analysis.get('primary_entity', 'general inquiry')}. "
                    f"Strategy: {analysis.get('analysis_strategy', 'exploratory')}.\n"
                )
            
            elif node_name == "tool_planning" and "tool_plan" in node_state:
                plan = node_state["tool_plan"]
                tools = plan.get("tool_sequence", [])
                reasoning_parts.append(
                    f"📋 Planning Execution: Designed {plan.get('strategy_type', 'unknown')} strategy "
                    f"with {len(tools)} tools. Estimated time: {plan.get('estimated_execution_time', 0):.1f}s. "
                    f"Tools: {', '.join(t.get('tool_name', 'unknown') for t in tools)}.\n"
                )
            
            elif node_name == "tool_execution" and "tool_results" in node_state:
                results = node_state["tool_results"]
                successful = sum(1 for r in results if r.get("success"))
                reasoning_parts.append(
                    f"⚡ Executing Tools: Completed {len(results)} tools ({successful} successful). "
                    f"Retrieved comprehensive information from knowledge graph.\n"
                )
            
            elif node_name == "response_synthesis" and "final_response" in node_state:
                response = node_state["final_response"]
                reasoning_parts.append(
                    f"✨ Synthesizing Response: Generated comprehensive response "
                    f"({len(response.split()) if response else 0} words). "
                    f"Integrating insights from multiple sources.\n"
                )
        
        return "".join(reasoning_parts)
    
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