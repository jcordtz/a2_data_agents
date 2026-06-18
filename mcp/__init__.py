"""MCP Server Package
================================================================================

Model Context Protocol server for Oracle data agents.
Provides a unified interface for AI models to query multiple table-specific agents.

================================================================================
DISCLAIMER
================================================================================
This code was generated with AI assistance (AI-generated code).
It is provided "AS-IS" under the MIT License without warranty of any kind.

Users should:
- Review and test thoroughly before production use
- Validate security implications for their specific use case
- Ensure compliance with their organization's policies

LICENSE: MIT License - Copyright (c) 2026
See LICENSE file in project root for full license text.
================================================================================
"""

from .mcp_server import app, registry

__all__ = ["app", "registry"]
