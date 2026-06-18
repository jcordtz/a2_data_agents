"""
Agents Module
================================================================================

This module provides AI-powered data agents for natural language database querying.

Components:
    - DataAgent: Main AI agent for natural language queries
    - agent_generator: Utilities for generating table-specific agents
    - function_app: Azure Function endpoints

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

from .data_agent import DataAgent

__all__ = ["DataAgent"]
