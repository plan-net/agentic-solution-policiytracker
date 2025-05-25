# Langfuse Integration Guide

**Complete implementation guide and best practices for Langfuse integration with LangChain and Ray**

*Based on successful implementation in the Political Monitoring Agent*

## 📋 Table of Contents

- [Overview](#overview)
- [Key Learnings](#key-learnings)
- [Architecture Pattern](#architecture-pattern)
- [Implementation Steps](#implementation-steps)
- [Common Pitfalls](#common-pitfalls)
- [Troubleshooting](#troubleshooting)
- [Production Best Practices](#production-best-practices)

## Overview

This guide documents the complete Langfuse integration journey, including all the challenges faced and solutions discovered. The final implementation achieves:

✅ **Generation tracking** - Counters increment correctly  
✅ **Cost tracking** - Full token and cost monitoring  
✅ **Session tracking** - Grouped traces with session IDs  
✅ **Dynamic configuration** - Temperature and model settings from Langfuse  
✅ **Production labels** - Using production-labeled prompts  
✅ **Ray compatibility** - Working in distributed environments  

## Key Learnings

### ❌ What DOESN'T Work

1. **Custom Langfuse wrappers** - Over-engineering that breaks integration
2. **Version-based prompt retrieval** - Use labels instead
3. **Manual trace creation** - Breaks context propagation in Ray
4. **Global CallbackHandler** - Conflicts with @observe decorators
5. **Chain metadata approach** - Complex and error-prone
6. **Prompt metadata in config** - Doesn't link generations properly

### ✅ What WORKS

1. **Official Langfuse client** - Direct usage without wrappers
2. **Production labels** - `langfuse.get_prompt(name="...", label="production")`
3. **@observe decorators** - Proper context management
4. **Context-based handlers** - `langfuse_context.get_current_langchain_handler()`
5. **Nested generation pattern** - `@observe(as_type="generation")`
6. **Direct prompt linking** - `langfuse_context.update_current_observation(prompt=prompt)`

## Architecture Pattern

### Proven Stack
```
- Langfuse: Official Python SDK
- LangChain: 0.2.16 with Callback integration
- Ray: Distributed processing with context propagation
- Environment: Variables for authentication
```

### File Structure
```
src/
├── llm/
│   ├── langchain_service.py     # Main LLM service with @observe
│   └── models.py                # Pydantic models
├── prompts/
│   ├── *.md                     # Prompt files with frontmatter
│   └── prompt_manager.py        # Langfuse-first prompt management
├── integrations/
│   └── azure_storage.py         # Storage integration
└── config.py                   # Settings with Langfuse config
```

## Implementation Steps

### 1. Environment Setup

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-your-actual-public-key-from-ui
LANGFUSE_SECRET_KEY=sk-lf-your-actual-secret-key-from-ui
LANGFUSE_HOST=http://localhost:3001
```

### 2. Langfuse Client Initialization

```python
# src/llm/langchain_service.py
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from langfuse.callback import CallbackHandler

# Initialize global Langfuse client and callback handler
try:
    # Initialize Langfuse client (prompt management)
    langfuse = Langfuse()
    
    # Initialize Langfuse CallbackHandler for Langchain (tracing)
    langfuse_callback_handler = CallbackHandler()
    
    # Verify that Langfuse is configured correctly
    assert langfuse.auth_check()
    assert langfuse_callback_handler.auth_check()
    
    logger.info("Langfuse client and CallbackHandler initialized and authenticated successfully")
except Exception as e:
    langfuse = None
    langfuse_callback_handler = None
    logger.warning(f"Failed to initialize Langfuse: {e}")
```

### 3. Prompt Management Pattern

```python
# src/prompts/prompt_manager.py
class PromptManager:
    async def get_prompt_with_config(self, name: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Langfuse-first prompt retrieval with local fallback."""
        try:
            # Try Langfuse first with production label
            if self._langfuse:
                prompt = self._langfuse.get_prompt(name=name, label="production")
                return {
                    "prompt": self._substitute_variables(prompt.prompt, variables or {}),
                    "config": getattr(prompt, 'config', {}) or {}
                }
        except Exception as e:
            logger.warning(f"Langfuse prompt retrieval failed: {e}")
        
        # Fall back to local file
        prompt_text = await self._get_from_local_file(name)
        return {
            "prompt": self._substitute_variables(prompt_text, variables or {}),
            "config": {}
        }
```

### 4. LLM Service Pattern

```python
class LangChainLLMService:
    @observe()  # Main trace
    async def analyze_document(self, text: str, context: Dict[str, Any], session_id: Optional[str] = None):
        # Update trace with session info
        langfuse_context.update_current_trace(
            name="Document Analysis Session",
            session_id=session_id,
            tags=["document-analysis"],
            metadata={"provider": self.current_provider.value}
        )

        @observe(as_type="generation")  # Generation tracking
        async def execute_analysis(llm: BaseChatModel):
            # Get Langfuse prompt object for generation tracking
            try:
                if langfuse:
                    langfuse_prompt = langfuse.get_prompt(name="document_analysis", label="production")
                    # THIS IS THE KEY: Link prompt to generation
                    langfuse_context.update_current_observation(prompt=langfuse_prompt)
                    logger.info("Updated observation with Langfuse prompt")
            except Exception as e:
                logger.warning(f"Could not get Langfuse prompt: {e}")

            # Load prompt and config
            prompt_data = await prompt_manager.get_prompt_with_config("document_analysis", variables={...})
            
            # Configure LLM with Langfuse settings
            if prompt_data["config"].get("temperature"):
                configured_llm = llm.bind(temperature=prompt_data["config"]["temperature"])
            
            # Get context-based handler (preserves cost tracking)
            langfuse_handler = langfuse_context.get_current_langchain_handler()
            
            # Execute LLM call
            result = await configured_llm.ainvoke(
                [HumanMessage(content=prompt_data["prompt"])], 
                config={"callbacks": [langfuse_handler]} if langfuse_handler else {}
            )
            
            return result

        return await self._execute_with_fallback("document_analysis", execute_analysis, mock_response)
```

### 5. Prompt Upload Script

```python
# scripts/upload_prompts_to_langfuse.py
def upload_prompts_to_langfuse():
    langfuse = Langfuse()
    
    for prompt_file in prompt_files:
        # Parse frontmatter
        frontmatter = yaml.safe_load(parts[1])
        prompt_name = frontmatter.get('name')
        prompt_content = parts[2].strip()
        
        # Include model configuration
        config = {
            "model": settings.ANTHROPIC_MODEL if settings.ANTHROPIC_API_KEY else settings.OPENAI_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }
        
        # Upload with production label (NOT version)
        langfuse.create_prompt(
            name=prompt_name,
            prompt=prompt_content,
            config=config,
            labels=["production"],  # Use labels, not versions
            tags=["political-monitoring", "uploaded-from-file"]
        )
```

## Common Pitfalls

### ❌ Pitfall 1: Using Custom Wrappers
```python
# DON'T DO THIS
class LangfuseClient:
    def __init__(self):
        self._client = Langfuse()  # Unnecessary wrapper
```

**Solution**: Use official Langfuse client directly.

### ❌ Pitfall 2: Manual Trace Creation
```python
# DON'T DO THIS - Breaks context in Ray
trace = langfuse.trace(name="...")
callback_handler = trace.get_langchain_handler()
```

**Solution**: Use `@observe` decorators with context-based handlers.

### ❌ Pitfall 3: Version-Based Retrieval
```python
# DON'T DO THIS
prompt = langfuse.get_prompt(name="...", version=1)
```

**Solution**: Use production labels: `langfuse.get_prompt(name="...", label="production")`

### ❌ Pitfall 4: Global CallbackHandler
```python
# DON'T DO THIS - Conflicts with @observe
config = {"callbacks": [langfuse_callback_handler]}
```

**Solution**: Use context-based handler: `langfuse_context.get_current_langchain_handler()`

### ❌ Pitfall 5: Metadata-Based Generation Tracking
```python
# DON'T DO THIS - Doesn't link generations
config = {"metadata": {"prompt_name": "...", "prompt_version": "..."}}
```

**Solution**: Use direct prompt linking: `langfuse_context.update_current_observation(prompt=prompt)`

## Troubleshooting

### Generation Counters Not Incrementing

**Symptoms**: Traces appear but generation counters stay at 0

**Root Cause**: Missing `@observe(as_type="generation")` or prompt linking

**Solution**:
```python
@observe(as_type="generation")
async def llm_function():
    langfuse_prompt = langfuse.get_prompt(name="...", label="production")
    langfuse_context.update_current_observation(prompt=langfuse_prompt)
    # ... LLM call
```

### Cost Tracking Missing

**Symptoms**: Generations tracked but no cost/token data

**Root Cause**: Not using context-based callback handler

**Solution**:
```python
langfuse_handler = langfuse_context.get_current_langchain_handler()
config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}
```

### Ray Context Issues

**Symptoms**: Traces break in distributed Ray workers

**Root Cause**: Manual trace creation doesn't propagate context

**Solution**: Always use `@observe` decorators, never manual trace creation.

### Environment Variable Issues

**Symptoms**: "Langfuse not configured" errors

**Solution**:
1. Set environment variables correctly
2. Use `assert langfuse.auth_check()` to verify
3. Check Langfuse UI for correct API keys

## Production Best Practices

### 1. Environment Management
- Always use environment variables for credentials
- Test authentication with `auth_check()`
- Use production labels, not version numbers

### 2. Error Handling
- Always have local file fallbacks for prompts
- Graceful degradation when Langfuse unavailable
- Log all fallback occurrences

### 3. Performance
- Cache prompts in memory when possible
- Use production labels to avoid version lookups
- Batch operations where possible

### 4. Development Workflow
```bash
# 1. Update local prompts
just upload-prompts    # Upload to Langfuse with production labels

# 2. Test integration
just dev-quick         # Deploy and test

# 3. Verify in Langfuse UI
# Check generation counters, cost tracking, and traces
```

### 5. Monitoring
- Monitor fallback counts (should be low in production)
- Track generation/cost metrics in Langfuse
- Alert on authentication failures

## Success Metrics

A properly integrated Langfuse implementation should show:

✅ **Generation counters incrementing** - Each LLM call counted  
✅ **Cost tracking active** - Token usage and costs recorded  
✅ **Session grouping** - Related calls grouped by session ID  
✅ **Prompt linkage** - Generations linked to specific prompts  
✅ **Configuration application** - Temperature/model settings from Langfuse  
✅ **Error resilience** - Graceful fallbacks when Langfuse unavailable  

## Conclusion

The key to successful Langfuse integration is following the official patterns exactly:

1. **Use `@observe` decorators** for proper context management
2. **Link prompts directly** with `update_current_observation(prompt=prompt)`
3. **Use production labels** instead of version numbers
4. **Get context-based handlers** for cost tracking
5. **Always have fallbacks** for reliability

This pattern works reliably in production environments with Ray, LangChain, and complex async workflows.