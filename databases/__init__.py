"""
Databases Package
================================================================================

This package contains database connectors for various database systems.

Supported Databases:
    - Oracle (via oracledb)
    - Microsoft SQL Server (via pyodbc)
    - PostgreSQL (via psycopg2)
    - IBM DB2 LUW (via ibm_db)

Usage:
    # Import specific connector (recommended - only requires that driver)
    from databases.oracle import OracleConnector
    from databases.mssql import MSSQLConnector
    from databases.postgres import PostgresConnector
    from databases.ibmdb2 import IBMDB2Connector

    # Or import all available connectors (requires all drivers installed)
    from databases import OracleConnector, MSSQLConnector, PostgresConnector, IBMDB2Connector

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

# Lazy imports - only import when accessed to avoid requiring all drivers
# Users can import directly from submodules: from databases.oracle import OracleConnector

__all__ = [
    "OracleConnector",
    "MSSQLConnector", 
    "PostgresConnector",
    "IBMDB2Connector",
]

# Optional imports - don't fail if driver is missing
try:
    from .oracle import OracleConnector
except ImportError:
    OracleConnector = None  # type: ignore

try:
    from .mssql import MSSQLConnector
except ImportError:
    MSSQLConnector = None  # type: ignore

try:
    from .postgres import PostgresConnector
except ImportError:
    PostgresConnector = None  # type: ignore

try:
    from .ibmdb2 import IBMDB2Connector
except ImportError:
    IBMDB2Connector = None  # type: ignore
