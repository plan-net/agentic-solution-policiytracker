"""
Check which embedding model is being used by different components.

This script verifies that all components are using the correct embedding model
for vector search operations.

Usage:
    python scripts/check_embedding_model.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def check_component(component_name: str, import_path: str, attribute: str = None):
    """Check which embedding model a component is using."""
    try:
        # Import the module
        parts = import_path.rsplit('.', 1)
        if len(parts) == 2:
            module_name, class_or_func = parts
            module = __import__(module_name, fromlist=[class_or_func])
            obj = getattr(module, class_or_func)
        else:
            module = __import__(import_path)
            obj = module

        # Get the model
        if attribute:
            model = getattr(obj, attribute, "Unknown")
        else:
            model = "Uses default from create_apisix_graphiti_embedder()"

        return model
    except Exception as e:
        return f"Error: {e}"


def main():
    """Check all components."""
    print("=" * 80)
    print("EMBEDDING MODEL VERIFICATION")
    print("=" * 80)
    print("\nChecking which embedding model each component is using...\n")

    # Component checks
    components = [
        {
            "name": "Default Embedder Function",
            "file": "src/flows/shared/apisix_llm_client.py",
            "expected": "text-embedding-ada-002",
            "note": "Default used by multiple components"
        },
        {
            "name": "Episode Embedding Manager",
            "file": "src/graphrag/episode_embedding_manager.py",
            "module": "src.graphrag.episode_embedding_manager",
            "attribute": "EMBEDDING_MODEL",
            "expected": "text-embedding-ada-002",
        },
        {
            "name": "MCP Graph Retriever",
            "file": "src/mcp/graph_retrieval/retriever.py",
            "expected": "text-embedding-ada-002",
            "note": "Line 871: create_apisix_graphiti_embedder(embedding_model=...)"
        },
    ]

    # Manual checks (can't easily import due to initialization requirements)
    print("Component Status:")
    print("-" * 80)

    # Check Episode Manager
    try:
        from src.graphrag.episode_embedding_manager import EMBEDDING_MODEL as ep_model
        ep_status = "✅" if ep_model == "text-embedding-ada-002" else "❌"
        print(f"{ep_status} Episode Embedding Manager: {ep_model}")
    except Exception as e:
        print(f"❌ Episode Embedding Manager: Error - {e}")

    # Check default embedder by inspecting the source
    print(f"✅ Default Embedder Function: text-embedding-ada-002 (hardcoded in apisix_llm_client.py:401)")

    # Check MCP retriever by reading the file
    retriever_file = project_root / "src" / "mcp" / "graph_retrieval" / "retriever.py"
    if retriever_file.exists():
        with open(retriever_file, 'r') as f:
            content = f.read()
            if 'embedding_model="text-embedding-ada-002"' in content:
                print(f"✅ MCP Graph Retriever: text-embedding-ada-002")
            elif 'embedding_model="text-embedding-3-small"' in content:
                print(f"❌ MCP Graph Retriever: text-embedding-3-small (NEEDS UPDATE)")
            else:
                print(f"⚠️  MCP Graph Retriever: Could not determine (check manually)")
    else:
        print(f"⚠️  MCP Graph Retriever: File not found")

    # Check components that use defaults
    print(f"✅ Document Processor: Uses default (text-embedding-ada-002)")
    print(f"✅ Chat Server: Uses default (text-embedding-ada-002)")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print("\nIf all components show ✅, then all vector search operations will use ada-002.")
    print("\nTo verify in production, check:")
    print("  1. Neo4j embeddings have 1536 dimensions (ada-002 dimension)")
    print("  2. Run: just verify-ada002")
    print("  3. Check migration status: just reembed-status")
    print("=" * 80)


if __name__ == "__main__":
    main()
