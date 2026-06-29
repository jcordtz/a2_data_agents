# =============================================================================
# MCP Server Dockerfile
# =============================================================================
# Multi-stage build for the MCP server container.
#
# =============================================================================
# DISCLAIMER
# =============================================================================
# This code was generated with AI assistance (AI-generated code).
# It is provided "AS-IS" under the MIT License without warranty of any kind.
#
# Users should:
# - Review and test thoroughly before production use
# - Validate security implications for their specific use case
# - Ensure compliance with their organization's policies
#
# LICENSE: MIT License - Copyright (c) 2026
# See LICENSE file in project root for full license text.
# =============================================================================
#
# Build:
#   docker build -t mcp-server .
#
# Run:
#   docker run -p 8080:8080 mcp-server
# =============================================================================

FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt


# =============================================================================
# Runtime stage
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r mcp && useradd -r -g mcp mcp

# Copy wheels and install
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY mcp_server.py .
COPY __init__.py .

# Create data directory for agent registry
RUN mkdir -p /data && chown -R mcp:mcp /data

# Environment variables
ENV MCP_SERVER_PORT=8080
ENV MCP_REGISTRY_PATH=/data/agents.json
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER mcp

# Expose port
EXPOSE 8080

# Health check - more generous start period for container startup
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Start server
CMD ["python", "mcp_server.py"]
