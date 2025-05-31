# Ray Deployment v0.2.0 Patterns

## Ray Serve Architecture

### Service Configuration
```yaml
# config.yaml - Ray Serve deployment
services:
  chat-server:
    import_path: src.chat.server.app:app
    route_prefix: /v1
    num_replicas: 1
    ray_actor_options:
      num_cpus: 1
      memory: 2000000000
    
  flow1-data-ingestion:
    import_path: src.flows.data_ingestion.app:app
    route_prefix: /data-ingestion
    num_replicas: 1
    ray_actor_options:
      num_cpus: 2
      memory: 4000000000
```

### Deployment Commands
```bash
# Start Ray cluster
ray start --head

# Deploy all services
uv run --active serve deploy config.yaml

# Check deployment status
uv run --active serve status

# Monitor Ray dashboard
open http://localhost:8265
```

## Chat Server Deployment

### FastAPI + Ray Serve Integration
```python
# src/chat/server/app.py
from ray import serve
from fastapi import FastAPI
from src.chat.agent.orchestrator import MultiAgentOrchestrator

app = FastAPI(title="Political Monitoring Chat API")

@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_cpus": 1, "memory": 2000000000}
)
@serve.ingress(app)
class ChatServer:
    def __init__(self):
        self.orchestrator = MultiAgentOrchestrator()
    
    @app.post("/v1/chat/completions")
    async def chat_completions(self, request: ChatCompletionRequest):
        if request.stream:
            return StreamingResponse(
                self.orchestrator.process_query_streaming(request),
                media_type="text/plain"
            )
        else:
            return await self.orchestrator.process_query(request)

# Deployment binding
chat_server = ChatServer.bind()
```

### Health Check Integration
```python
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    try:
        # Check critical dependencies
        orchestrator_status = await self.orchestrator.health_check()
        graph_status = await self.check_knowledge_graph()
        
        return {
            "status": "healthy",
            "orchestrator": orchestrator_status,
            "knowledge_graph": graph_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

## Kodosumi Flow Deployment

### Flow Server Pattern
```python
# src/flows/data_ingestion/app.py
from kodosumi import ServeAPI
from ray import serve

app = ServeAPI()

@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_cpus": 2, "memory": 4000000000}
)
@serve.ingress(app)
class DataIngestionFlow:
    def __init__(self):
        # Initialize flow dependencies
        self.document_processor = DocumentProcessor()
        self.knowledge_graph_client = GraphitiClient()
    
    # Kodosumi routes are automatically handled by ServeAPI

# Deployment binding
data_ingestion_flow = DataIngestionFlow.bind()
```

### Ray Task Integration in Flows
```python
# src/flows/data_ingestion/document_processor.py
import ray

@ray.remote
class BatchDocumentProcessor:
    def __init__(self):
        self.graphiti_client = GraphitiClient()
    
    async def process_batch(self, documents: List[str]) -> Dict:
        results = []
        for doc_path in documents:
            result = await self.process_single_document(doc_path)
            results.append(result)
        
        return {
            'processed': len(results),
            'successful': len([r for r in results if r['success']]),
            'errors': [r['error'] for r in results if not r['success']]
        }

# Usage in flow entrypoint
async def process_documents(inputs: dict, tracer: Tracer):
    # Create remote Ray actor
    processor = BatchDocumentProcessor.remote()
    
    # Process documents in batches
    batch_size = 5
    document_batches = [
        inputs.documents[i:i + batch_size] 
        for i in range(0, len(inputs.documents), batch_size)
    ]
    
    # Execute batches in parallel
    batch_tasks = [
        processor.process_batch.remote(batch) 
        for batch in document_batches
    ]
    
    # Monitor progress
    while batch_tasks:
        ready, batch_tasks = ray.wait(batch_tasks, num_returns=1, timeout=10)
        
        for completed_task in ready:
            result = await completed_task
            await tracer.markdown(f"✅ Batch completed: {result['processed']} documents")
    
    return core.response.Markdown("All document processing complete!")
```

## Resource Management

### CPU and Memory Allocation
```python
# Optimal resource allocation for different workloads

# Chat Server - Low latency, moderate memory
chat_server_options = {
    "num_cpus": 1,           # Single CPU for fast response
    "memory": 2000000000,    # 2GB for LLM inference + tool execution
}

# Data Ingestion Flow - High CPU, high memory
data_ingestion_options = {
    "num_cpus": 2,           # Parallel document processing
    "memory": 4000000000,    # 4GB for large document batches
    "max_concurrency": 4,    # Limit concurrent requests
}

# ETL Tasks - Variable based on collection size
etl_task_options = {
    "num_cpus": 1,           # I/O bound operations
    "memory": 1000000000,    # 1GB for data collection
    "max_retries": 3,        # Retry failed collections
}
```

### Autoscaling Configuration
```yaml
# config.yaml - Autoscaling settings
services:
  chat-server:
    autoscaling_config:
      min_replicas: 1
      max_replicas: 3
      target_num_ongoing_requests_per_replica: 2
      
  flow1-data-ingestion:
    autoscaling_config:
      min_replicas: 1
      max_replicas: 2
      target_num_ongoing_requests_per_replica: 1
```

## Service Discovery and Routing

### Internal Service Communication
```python
# Get deployed service handle
@serve.deployment
class ChatServer:
    def __init__(self):
        # Get handle to data ingestion flow
        self.data_ingestion = serve.get_deployment("flow1-data-ingestion").get_handle()
    
    async def trigger_document_processing(self, documents):
        # Call other Ray Serve deployment
        result = await self.data_ingestion.process_documents.remote(documents)
        return result
```

### Route Configuration
```python
# Multiple route prefixes for different services
routes = {
    "/v1/chat/completions": "chat-server",
    "/v1/models": "chat-server", 
    "/data-ingestion": "flow1-data-ingestion",
    "/health": "chat-server"  # Global health check
}
```

## Monitoring and Observability

### Ray Dashboard Integration
```python
# Custom metrics for Ray dashboard
import ray
from ray.util.metrics import Counter, Histogram

# Define custom metrics
chat_requests = Counter(
    "chat_requests_total",
    description="Total number of chat requests",
    tag_keys=("model", "stream")
)

processing_time = Histogram(
    "document_processing_seconds",
    description="Time spent processing documents",
    boundaries=[1, 5, 10, 30, 60, 300]
)

# Use in deployment
@serve.deployment
class ChatServer:
    async def process_request(self, request):
        # Increment counter
        chat_requests.inc(tags={"model": request.model, "stream": str(request.stream)})
        
        # Time processing
        start_time = time.time()
        try:
            result = await self.orchestrator.process_query(request)
            return result
        finally:
            processing_time.observe(time.time() - start_time)
```

### Service Health Monitoring
```python
# Comprehensive health checks
async def check_service_health():
    health_status = {}
    
    # Check Ray cluster
    try:
        cluster_resources = ray.cluster_resources()
        health_status["ray_cluster"] = {
            "status": "healthy",
            "available_cpus": cluster_resources.get("CPU", 0),
            "available_memory": cluster_resources.get("memory", 0)
        }
    except Exception as e:
        health_status["ray_cluster"] = {"status": "unhealthy", "error": str(e)}
    
    # Check deployed services
    try:
        serve_status = serve.status()
        health_status["serve_applications"] = {
            "status": "healthy" if serve_status.app_status.status == "RUNNING" else "unhealthy",
            "deployments": len(serve_status.deployment_statuses)
        }
    except Exception as e:
        health_status["serve_applications"] = {"status": "unhealthy", "error": str(e)}
    
    return health_status
```

## Development and Testing

### Local Development Setup
```python
# Local Ray development pattern
import ray

# Start Ray locally for development
if not ray.is_initialized():
    ray.init(
        runtime_env={
            "working_dir": ".",
            "pip": ["requirements from pyproject.toml"]
        }
    )

# Deploy for development
serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 8001})
serve.deploy(config="config.yaml")
```

### Testing Deployed Services
```python
# Test deployed services
async def test_deployed_chat_service():
    # Test via HTTP
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8001/v1/chat/completions",
            json={
                "model": "political-monitoring-agent",
                "messages": [{"role": "user", "content": "Test query"}],
                "stream": False
            }
        ) as response:
            assert response.status == 200
            result = await response.json()
            assert "choices" in result

async def test_deployed_data_ingestion():
    # Test Kodosumi flow via handle
    deployment = serve.get_deployment("flow1-data-ingestion")
    handle = deployment.get_handle()
    
    # Test health check
    health = await handle.health_check.remote()
    assert health["status"] == "healthy"
```

## Production Deployment

### Production Configuration
```yaml
# config.yaml - Production settings
runtime_env:
  working_dir: "."
  pip: "requirements.txt"
  env_vars:
    RAY_DEDUP_LOGS: "0"
    RAY_SERVE_REQUEST_PROCESSING_TIMEOUT_S: "300"

services:
  chat-server:
    num_replicas: 2  # High availability
    max_concurrent_queries: 10
    ray_actor_options:
      num_cpus: 2
      memory: 4000000000
      
  flow1-data-ingestion:
    num_replicas: 1
    max_concurrent_queries: 2  # Limit resource usage
    ray_actor_options:
      num_cpus: 4
      memory: 8000000000
```

### Deployment Scripts
```bash
#!/bin/bash
# deploy.sh - Production deployment script

set -e

echo "Starting Ray cluster..."
ray start --head --port=6379 --dashboard-host=0.0.0.0

echo "Waiting for Ray to be ready..."
sleep 10

echo "Deploying services..."
uv run --active serve deploy config.yaml

echo "Verifying deployment..."
uv run --active serve status

echo "Deployment complete. Services available at:"
echo "  Chat API: http://localhost:8001/v1/chat/completions"
echo "  Data Ingestion: http://localhost:8001/data-ingestion"
echo "  Ray Dashboard: http://localhost:8265"
```

### Rolling Updates
```bash
# Rolling update strategy
# 1. Deploy new version alongside old
serve deploy config-new.yaml --name new-version

# 2. Test new version
curl http://localhost:8001/health

# 3. Switch traffic gradually
# (Ray Serve handles this automatically with new deployment)

# 4. Remove old version
serve delete old-version
```

## Error Handling and Recovery

### Deployment Failure Recovery
```python
async def ensure_deployment_health():
    """Monitor and recover from deployment failures."""
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Check deployment status
            status = serve.status()
            
            unhealthy_deployments = [
                name for name, deployment_status in status.deployment_statuses.items()
                if deployment_status.status != "HEALTHY"
            ]
            
            if unhealthy_deployments:
                logger.warning(f"Unhealthy deployments detected: {unhealthy_deployments}")
                
                # Attempt to redeploy unhealthy services
                await redeploy_services(unhealthy_deployments)
                
            else:
                logger.info("All deployments healthy")
                break
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            retry_count += 1
            
            if retry_count < max_retries:
                await asyncio.sleep(30)  # Wait before retry
            else:
                raise
```

### Resource Exhaustion Handling
```python
@serve.deployment(
    ray_actor_options={"num_cpus": 2, "memory": 4000000000},
    max_concurrent_queries=5,  # Prevent overload
)
class DataIngestionFlow:
    async def process_request(self, request):
        # Check available resources before processing
        cluster_resources = ray.cluster_resources()
        available_memory = cluster_resources.get("memory", 0)
        
        if available_memory < 2000000000:  # 2GB minimum
            raise HTTPException(
                status_code=503,
                detail="Insufficient resources available. Please try again later."
            )
        
        return await self.process_documents(request)
```

## Common Anti-Patterns

❌ **Blocking operations in Ray Serve**:
```python
# DON'T: Use blocking calls in Ray Serve deployments
def process_request(self, request):
    result = time.sleep(30)  # Blocks entire replica
```

❌ **Excessive resource allocation**:
```python
# DON'T: Over-allocate resources
ray_actor_options = {
    "num_cpus": 16,  # Too many CPUs for single request
    "memory": 32000000000  # 32GB for simple operations
}
```

❌ **No error handling**:
```python
# DON'T: Ignore deployment failures
serve.deploy(config)  # No error handling
```

✅ **Correct patterns**:
```python
# DO: Use async operations
async def process_request(self, request):
    result = await async_operation()

# DO: Right-size resources
ray_actor_options = {
    "num_cpus": 2,      # Match workload requirements
    "memory": 4000000000  # Adequate for processing
}

# DO: Handle deployment errors
try:
    serve.deploy(config)
    logger.info("Deployment successful")
except Exception as e:
    logger.error(f"Deployment failed: {e}")
    # Implement retry or rollback logic
```