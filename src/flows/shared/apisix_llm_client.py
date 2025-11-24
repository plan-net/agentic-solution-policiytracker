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

    # Create LLMConfig with APISIX base URL
    config = LLMConfig(api_key=api_key, model=model, base_url=base_url, temperature=temperature)

    # Create OpenAIClient (concrete implementation of LLMClient)
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
