"""Test LangWatch integration to verify traces are being sent."""

import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_langwatch_basic():
    """Test basic LangWatch setup."""

    # Check environment
    print("=" * 60)
    print("Environment Configuration:")
    print(f"ENABLE_LANGWATCH: {os.getenv('ENABLE_LANGWATCH')}")
    print(f"LANGWATCH_API_KEY: {os.getenv('LANGWATCH_API_KEY', 'Not set')[:20]}...")
    print(f"LANGWATCH_ENDPOINT: {os.getenv('LANGWATCH_ENDPOINT')}")
    print("=" * 60)

    # Initialize LangWatch
    from src.chat.observability.langwatch_config import langwatch_config

    initialized = langwatch_config.initialize()
    print(f"\nLangWatch initialization: {'SUCCESS' if initialized else 'FAILED'}")

    if not initialized:
        print("❌ LangWatch not initialized. Check your configuration.")
        return

    # Test with OpenAI client
    try:
        from langchain_openai import ChatOpenAI

        print("\n" + "=" * 60)
        print("Testing LLM call with instrumentation...")
        print("=" * 60)

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
        )

        response = await llm.ainvoke("Say hello in one word")
        print(f"\nLLM Response: {response.content}")

        # Give time for trace to be sent
        await asyncio.sleep(2)

        print("\n✅ LLM call completed. Check LangWatch UI for traces at:")
        print("   http://localhost:5560")

    except Exception as e:
        print(f"\n❌ Error during LLM call: {e}")
        import traceback

        traceback.print_exc()


async def test_langwatch_trace_decorator():
    """Test the trace decorator directly."""
    from src.chat.observability.langwatch_config import langwatch_config

    langwatch_config.initialize()

    @langwatch_config.trace(name="test_function", metadata={"test": True})
    async def traced_function(query: str):
        """A function that should be traced."""
        return f"Processed: {query}"

    print("\n" + "=" * 60)
    print("Testing trace decorator...")
    print("=" * 60)

    result = await traced_function("test query")
    print(f"Result: {result}")

    await asyncio.sleep(2)
    print("✅ Decorator test complete. Check LangWatch for 'test_function' trace.")


if __name__ == "__main__":
    print("LangWatch Integration Test")
    print("=" * 60)

    asyncio.run(test_langwatch_basic())
    asyncio.run(test_langwatch_trace_decorator())

    print("\n" + "=" * 60)
    print("Test complete! Check traces at: http://localhost:5560")
    print("=" * 60)
