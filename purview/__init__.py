"""
Purview Integration Module
================================================================================

This module provides integration with Microsoft Purview Data Governance for
looking up table and column asset descriptions, formatted as easy-to-read
essay-style prose.

================================================================================
DISCLAIMER
================================================================================
This code was generated with AI assistance (AI-generated code).
It is provided "AS-IS" under the MIT License without warranty of any kind.

LICENSE: MIT License - Copyright (c) 2026
See LICENSE file in project root for full license text.
================================================================================

USAGE:
    from purview import lookup_asset_description
    
    # Look up table and column descriptions in Purview
    # All parameters are required
    description = lookup_asset_description(
        db_type="oracle",
        host="db.example.com",
        port=1521,
        service_name="ORCL",
        schema="HR",
        table_name="EMPLOYEES"
    )
    # Returns essay-style description combining table and column info:
    #
    #   This table stores employee master data including personal information.
    #
    #   The table includes the following data elements: EMPLOYEE_ID (unique 
    #   identifier for each employee), FIRST_NAME (employee's given name), 
    #   and LAST_NAME (employee's family name).
    
    # Build qualified names for Purview lookups
    from purview import build_qualified_name
    qn = build_qualified_name(
        database_type="oracle",
        host="db.example.com",
        port=1521,
        service_name="ORCL",
        schema="HR",
        table_name="EMPLOYEES"
    )

DEPENDENCIES:
    pip install azure-identity azure-purview-catalog
"""

from purview.purview_handler import (
    # Main lookup function
    lookup_asset_description,
    
    # Client and config classes
    PurviewClient,
    PurviewConfig,
    
    # Qualified name utilities
    build_qualified_name,
    
    # Constants
    DATABASE_TYPE_MAPPINGS
)

__all__ = [
    # Main lookup function
    "lookup_asset_description",
    
    # Client and config classes
    "PurviewClient",
    "PurviewConfig",
    
    # Qualified name utilities
    "build_qualified_name",
    
    # Constants
    "DATABASE_TYPE_MAPPINGS"
]

