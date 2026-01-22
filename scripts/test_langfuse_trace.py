#!/usr/bin/env python3
"""Test script to verify LangFuse tracing is working."""

import sys
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Handle LANGFUSE_BASE_URL -> LANGFUSE_HOST mapping if needed
if os.environ.get("LANGFUSE_BASE_URL") and not os.environ.get("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import settings


def test_langfuse_trace():
    """Test LangFuse tracing with a simple trace."""
    print("=" * 60)
    print("LangFuse Trace Test")
    print("=" * 60)
    print()

    # Check configuration
    print("📋 Configuration:")
    print(f"   OBSERVABILITY_PROVIDER: {settings.OBSERVABILITY_PROVIDER}")
    print(f"   LANGFUSE_HOST: {settings.LANGFUSE_HOST}")
    print(f"   LANGFUSE_PUBLIC_KEY: {settings.LANGFUSE_PUBLIC_KEY[:20]}..." if settings.LANGFUSE_PUBLIC_KEY else "   LANGFUSE_PUBLIC_KEY: Not set")
    print(f"   LANGFUSE_ENABLE_TRACING: {settings.LANGFUSE_ENABLE_TRACING}")
    print()

    # Test direct LangFuse connection first
    print("🔧 Testing direct LangFuse connection...")
    from langfuse import Langfuse

    try:
        langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        langfuse.auth_check()
        print("✅ LangFuse connection verified")
    except Exception as e:
        print(f"❌ LangFuse connection failed: {e}")
        return False
    print()

    # Create a test trace using the LangFuse 3.x API
    print("📤 Creating test trace with spans...")

    trace_id = None

    # Start a root span (automatically creates a trace)
    with langfuse.start_as_current_span(
        name="test-trace-verification",
        input={"test": True, "source": "test_langfuse_trace.py"},
        metadata={"test": True},
    ) as root_span:
        # Get the trace ID
        trace_id = langfuse.get_current_trace_id()
        print(f"   Trace ID: {trace_id}")

        # Update trace metadata
        langfuse.update_current_trace(
            tags=["test", "verification"],
            metadata={"test_type": "manual"},
        )

        # Simulate an LLM generation using start_as_current_observation
        with langfuse.start_as_current_observation(
            name="test-llm-call",
            as_type="generation",
            input="What is 2+2?",
            output="2+2 equals 4.",
            model="claude-3-5-sonnet-20241022",
            metadata={"simulated": True},
        ):
            pass  # Auto-ends on exit

        # Simulate a tool call
        with langfuse.start_as_current_span(
            name="test-tool-call",
            input={"query": "test query"},
            output={"result": "test result"},
            metadata={"tool": "test_tool"},
        ):
            pass  # Auto-ends on exit

    print("✅ Test trace created with nested spans")
    print()

    # Flush to ensure data is sent
    print("📤 Flushing data to LangFuse...")
    langfuse.flush()
    print("✅ Data flushed")
    print()

    # Get trace URL
    if trace_id:
        try:
            trace_url = langfuse.get_trace_url(trace_id)
            print(f"🔗 Direct trace URL: {trace_url}")
            print()
        except Exception:
            pass

    # Provide verification instructions
    print("🎉 Test complete!")
    print()
    print("📋 To verify the trace:")
    print(f"   1. Open LangFuse UI: {settings.LANGFUSE_HOST}")
    print("   2. Go to the 'Traces' section")
    print("   3. Look for trace: 'test-trace-verification'")
    print("   4. You should see nested spans:")
    print("      - test-trace-verification (root)")
    print("        └── test-llm-call (generation)")
    print("        └── test-tool-call (span)")
    print()

    # Shutdown gracefully
    langfuse.shutdown()

    return True


if __name__ == "__main__":
    success = test_langfuse_trace()
    sys.exit(0 if success else 1)
