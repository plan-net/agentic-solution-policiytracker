"""Minimal Ray Serve chat server."""

import ray
from ray import serve
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import logging
from graphiti_core import Graphiti
from src.config import settings

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
                # Simple search logic
                if "search" in user_message.lower():
                    query = user_message.replace("search", "").strip()
                    if query:
                        results = await client.search(query)
                        if results:
                            num_shown = min(len(results), 3)
                            response_content = f"Found {len(results)} facts related to '{query}' (showing top {num_shown}):\n\n"
                            # Show first few results with better formatting
                            for i, fact in enumerate(results[:3]):
                                response_content += f"{i+1}. {fact.fact}\n"
                                if hasattr(fact, 'name') and fact.name:
                                    response_content += f"   Relationship: {fact.name}\n"
                                response_content += "\n"
                            
                            # Add note if there are more results
                            if len(results) > 3:
                                response_content += f"... and {len(results) - 3} more facts. Ask me to 'search {query} more' for additional results."
                        else:
                            response_content = f"No results found for '{query}'"
                    else:
                        response_content = "Please specify what to search for"
                else:
                    response_content = "I can help you explore political data. Try asking me to 'search for EU AI Act' or 'search Digital Services Act'"
            
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