# =============================================================================
# Data GraphQL Agent - MCP Service Dockerfile
# =============================================================================
# Multi-stage build for optimized container image
# =============================================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock* ./
COPY README.md ./

# Configure poetry to not create virtual env (we're in a container)
RUN poetry config virtualenvs.create false

# Install dependencies (skip installing the project itself)
RUN poetry install --only main --no-root --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY .env.example .env.example

# Create output directory for generated GraphQL servers
RUN mkdir -p /app/output

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash mcp && \
    chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Set Python path
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Set unbuffered Python output for better logging
ENV PYTHONUNBUFFERED=1

# Expose MCP service port (HTTP transport)
EXPOSE 8083

# Health check (for container orchestration)
# Note: Only works when MCP_TRANSPORT=http
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8083/health').read()" || exit 1

# Default command: run MCP server
CMD ["python", "-m", "data_graphql_agent.mcp"]

# Labels for container metadata
LABEL maintainer="data-graphql-agent"
LABEL description="MCP service for generating Apollo GraphQL servers from BigQuery queries"
LABEL version="1.0.0"

