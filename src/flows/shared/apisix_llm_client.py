"""
Agent-aware LLM client for routing through APISIX with cost tracking.

This module provides wrappers for LangChain and OpenAI clients that automatically
inject agent context headers for APISIX gateway routing and TimescaleDB cost tracking.

NOTE: Graphiti Integration Limitation
-------------------------------------
Graphiti's LLMConfig supports base_url but does NOT support custom default_headers.
This means Graphiti LLM calls will route through APISIX but WITHOUT agent tracking headers.

Workaround: We're documenting this for Week 2 implementation of custom Graphiti LLMClient.
"""

import os
from typing import Optional

from anthropic import AsyncAnthropic
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI, OpenAI


class AgentContext:
    """Context for agent-level cost tracking through APISIX."""

    def __init__(
        self,
        agent_type: str,
        agent_name: str,
        flow_name: Optional[str] = None,
        chat_agent_name: Optional[str] = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        project_id: str = "political_monitoring_v2",
    ):
        """
        Initialize agent context for cost tracking.

        Args:
            agent_type: Type of agent - 'kodosumi_flow', 'chat_agent', 'etl_processor'
            agent_name: Specific agent identifier
            flow_name: Name of Kodosumi flow (for kodosumi_flow type)
            chat_agent_name: Name of chat agent (for chat_agent type)
            session_id: Session/conversation identifier
            trace_id: Distributed tracing identifier
            project_id: Project identifier for grouping
        """
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.flow_name = flow_name
        self.chat_agent_name = chat_agent_name
        self.session_id = session_id
        self.trace_id = trace_id
        self.project_id = project_id

    def to_headers(self) -> dict[str, str]:
        """Convert context to HTTP headers for APISIX."""
        headers = {
            "X-Agent-Type": self.agent_type,
            "X-Agent-Name": self.agent_name,
            "X-Project-ID": self.project_id,
        }

        if self.flow_name:
            headers["X-Flow-Name"] = self.flow_name

        if self.chat_agent_name:
            headers["X-Chat-Agent-Name"] = self.chat_agent_name

        if self.session_id:
            headers["X-Session-ID"] = self.session_id

        if self.trace_id:
            headers["X-Trace-ID"] = self.trace_id

        return headers


def create_agent_aware_langchain_llm(
    agent_context: AgentContext,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,
    streaming: bool = True,
    **kwargs,
) -> ChatOpenAI:
    """
    Create a LangChain ChatOpenAI client that routes through APISIX with agent tracking.

    Args:
        agent_context: Agent context for cost tracking
        model: OpenAI model name
        temperature: LLM temperature
        streaming: Enable streaming responses
        **kwargs: Additional ChatOpenAI arguments

    Returns:
        ChatOpenAI instance configured to use APISIX gateway

    Example:
        >>> context = AgentContext(
        ...     agent_type="chat_agent",
        ...     agent_name="query_understanding",
        ...     chat_agent_name="query_understanding",
        ...     session_id="session_abc123"
        ... )
        >>> llm = create_agent_aware_langchain_llm(context)
        >>> response = await llm.ainvoke("What is GDPR?")
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # APISIX gateway URL
    base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")

    # Get agent context headers
    default_headers = agent_context.to_headers()

    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=temperature,
        streaming=streaming,
        base_url=base_url,
        default_headers=default_headers,
        **kwargs,
    )


def create_agent_aware_openai_client(
    agent_context: AgentContext,
    async_client: bool = True,
    **kwargs,
) -> AsyncOpenAI | OpenAI:
    """
    Create an OpenAI client that routes through APISIX with agent tracking.

    Args:
        agent_context: Agent context for cost tracking
        async_client: If True, return AsyncOpenAI, else OpenAI
        **kwargs: Additional OpenAI client arguments

    Returns:
        AsyncOpenAI or OpenAI instance configured to use APISIX gateway

    Example:
        >>> context = AgentContext(
        ...     agent_type="kodosumi_flow",
        ...     agent_name="data_ingestion_processor",
        ...     flow_name="data_ingestion",
        ...     session_id="flow_xyz789"
        ... )
        >>> client = create_agent_aware_openai_client(context)
        >>> response = await client.chat.completions.create(
        ...     model="gpt-4o-mini",
        ...     messages=[{"role": "user", "content": "Analyze this document"}]
        ... )
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # APISIX gateway URL
    base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")

    # Get agent context headers
    default_headers = agent_context.to_headers()

    if async_client:
        return AsyncOpenAI(
            api_key=api_key, base_url=base_url, default_headers=default_headers, **kwargs
        )
    else:
        return OpenAI(api_key=api_key, base_url=base_url, default_headers=default_headers, **kwargs)


def create_graphiti_compatible_client(
    agent_context: AgentContext,
    **kwargs,
) -> AsyncOpenAI:
    """
    Create an AsyncOpenAI client compatible with Graphiti that routes through APISIX.

    Graphiti internally uses AsyncOpenAI for LLM operations. This function creates
    a client that can be passed to Graphiti to enable cost tracking.

    Args:
        agent_context: Agent context for cost tracking
        **kwargs: Additional AsyncOpenAI arguments

    Returns:
        AsyncOpenAI instance configured for Graphiti

    Example:
        >>> context = AgentContext(
        ...     agent_type="kodosumi_flow",
        ...     agent_name="graphiti_document_processor",
        ...     flow_name="data_ingestion"
        ... )
        >>> openai_client = create_graphiti_compatible_client(context)
        >>> graphiti = Graphiti(
        ...     neo4j_uri, neo4j_user, neo4j_password,
        ...     llm_client=openai_client  # Custom client with APISIX routing
        ... )
    """
    return create_agent_aware_openai_client(agent_context, async_client=True, **kwargs)


# Convenience functions for common agent types


def create_chat_agent_llm(
    agent_name: str,
    session_id: str,
    model: str = "gpt-4o-mini",
    **kwargs,
) -> ChatOpenAI:
    """
    Create LangChain LLM for chat agents.

    Args:
        agent_name: Chat agent name (e.g., "query_understanding", "tool_planning")
        session_id: Conversation session ID
        model: OpenAI model name
        **kwargs: Additional ChatOpenAI arguments

    Returns:
        ChatOpenAI instance with chat agent context
    """
    context = AgentContext(
        agent_type="chat_agent",
        agent_name=agent_name,
        chat_agent_name=agent_name,
        session_id=session_id,
    )
    return create_agent_aware_langchain_llm(context, model=model, **kwargs)


def create_kodosumi_flow_llm(
    flow_name: str,
    agent_name: str,
    session_id: Optional[str] = None,
    model: str = "gpt-4o-mini",
    **kwargs,
) -> ChatOpenAI:
    """
    Create LangChain LLM for Kodosumi flows.

    Args:
        flow_name: Flow name (e.g., "data_ingestion", "context_analysis")
        agent_name: Specific agent within flow
        session_id: Flow execution session ID
        model: OpenAI model name
        **kwargs: Additional ChatOpenAI arguments

    Returns:
        ChatOpenAI instance with Kodosumi flow context
    """
    context = AgentContext(
        agent_type="kodosumi_flow",
        agent_name=agent_name,
        flow_name=flow_name,
        session_id=session_id,
    )
    return create_agent_aware_langchain_llm(context, model=model, **kwargs)


def create_etl_processor_llm(
    processor_name: str,
    model: str = "gpt-4o-mini",
    **kwargs,
) -> ChatOpenAI:
    """
    Create LangChain LLM for ETL processors.

    Args:
        processor_name: ETL processor name
        model: OpenAI model name
        **kwargs: Additional ChatOpenAI arguments

    Returns:
        ChatOpenAI instance with ETL processor context
    """
    context = AgentContext(
        agent_type="etl_processor",
        agent_name=processor_name,
    )
    return create_agent_aware_langchain_llm(context, model=model, **kwargs)


def create_graphiti_apisix_config(
    agent_context: AgentContext,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1,
    max_tokens: int = 16000,  # Increased from default 8192 to handle large entity extractions
):
    """
    Create Graphiti-compatible LLM configuration that routes through APISIX.

    NOTE: This function creates a configuration that routes through APISIX but
    WITHOUT agent tracking headers due to Graphiti's LLMConfig limitations.
    Week 2 implementation will create a custom LLMClient with header support.

    Args:
        agent_context: Agent context (for documentation, not used in Week 1)
        model: OpenAI model name
        temperature: LLM temperature

    Returns:
        Tuple of (LLMClient, note about limitation)

    Example:
        >>> from graphiti_core.llm_client.client import LLMClient
        >>> from graphiti_core.llm_client.config import LLMConfig
        >>> from graphiti_core import Graphiti
        >>>
        >>> context = AgentContext(
        ...     agent_type="kodosumi_flow",
        ...     agent_name="graphiti_processor",
        ...     flow_name="data_ingestion"
        ... )
        >>> llm_client, note = create_graphiti_apisix_config(context)
        >>> graphiti = Graphiti(
        ...     neo4j_uri, neo4j_user, neo4j_password,
        ...     llm_client=llm_client
        ... )
    """
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_client import OpenAIClient

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # APISIX gateway URL
    base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")

    # Create LLMConfig with APISIX base URL and increased max_tokens for entity extraction
    config = LLMConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,  # Increased to handle large entity extraction responses
    )

    # Create OpenAIClient — use cache-optimized variant if enabled
    from src.config import graphrag_settings
    if graphrag_settings.ENABLE_PROMPT_CACHE_OPTIMIZATION:
        from src.graphrag.cached_openai_client import CacheFriendlyOpenAIClient
        llm_client = CacheFriendlyOpenAIClient(config=config, cache=False)
    else:
        llm_client = OpenAIClient(config=config, cache=False)

    note = f"""
    ⚠️  WEEK 1 LIMITATION: Graphiti routing through APISIX without agent headers

    Agent Context (not yet tracked):
    - Type: {agent_context.agent_type}
    - Name: {agent_context.agent_name}
    - Flow: {agent_context.flow_name or 'N/A'}

    This will be addressed in Week 2 with custom Graphiti LLMClient implementation.
    """

    return llm_client, note


def create_apisix_openai_embeddings(
    model: str = "text-embedding-3-small",
    dimensions: int = 1536,
    **kwargs,
):
    """
    Create OpenAIEmbeddings routed through APISIX for cost tracking.

    This function creates a LangChain OpenAIEmbeddings client that routes
    all embedding requests through APISIX gateway, enabling cost tracking
    in TimescaleDB/Grafana.

    Args:
        model: OpenAI embedding model name (default: text-embedding-3-small)
        dimensions: Embedding dimensions (default: 1536)
        **kwargs: Additional OpenAIEmbeddings arguments

    Returns:
        OpenAIEmbeddings instance configured to use APISIX gateway

    Example:
        >>> embeddings = create_apisix_openai_embeddings()
        >>> vector = embeddings.embed_query("Hello world")
    """
    from langchain_openai import OpenAIEmbeddings

    base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")

    return OpenAIEmbeddings(
        model=model,
        dimensions=dimensions,
        openai_api_base=base_url,
        **kwargs,
    )


def create_apisix_graphiti_embedder(
    embedding_model: str = "text-embedding-ada-002",
):
    """
    Create Graphiti OpenAIEmbedder routed through APISIX for cost tracking.

    This function creates a Graphiti-compatible embedder that routes all
    embedding requests through APISIX gateway, enabling cost tracking in
    TimescaleDB/Grafana.

    Use this when initializing Graphiti to ensure embedding costs are tracked:

    Args:
        embedding_model: OpenAI embedding model name (default: text-embedding-ada-002)
                        Changed from text-embedding-3-small to ada-002 for better multilingual support.
                        Testing showed ada-002 achieves 100% cross-lingual similarity vs 13% for 3-small.

    Returns:
        OpenAIEmbedder instance configured to use APISIX gateway

    Example:
        >>> embedder = create_apisix_graphiti_embedder()
        >>> graphiti = Graphiti(
        ...     neo4j_uri, neo4j_user, neo4j_password,
        ...     llm_client=llm_client,
        ...     embedder=embedder,  # Route embeddings through APISIX
        ... )
    """
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")

    config = OpenAIEmbedderConfig(
        api_key=api_key,
        base_url=base_url,
        embedding_model=embedding_model,
        embedding_dim=1536,  # ada-002 also returns 1536 dimensions
    )

    return OpenAIEmbedder(config=config)


def create_apisix_anthropic_client(
    agent_context: Optional[AgentContext] = None,
    api_key: Optional[str] = None,
    use_apisix: Optional[bool] = None,
    **kwargs,
) -> AsyncAnthropic:
    """
    Create an AsyncAnthropic client, optionally routing through APISIX.

    This function creates an Anthropic client that can route through the APISIX
    gateway for cost tracking, or connect directly to Anthropic's API.

    Args:
        agent_context: Optional agent context for cost tracking headers
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        use_apisix: Whether to route through APISIX. Defaults to checking
                    USE_APISIX_FOR_ANTHROPIC env var, then False.
        **kwargs: Additional AsyncAnthropic arguments

    Returns:
        AsyncAnthropic instance

    Example:
        >>> context = AgentContext(
        ...     agent_type="kodosumi_flow",
        ...     agent_name="weekly_report_agent",
        ...     flow_name="weekly_report_sdk"
        ... )
        >>> client = create_apisix_anthropic_client(context)
        >>> response = await client.messages.create(
        ...     model="claude-sonnet-4-20250514",
        ...     max_tokens=8192,
        ...     messages=[{"role": "user", "content": "Generate a report"}]
        ... )
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Determine whether to use APISIX
    if use_apisix is None:
        use_apisix = os.getenv("USE_APISIX_FOR_ANTHROPIC", "false").lower() == "true"

    # Get agent context headers if provided
    default_headers = agent_context.to_headers() if agent_context else {}

    if use_apisix:
        # Route through APISIX gateway
        # NOTE: APISIX must have Anthropic route configured at /v1/messages
        base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080")
        return AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers,
            **kwargs,
        )
    else:
        # Connect directly to Anthropic API
        return AsyncAnthropic(
            api_key=api_key,
            default_headers=default_headers,
            **kwargs,
        )


def create_graphiti_anthropic_config(
    agent_context: AgentContext,
    model: str = "claude-sonnet-4-5-latest",
    temperature: float = 0.1,
    max_tokens: int = 16000,
):
    """
    Create Graphiti-compatible Anthropic client with optional APISIX routing.

    This function creates an AnthropicClient from graphiti_core that can route
    through the APISIX gateway for cost tracking.

    Note: Graphiti's AnthropicClient does NOT pass base_url from LLMConfig to
    AsyncAnthropic. To enable APISIX routing, we create our own AsyncAnthropic
    client with base_url and pass it via the client parameter.

    Args:
        agent_context: Agent context for cost tracking headers
        model: Anthropic model name (default: claude-sonnet-4-5-latest)
        temperature: LLM temperature (default: 0.1 for deterministic extraction)
        max_tokens: Maximum tokens for response (default: 16000 for entity extraction)

    Returns:
        Tuple of (AnthropicClient, info_message)

    Example:
        >>> context = AgentContext(
        ...     agent_type="kodosumi_flow",
        ...     agent_name="graphiti_document_processor",
        ...     flow_name="data_ingestion"
        ... )
        >>> llm_client, note = create_graphiti_anthropic_config(context)
        >>> graphiti = Graphiti(
        ...     neo4j_uri, neo4j_user, neo4j_password,
        ...     llm_client=llm_client
        ... )
    """
    from graphiti_core.llm_client.anthropic_client import AnthropicClient
    from graphiti_core.llm_client.config import LLMConfig

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Check if APISIX routing is enabled
    use_apisix = os.getenv("USE_APISIX_FOR_ANTHROPIC", "false").lower() == "true"

    # Create LLMConfig for Graphiti
    config = LLMConfig(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Create AsyncAnthropic client with APISIX routing if enabled
    if use_apisix:
        base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080")
        default_headers = agent_context.to_headers() if agent_context else {}
        anthropic_client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers,
            max_retries=1,
        )
    else:
        anthropic_client = AsyncAnthropic(
            api_key=api_key,
            max_retries=1,
        )

    # Create Graphiti AnthropicClient — use cache-optimized variant if enabled
    from src.config import graphrag_settings
    if graphrag_settings.ENABLE_PROMPT_CACHE_OPTIMIZATION:
        from src.graphrag.cached_anthropic_client import CachedAnthropicClient
        llm_client = CachedAnthropicClient(config=config, cache=False, client=anthropic_client)
    else:
        llm_client = AnthropicClient(config=config, cache=False, client=anthropic_client)

    note = f"Using Anthropic ({model}) via {'APISIX' if use_apisix else 'direct API'}"
    return llm_client, note


def create_graphiti_llm_client(
    agent_context: AgentContext,
    temperature: float = 0.1,
    max_tokens: int = 16000,
):
    """
    Create Graphiti LLM client based on GRAPHITI_LLM_PROVIDER environment variable.

    This factory function selects the appropriate LLM client (OpenAI or Anthropic)
    based on the GRAPHITI_LLM_PROVIDER configuration setting.

    Args:
        agent_context: Agent context for cost tracking headers
        temperature: LLM temperature (default: 0.1 for deterministic extraction)
        max_tokens: Maximum tokens for response (default: 16000 for entity extraction)

    Returns:
        Tuple of (LLMClient, info_message)

    Example:
        >>> context = AgentContext(
        ...     agent_type="kodosumi_flow",
        ...     agent_name="graphiti_document_processor",
        ...     flow_name="data_ingestion"
        ... )
        >>> llm_client, note = create_graphiti_llm_client(context)
        >>> graphiti = Graphiti(
        ...     neo4j_uri, neo4j_user, neo4j_password,
        ...     llm_client=llm_client
        ... )
    """
    from src.config import graphrag_settings

    provider = graphrag_settings.GRAPHITI_LLM_PROVIDER.lower()

    if provider == "anthropic":
        model = graphrag_settings.GRAPHITI_ANTHROPIC_MODEL
        return create_graphiti_anthropic_config(
            agent_context, model=model, temperature=temperature, max_tokens=max_tokens
        )
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return create_graphiti_apisix_config(
            agent_context, model=model, temperature=temperature, max_tokens=max_tokens
        )
    else:
        raise ValueError(
            f"Unknown GRAPHITI_LLM_PROVIDER: {provider}. Use 'openai' or 'anthropic'"
        )
