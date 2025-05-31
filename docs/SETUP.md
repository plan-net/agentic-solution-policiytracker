# Open WebUI Setup - Critical Configuration

## Key Learning: Model Detection

Open WebUI detects models through the OpenAI-compatible `/v1/models` endpoint. The critical configuration is:

### 1. Environment Variable Structure
```yaml
OPENAI_API_BASE_URL=http://host.docker.internal:8001/chat/v1
```

**IMPORTANT**: Open WebUI expects the base URL to include `/v1`. It will append `/models` to get the full endpoint:
- ✅ CORRECT: `OPENAI_API_BASE_URL=http://host.docker.internal:8001/chat/v1` 
  - Results in: `http://host.docker.internal:8001/chat/v1/models`
- ❌ WRONG: `OPENAI_API_BASE_URL=http://host.docker.internal:8001/chat`
  - Results in: `http://host.docker.internal:8001/chat/models` (404 error)

### 2. Ray Serve Route Configuration
```yaml
- name: chat-server
  route_prefix: /chat  # NOT "/" - root path can cause issues
  import_path: src.chat.server.app:chat_app
```

**IMPORTANT**: Never use `/` as the route_prefix for Ray Serve applications that need to be accessed by Open WebUI. Use a proper path like `/chat`.

### 3. Required Endpoints in app.py
The chat server must implement:
- `GET /v1/models` - Returns list of available models
- `POST /v1/chat/completions` - Handles chat requests

### 4. Docker Compose Configuration
```yaml
open-webui:
  environment:
    - OPENAI_API_BASE_URL=http://host.docker.internal:8001/chat/v1
    - OPENAI_API_KEY=dummy-key-not-required
    - DEFAULT_MODELS=political-monitoring-agent
    - WEBUI_AUTH=false
    - OLLAMA_BASE_URL=""  # Disable Ollama
```

### 5. Updating Configuration
When changing environment variables in docker-compose.yml:
- `docker compose restart` is NOT enough - it doesn't reload env vars
- Use `docker compose up -d open-webui` to recreate the container

## Troubleshooting

### Check if model detection is working:
```bash
# From host
curl http://localhost:8001/chat/v1/models

# From inside Open WebUI container  
docker exec policiytracker-open-webui curl http://host.docker.internal:8001/chat/v1/models
```

### Check Open WebUI logs for errors:
```bash
docker logs policiytracker-open-webui 2>&1 | grep -i "models"
```

Look for errors like:
- `Connection error: 404` - Wrong base URL
- `url='http://host.docker.internal:8001/models'` - Missing `/chat/v1` in base URL

## Summary
The model detection works when:
1. Chat server is deployed at a non-root path (e.g., `/chat`)
2. Open WebUI's `OPENAI_API_BASE_URL` includes the full path with `/v1`
3. The chat server implements the `/v1/models` endpoint
4. Container is recreated (not just restarted) after env var changes