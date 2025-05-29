"""Minimal Ray Serve chat server."""

import ray
from ray import serve
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import logging
import os
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
    stream: bool = False

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
    async def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """OpenAI-compatible chat completions endpoint."""
        import time
        import uuid
        
        try:
            client = await self._get_graphiti_client()
            
            # Get the last user message
            user_message = None
            for msg in reversed(request.messages):
                if msg.role == "user":
                    user_message = msg.content
                    break
            
            if not user_message:
                response_content = "Please provide a message."
            else:
                # Use LLM agent for processing
                agent = await self._get_agent()
                response_content = await agent.process_query(user_message)
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            response_content = f"Sorry, I encountered an error: {str(e)}"
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content=response_content),
                    finish_reason="stop"
                )
            ]
        )

# Deployment function
def deploy_chat_server():
    """Deploy the chat server."""
    if not ray.is_initialized():
        ray.init()
    
    serve.start(detached=True)
    serve.run(ChatServer.bind(), name="chat-server", route_prefix="/")
    
    logger.info("Chat server deployed at /")

if __name__ == "__main__":
    deploy_chat_server()