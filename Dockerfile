FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast Python package management
RUN pip install uv

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Install Python dependencies using UV
RUN uv pip install --system --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY config.yaml ./
COPY .env.template ./

# Create data directories with proper permissions
RUN mkdir -p /data/input /data/output /data/context && \
    chmod 755 /data/input /data/output /data/context

# Create a default context file
RUN echo "# Default context file - replace with your organization's context" > /data/context/client.yaml && \
    echo "company_terms:" >> /data/context/client.yaml && \
    echo "  - your-company" >> /data/context/client.yaml && \
    echo "core_industries:" >> /data/context/client.yaml && \
    echo "  - technology" >> /data/context/client.yaml && \
    echo "primary_markets:" >> /data/context/client.yaml && \
    echo "  - global" >> /data/context/client.yaml && \
    echo "strategic_themes:" >> /data/context/client.yaml && \
    echo "  - digital transformation" >> /data/context/client.yaml

# Set environment variables
ENV PYTHONPATH=/app
ENV RAY_ADDRESS=auto
ENV DEFAULT_INPUT_FOLDER=/data/input
ENV DEFAULT_OUTPUT_FOLDER=/data/output
ENV DEFAULT_CONTEXT_FOLDER=/data/context

# Expose Kodosumi service port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# The actual start command will be managed by Kodosumi
CMD ["echo", "This container should be started using Kodosumi runtime"]