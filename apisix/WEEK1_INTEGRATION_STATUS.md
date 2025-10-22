# Week 1 APISIX Integration Status

**Branch**: `policytracker_llmops_apigw`
**Date**: 2025-10-22

## ✅ Completed

### Infrastructure Setup
- [x] APISIX gateway, Dashboard, and etcd services in docker-compose.yml
- [x] APISIX configuration (config.yaml, apisix.yaml)
- [x] Routes for OpenAI and Anthropic providers
- [x] TimescaleDB schema for cost tracking
- [x] Cost Analytics API service
- [x] Justfile commands for APISIX management
- [x] Comprehensive documentation (README.md, JUSTFILE_COMMANDS.md)

### Agent Integration
- [x] Created `src/flows/shared/apisix_llm_client.py` - Agent-aware LLM client wrapper
- [x] Updated chat server to use APISIX routing (`src/chat/server/app.py`)
- [x] Updated Kodosumi flow document processor to use APISIX (`src/flows/data_ingestion/document_processor.py`)
- [x] Updated Graphiti clients to route through APISIX

## Week 1 Implementation Details

### Agent-Aware LLM Client

Created `src/flows/shared/apisix_llm_client.py` with the following components:

#### 1. AgentContext Class
Encapsulates agent metadata for cost tracking:
- `agent_type`: 'kodosumi_flow', 'chat_agent', 'etl_processor'
- `agent_name`: Specific agent identifier
- `flow_name`: Kodosumi flow name (optional)
- `chat_agent_name`: Chat agent name (optional)
- `session_id`: Session/conversation identifier
- `trace_id`: Distributed tracing ID
- `project_id`: Project grouping

#### 2. LangChain Integration
- `create_agent_aware_langchain_llm()`: Creates ChatOpenAI with agent headers
- `create_chat_agent_llm()`: Convenience function for chat agents
- `create_kodosumi_flow_llm()`: Convenience function for Kodosumi flows
- `create_etl_processor_llm()`: Convenience function for ETL processors

#### 3. OpenAI Client Integration
- `create_agent_aware_openai_client()`: Creates AsyncOpenAI/OpenAI with agent headers
- Supports both async and sync clients

#### 4. Graphiti Integration
- `create_graphiti_apisix_config()`: Creates Graphiti LLMClient routed through APISIX

## ⚠️ Week 1 Limitations

### Graphiti Agent Tracking
**Issue**: Graphiti's `LLMConfig` supports `base_url` but NOT `default_headers`.

**Current State**:
- ✅ Graphiti LLM calls route through APISIX gateway
- ❌ Agent tracking headers are NOT injected (cost tracking incomplete)
- ❌ Graphiti costs will appear in APISIX logs but WITHOUT agent attribution

**Week 2 Solution**:
Implement custom Graphiti `LLMClient` subclass that adds agent headers to all requests:

```python
class AgentAwareGraphitiLLMClient(LLMClient):
    """Custom Graphiti LLM client with agent header injection."""

    def __init__(self, config: LLMConfig, agent_context: AgentContext, cache: bool = False):
        super().__init__(config, cache)
        self.agent_context = agent_context
        self.agent_headers = agent_context.to_headers()

    async def _generate_response_with_retry(self, messages, **kwargs):
        # Inject agent headers into OpenAI client calls
        # Implementation in Week 2
        pass
```

## 📊 Integration Coverage

### Fully Integrated (with agent headers)
- ✅ Chat server LLM (`src/chat/server/app.py`)
  - Agent Type: `chat_agent`
  - Agent Name: `chat_orchestrator`
  - Headers: Full tracking enabled

### Partially Integrated (routing only, no headers)
- ⚠️ Graphiti in Kodosumi flows (`src/flows/data_ingestion/document_processor.py`)
  - Routes through APISIX ✅
  - Agent headers NOT injected ❌ (Week 2)

- ⚠️ Graphiti in chat server (`src/chat/server/app.py`)
  - Routes through APISIX ✅
  - Agent headers NOT injected ❌ (Week 2)

### Not Yet Integrated
- ⏳ ETL processors (Week 2)
- ⏳ Individual chat agents (query_understanding, tool_planning, etc.) - currently use shared LLM
- ⏳ Additional Kodosumi flows if added

## 🧪 Testing Status

### Manual Testing Required
1. Start APISIX services:
   ```bash
   just apisix-up
   ```

2. Test OpenAI routing:
   ```bash
   just apisix-test-openai
   ```

3. Check cost tracking:
   ```bash
   just apisix-costs-today
   ```

4. Test chat server:
   ```bash
   # Start all services
   just start

   # Test chat API
   curl -X POST http://localhost:8001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"political-monitoring-agent","messages":[{"role":"user","content":"What is GDPR?"}],"stream":false}'
   ```

5. Monitor APISIX logs:
   ```bash
   just apisix-logs
   ```

### Expected Behavior

#### Chat Server Requests
✅ Should see in TimescaleDB:
```sql
SELECT agent_type, agent_name, chat_agent_name, cost_usd
FROM llm_requests
WHERE agent_type = 'chat_agent'
ORDER BY timestamp DESC LIMIT 10;
```

Expected results:
- `agent_type`: `chat_agent`
- `agent_name`: `chat_orchestrator`
- `chat_agent_name`: `chat_orchestrator`
- Cost tracking: ✅ Working

#### Graphiti Requests (Week 1)
⚠️ Should see in TimescaleDB:
```sql
SELECT provider, model, cost_usd, agent_type, agent_name
FROM llm_requests
WHERE agent_type IS NULL
ORDER BY timestamp DESC LIMIT 10;
```

Expected results:
- Requests logged ✅
- `agent_type`: `NULL` (missing headers)
- `agent_name`: `NULL` (missing headers)
- Cost tracking: ⚠️ Incomplete (no agent attribution)

## 🔄 Migration Guide for Existing Code

### Before (Direct OpenAI)
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    temperature=0.1
)
```

### After (APISIX with agent tracking)
```python
from src.flows.shared.apisix_llm_client import create_chat_agent_llm

llm = create_chat_agent_llm(
    agent_name="my_agent",
    session_id="session_123",
    model="gpt-4o-mini"
)
```

### Graphiti Migration (Week 1)

Before:
```python
from graphiti_core import Graphiti

client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
```

After (Week 1 - partial integration):
```python
from graphiti_core import Graphiti
from src.flows.shared.apisix_llm_client import AgentContext, create_graphiti_apisix_config

context = AgentContext(
    agent_type="kodosumi_flow",
    agent_name="graphiti_processor",
    flow_name="data_ingestion"
)

llm_client, note = create_graphiti_apisix_config(context)
client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, llm_client=llm_client)

logger.warning(note)  # Logs Week 1 limitation
```

## 📝 Next Steps (Week 2)

### 1. Custom Graphiti LLMClient
- [ ] Implement `AgentAwareGraphitiLLMClient` subclass
- [ ] Add agent header injection to all Graphiti LLM calls
- [ ] Update document processor to use custom client
- [ ] Update chat server Graphiti to use custom client

### 2. Complete Cost Tracking
- [ ] Implement custom Lua cost-tracker plugin for APISIX
- [ ] Add request/response body logging for detailed analysis
- [ ] Implement budget alerts and monitoring

### 3. Analytics Dashboard
- [ ] Build comprehensive cost analytics dashboard
- [ ] Add agent leaderboard visualization
- [ ] Implement cost comparison charts

## 🐛 Known Issues

1. **Graphiti Agent Headers Missing**: Tracked for Week 2 implementation
2. **Session ID Management**: Chat server uses default session_id for LLM initialization; should use per-request session IDs (minor issue, doesn't affect cost tracking)

## 📚 Documentation

- **Main README**: `apisix/README.md` - Complete APISIX setup and usage
- **Quick Reference**: `apisix/JUSTFILE_COMMANDS.md` - All justfile commands
- **This Document**: `apisix/WEEK1_INTEGRATION_STATUS.md` - Integration status and limitations
- **Agent Client**: `src/flows/shared/apisix_llm_client.py` - Inline documentation with examples

## 🎯 Success Metrics

### Week 1 Goals
- [x] Infrastructure deployed and operational
- [x] LLM requests routed through APISIX gateway
- [x] Cost tracking database schema created
- [x] Chat agent cost tracking fully operational
- [x] Documentation complete

### Week 1 Partial Success
- [⚠️] Graphiti routing through APISIX (without agent headers)
- [⚠️] Agent-level cost granularity (chat only, not Graphiti yet)

### Week 2 Targets
- [ ] 100% agent-level cost attribution (including Graphiti)
- [ ] Custom cost tracking plugin operational
- [ ] Analytics dashboard deployed
- [ ] Budget monitoring active
