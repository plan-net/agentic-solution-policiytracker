FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY src/mcp/graph_retrieval/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server source code
COPY src/mcp/graph_retrieval/ /app/src/mcp/graph_retrieval/

# Environment variables (defaults, can be overridden at runtime)
ENV NEO4J_URI=bolt://neo4j:7687
ENV NEO4J_USER=neo4j
ENV NEO4J_PASSWORD=password123
ENV NEO4J_DATABASE=politicalmonitoring.v3
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8003
ENV LOG_LEVEL=INFO
ENV PYTHONPATH=/app

EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["python", "-m", "src.mcp.graph_retrieval.server"]
