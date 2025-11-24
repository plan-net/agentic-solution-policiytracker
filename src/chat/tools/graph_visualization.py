"""Graph visualization tool for displaying interactive knowledge graph in Open WebUI."""

import logging
from typing import Optional
from urllib.parse import urlencode

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GraphVisualizationInput(BaseModel):
    """Input schema for graph visualization tool."""

    session_id: Optional[str] = Field(
        default=None,
        description="Chat session ID to visualize context for. If not provided, will use current session.",
    )
    view_type: str = Field(
        default="chat-context",
        description="Type of view: 'chat-context' (session-based) or 'schema-explorer' (full schema)",
    )
    is_3d: bool = Field(default=True, description="Use 3D visualization (True) or 2D (False)")


class GraphVisualizationTool(BaseTool):
    """Tool for displaying interactive graph visualization in Open WebUI.

    This tool generates an iframe that embeds the React-based graph visualization UI.
    Users can interact with the graph to:
    - View entities and relationships
    - Click nodes/links to see details
    - Drag nodes to pin them in place
    - Switch between 2D and 3D views
    - Search and filter entities
    """

    name: str = "show_graph_visualization"
    description: str = (
        "Display an interactive knowledge graph visualization. "
        "Shows entities, relationships, and allows interaction (click, drag, search). "
        "Use when user asks to visualize, show graph, or explore knowledge graph structure."
    )
    args_schema: type[BaseModel] = GraphVisualizationInput

    graph_viz_url: str = "http://localhost:5173"

    def __init__(self, graph_viz_url: str = "http://localhost:5173", **kwargs):
        super().__init__(**kwargs)
        self.graph_viz_url = graph_viz_url

    class Config:
        arbitrary_types_allowed = True

    def _build_iframe_url(self, session_id: Optional[str], view_type: str, is_3d: bool) -> str:
        """Build the iframe URL with query parameters.

        Args:
            session_id: Session ID for chat context
            view_type: Type of view to display
            is_3d: Whether to use 3D visualization

        Returns:
            Full URL with query parameters
        """
        params = {}

        if view_type == "chat-context" and session_id:
            params["session"] = session_id
            params["view"] = "context"

        params["mode"] = "3d" if is_3d else "2d"

        query_string = urlencode(params) if params else ""
        url = f"{self.graph_viz_url}{'?' + query_string if query_string else ''}"

        logger.info(f"Built graph visualization URL: {url}")
        return url

    def _generate_iframe_html(self, iframe_url: str) -> str:
        """Generate HTML for embedding the graph visualization.

        Args:
            iframe_url: URL to embed in iframe

        Returns:
            HTML string with link and instructions (iframe stripped by Open WebUI)
        """
        html = f"""
## 📊 Interactive Knowledge Graph Visualization

**🔗 [Click here to open the interactive 3D knowledge graph →]({iframe_url})**

The visualization will open in a new tab where you can explore the knowledge graph.

### 🎮 Interactive Features:
- **Click nodes** to view entity details and properties
- **Click edges** to see relationship types and metadata
- **Drag nodes** to reposition them (they stay pinned!)
- **Mouse wheel** to zoom in/out
- **Right-click + drag** (3D mode) to rotate the view
- **Search bar** to filter entities by name or type
- **Reset button** to unpin all nodes and reset view
- **2D/3D toggle** to switch viewing modes

### 💡 Visualization Guide:
- **Yellow text on edges** shows relationship types (e.g., "IMPOSES", "FINES", "REGULATES")
- **Colored nodes** represent different entity types:
  - 🔵 Blue: Policies and Regulations
  - 🟢 Green: Organizations and Companies
  - 🟠 Orange: Politicians and People
  - 🔴 Red: Events and Actions
  - 🟣 Purple: Other entity types
- **Node size** indicates importance/centrality
- **Edge thickness** shows relationship strength

### 📊 What You'll See:
This shows the knowledge graph context for your current conversation, including:
- All entities mentioned or discovered during our chat
- Relationships between these entities
- Temporal connections and hierarchies
- Cross-references and related concepts

_Note: If you see 0 nodes/edges, we haven't extracted entities yet. Try asking about specific policies, companies, or regulations._
"""
        return html

    def _run(
        self,
        session_id: Optional[str] = None,
        view_type: str = "chat-context",
        is_3d: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"

    async def _arun(
        self,
        session_id: Optional[str] = None,
        view_type: str = "chat-context",
        is_3d: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Display interactive graph visualization.

        Args:
            session_id: Optional session ID for context-specific view
            view_type: Type of view ('chat-context' or 'schema-explorer')
            is_3d: Whether to use 3D visualization
            run_manager: Optional callback manager

        Returns:
            HTML string with embedded iframe and instructions
        """
        try:
            logger.info(
                f"Generating graph visualization: session_id={session_id}, view_type={view_type}, is_3d={is_3d}"
            )

            # Build iframe URL with parameters
            iframe_url = self._build_iframe_url(session_id, view_type, is_3d)

            # Generate HTML with iframe
            html_output = self._generate_iframe_html(iframe_url)

            logger.info("Graph visualization HTML generated successfully")
            return html_output

        except Exception as e:
            error_msg = f"Failed to generate graph visualization: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"❌ Error: {error_msg}\n\nPlease ensure the graph visualization service is running on {self.graph_viz_url}"
