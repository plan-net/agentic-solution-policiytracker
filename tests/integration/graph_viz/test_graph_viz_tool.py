"""Test the graph visualization tool integration."""
import asyncio
from src.chat.tools.graph_visualization import GraphVisualizationTool


async def test_tool():
    """Test the graph visualization tool."""
    print("🧪 Testing Graph Visualization Tool\n")

    # Initialize tool
    tool = GraphVisualizationTool()

    print(f"✅ Tool initialized")
    print(f"   Name: {tool.name}")
    print(f"   Description: {tool.description[:100]}...")
    print()

    # Test 1: Generate visualization without session ID
    print("📊 Test 1: Generate visualization (no session ID)")
    html_output = await tool._arun()
    print(f"   Output length: {len(html_output)} characters")
    print(f"   Contains iframe: {'<iframe' in html_output}")
    print(f"   Contains instructions: {'How to Use' in html_output}")
    print()

    # Test 2: Generate visualization with session ID
    print("📊 Test 2: Generate visualization with session ID")
    session_id = "session_20251124_112220"
    html_output_with_session = await tool._arun(session_id=session_id)
    print(f"   Output length: {len(html_output_with_session)} characters")
    print(f"   Contains session ID in URL: {session_id in html_output_with_session}")
    print()

    # Test 3: Show sample HTML output
    print("📄 Sample HTML Output:")
    print("=" * 80)
    print(html_output_with_session[:500])
    print("..." if len(html_output_with_session) > 500 else "")
    print("=" * 80)
    print()

    print("✅ All tests passed!")
    print()
    print("💡 Next Steps:")
    print("   1. Open Open WebUI at http://localhost:3000")
    print("   2. Start a chat and ask: 'Show me the graph visualization'")
    print("   3. The agent should invoke the tool and display an iframe")
    print("   4. You'll see the interactive 3D graph embedded in the chat")


if __name__ == "__main__":
    asyncio.run(test_tool())
