"""
Purview Integration Module
================================================================================

This module provides integration with Microsoft Purview Data Governance for
catalog management, asset registration, and classification.

================================================================================
DISCLAIMER
================================================================================
This code was generated with AI assistance (AI-generated code).
It is provided "AS-IS" under the MIT License without warranty of any kind.

LICENSE: MIT License - Copyright (c) 2026
See LICENSE file in project root for full license text.
================================================================================

USAGE:
    from purview import handle_purview_integration, PurviewClient
    
    # High-level function for agent generator
    result = handle_purview_integration("HR", "EMPLOYEES")
    
    # Direct client usage
    client = PurviewClient("purview_config.ini")
    asset = client.register_table_asset("HR", "EMPLOYEES")
    client.close()
    
    # Build qualified names for Purview lookups
    from purview import build_qualified_name
    qn = build_qualified_name("oracle", "HR", "EMPLOYEES", 
                               host="db.example.com", port=1521)
    
    # Parse existing qualified names
    from purview import parse_qualified_name
    parsed = parse_qualified_name("oracle://db.example.com:1521/ORCL/HR/EMPLOYEES")

DEPENDENCIES:
    pip install azure-identity azure-purview-catalog azure-purview-scanning
"""

from purview.purview_handler import (
    # Main integration function
    handle_purview_integration,
    
    # Client and data classes
    PurviewClient,
    PurviewConfig,
    PurviewAsset,
    QualifiedNameParams,
    
    # Qualified name utilities
    build_qualified_name,
    build_qualified_name_from_params,
    parse_qualified_name,
    get_database_type_info,
    get_supported_database_types,
    
    # Constants
    DATABASE_TYPE_MAPPINGS
)

__all__ = [
    # Main integration function
    "handle_purview_integration",
    
    # Client and data classes
    "PurviewClient",
    "PurviewConfig",
    "PurviewAsset",
    "QualifiedNameParams",
    
    # Qualified name utilities
    "build_qualified_name",
    "build_qualified_name_from_params",
    "parse_qualified_name",
    "get_database_type_info",
    "get_supported_database_types",
    
    # Constants
    "DATABASE_TYPE_MAPPINGS"
]

