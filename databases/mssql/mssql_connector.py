"""
Microsoft SQL Server Database Connector Module
================================================================================

A Python module for connecting to Microsoft SQL Server databases and querying 
table metadata and data, with results returned as pandas DataFrames for easy analysis.
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

FUNCTIONALITY
-------------
This module provides:
    - MSSQL database connection management using SQLAlchemy with connection pooling
    - Table structure/schema querying (columns, data types, constraints, indexes)
    - Table and column comment retrieval from MSSQL extended properties
    - SQL query execution with DataFrame results
    - Table data loading with filtering and pagination

USAGE
-----
Basic usage with context manager:

    from mssql_connector import MSSQLConnector

    with MSSQLConnector.from_host("sql.example.com") as mssql:
        # List all tables
        tables = mssql.list_tables()
        
        # Get table structure
        structure = mssql.get_table_structure("Employees")
        
        # Query data into DataFrame
        df = mssql.table_to_dataframe("Employees", limit=100)
        
        # Execute custom SQL
        result = mssql.query_to_dataframe("SELECT * FROM Employees WHERE Salary > 50000")

Manual connection management:

    mssql = MSSQLConnector.from_host("sql.example.com")
    mssql.connect(use_pool=True)  # Use connection pooling (default with SQLAlchemy)
    
    # ... perform operations ...
    
    mssql.disconnect()

CONFIGURATION
-------------
Connection configuration is stored in XML files under the security/ directory.
See security/mssql_connections.xml for examples of supported authentication methods:
    - sql_password: SQL Server authentication
    - windows_integrated: Windows/AD integrated auth
    - azure_keyvault: Credentials from Key Vault
    - entra_id_managed_identity: Azure Managed Identity
    - entra_id_service_principal: Azure AD service principal

DEPENDENCIES
------------
    - sqlalchemy >= 2.0.0
    - pyodbc >= 4.0.0
    - pandas >= 2.0.0
    - Microsoft ODBC Driver for SQL Server

Install with: pip install sqlalchemy pyodbc pandas

LICENSE
-------
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

DISCLAIMER
----------
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus

# Defer import error to class instantiation for graceful package loading
_PYODBC_IMPORT_ERROR = None
try:
    import pyodbc
except ImportError as e:
    pyodbc = None  # type: ignore
    _PYODBC_IMPORT_ERROR = e

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import QueuePool, NullPool
except ImportError:
    raise ImportError(
        "sqlalchemy package is required. Install it with: pip install sqlalchemy"
    )


class MSSQLConnector:
    """
    A class to manage Microsoft SQL Server database connections and table operations using SQLAlchemy.
    
    Configuration is loaded from XML files in the security/ directory via hostname lookup.
    Use the from_host() class method to create instances.
    
    Example:
        connector = MSSQLConnector.from_host("sql.example.com")
    """

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize the MSSQL connector with configuration dictionary.

        Args:
            config_dict: Dictionary with connection configuration.
                        Use MSSQLConnector.from_host() to create instances.
        """
        if _PYODBC_IMPORT_ERROR is not None:
            raise ImportError(
                "pyodbc package is required. Install it with: pip install pyodbc"
            ) from _PYODBC_IMPORT_ERROR
        
        self.config = config_dict
        self.engine: Optional[Engine] = None

    @classmethod
    def from_host(cls, host: str, security_dir: Optional[str] = None, connection_id: Optional[str] = None) -> "MSSQLConnector":
        """
        Create a MSSQLConnector by looking up connection configuration from XML files.
        
        Args:
            host: Database hostname to look up (e.g., "sql.example.com")
            security_dir: Optional path to security directory containing XML files.
                         Defaults to the project's security/ directory.
            connection_id: Optional specific connection ID to use
        
        Returns:
            Configured MSSQLConnector instance
        
        Example:
            connector = MSSQLConnector.from_host("sql.example.com")
            connector = MSSQLConnector.from_host("sql.example.com", connection_id="mssql_sql_example_hr_keyvault")
        """
        # Import here to avoid circular imports
        from security.connection_loader import ConnectionLoader
        
        loader = ConnectionLoader(security_dir)
        config = loader.get_connection_for_ini("mssql", host, connection_id)
        
        return cls(config_dict=config)

    def _get_connection_url(self) -> str:
        """Build the SQLAlchemy connection URL for MSSQL."""
        host = self.config["host"]
        port = self.config["port"]
        database = self.config.get("database", "master")
        driver = self.config.get("driver", "ODBC Driver 18 for SQL Server")
        
        # Build connection string parameters
        params = {
            "driver": driver,
            "server": f"{host},{port}",
            "database": database,
        }
        
        # Add authentication
        if self.config.get("trusted_connection"):
            params["Trusted_Connection"] = "yes"
        else:
            params["uid"] = self.config["username"]
            params["pwd"] = self.config["password"]
        
        # Add encryption settings
        if "encrypt" in self.config:
            params["Encrypt"] = "yes" if self.config["encrypt"] else "no"
        if self.config.get("trust_server_certificate"):
            params["TrustServerCertificate"] = "yes"
        
        # Build ODBC connection string
        odbc_connect = ";".join(f"{k}={v}" for k, v in params.items())
        
        # URL encode the connection string
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_connect)}"

    def connect(self, use_pool: bool = True) -> "MSSQLConnector":
        """
        Establish a connection to the MSSQL database using SQLAlchemy.

        Args:
            use_pool: If True (default), use connection pooling. If False, disable pooling.

        Returns:
            Self for method chaining
        """
        connection_url = self._get_connection_url()

        if use_pool:
            # Convert pool settings to int (may be strings from XML config)
            min_conn = int(self.config.get("min_connections", 1))
            max_conn = int(self.config.get("max_connections", 5))
            self.engine = create_engine(
                connection_url,
                poolclass=QueuePool,
                pool_size=min_conn,
                max_overflow=max_conn - min_conn,
                pool_pre_ping=True,
            )
        else:
            self.engine = create_engine(
                connection_url,
                poolclass=NullPool,
            )

        return self

    def get_connection(self):
        """Get a database connection from the SQLAlchemy engine."""
        if self.engine:
            return self.engine.connect()
        else:
            raise ConnectionError("Not connected. Call connect() first.")

    def disconnect(self) -> None:
        """Dispose of the SQLAlchemy engine and close all connections."""
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def _get_schema(self, schema: Optional[str] = None) -> str:
        """Get the schema to use, defaulting to config schema or 'dbo'."""
        return schema or self.config.get("schema", "dbo")

    def _get_database(self) -> str:
        """Get the database name from config."""
        return self.config.get("database", "master")

    def _ensure_engine(self) -> Engine:
        """Ensure the engine is initialized and return it."""
        if self.engine is None:
            raise ConnectionError("Not connected. Call connect() first.")
        return self.engine

    def get_table_structure(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query and return the structure of a table as a DataFrame.

        Args:
            table_name: Name of the table to describe
            schema: Schema of the table (defaults to config schema or 'dbo')

        Returns:
            DataFrame with column information (name, type, nullable, etc.)
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                c.COLUMN_NAME as column_name,
                c.DATA_TYPE as data_type,
                c.CHARACTER_MAXIMUM_LENGTH as data_length,
                c.NUMERIC_PRECISION as data_precision,
                c.NUMERIC_SCALE as data_scale,
                c.IS_NULLABLE as nullable,
                c.COLUMN_DEFAULT as data_default,
                c.ORDINAL_POSITION as column_id
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_NAME = :table_name
              AND c.TABLE_SCHEMA = :schema
            ORDER BY c.ORDINAL_POSITION
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name, "schema": resolved_schema})
            return df

    def get_table_constraints(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query and return the constraints of a table as a DataFrame.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            DataFrame with constraint information
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                tc.CONSTRAINT_NAME as constraint_name,
                tc.CONSTRAINT_TYPE as constraint_type,
                kcu.COLUMN_NAME as column_name,
                kcu.ORDINAL_POSITION as position
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                AND tc.TABLE_NAME = kcu.TABLE_NAME
            WHERE tc.TABLE_NAME = :table_name
              AND tc.TABLE_SCHEMA = :schema
            ORDER BY tc.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name, "schema": resolved_schema})
            return df

    def get_table_indexes(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query and return the indexes of a table as a DataFrame.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            DataFrame with index information
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                i.name as index_name,
                i.type_desc as index_type,
                CASE WHEN i.is_unique = 1 THEN 'UNIQUE' ELSE 'NONUNIQUE' END as uniqueness,
                c.name as column_name,
                ic.key_ordinal as column_position
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.name = :table_name
              AND s.name = :schema
              AND i.name IS NOT NULL
            ORDER BY i.name, ic.key_ordinal
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name, "schema": resolved_schema})
            return df

    def list_tables(self, schema: Optional[str] = None) -> pd.DataFrame:
        """
        List all tables in a schema.

        Args:
            schema: Schema to list tables from

        Returns:
            DataFrame with table names and metadata
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                t.TABLE_NAME as table_name,
                p.rows as num_rows,
                STATS_DATE(o.object_id, 1) as last_analyzed
            FROM INFORMATION_SCHEMA.TABLES t
            LEFT JOIN sys.objects o ON t.TABLE_NAME = o.name AND o.type = 'U'
            LEFT JOIN sys.partitions p ON o.object_id = p.object_id AND p.index_id IN (0, 1)
            LEFT JOIN sys.schemas s ON o.schema_id = s.schema_id
            WHERE t.TABLE_SCHEMA = :schema
              AND t.TABLE_TYPE = 'BASE TABLE'
            ORDER BY t.TABLE_NAME
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"schema": resolved_schema})
            return df

    def query_to_dataframe(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a DataFrame.

        Args:
            query: SQL query to execute
            params: Optional dictionary of bind parameters

        Returns:
            DataFrame with query results
        """
        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(text(query), conn, params=params or {})
            return df

    def table_to_dataframe(
        self,
        table_name: str,
        schema: Optional[str] = None,
        columns: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Load a table (or subset) into a DataFrame for querying.

        Args:
            table_name: Name of the table to load
            schema: Schema of the table
            columns: List of columns to select (None = all columns)
            where_clause: Optional WHERE clause (without 'WHERE' keyword)
            limit: Maximum number of rows to fetch

        Returns:
            DataFrame with table data
        """
        resolved_schema = self._get_schema(schema)

        # Build column list
        col_str = ", ".join(columns) if columns else "*"

        # Build query with TOP for limit (MSSQL syntax)
        if limit:
            query = f"SELECT TOP {limit} {col_str} FROM [{resolved_schema}].[{table_name}]"
        else:
            query = f"SELECT {col_str} FROM [{resolved_schema}].[{table_name}]"

        if where_clause:
            query += f" WHERE {where_clause}"

        return self.query_to_dataframe(query)

    def get_table_comments(
        self, table_name: str, schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get table and column comments/descriptions from MSSQL extended properties.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            Dictionary with 'table_comment' and 'column_comments' DataFrame
        """
        resolved_schema = self._get_schema(schema)

        # Get table comment (MS_Description extended property)
        table_comment_query = text("""
            SELECT CAST(ep.value AS NVARCHAR(MAX)) as comments
            FROM sys.extended_properties ep
            JOIN sys.tables t ON ep.major_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.name = :table_name
              AND s.name = :schema
              AND ep.minor_id = 0
              AND ep.name = 'MS_Description'
        """)

        # Get column comments
        column_comments_query = text("""
            SELECT 
                c.name as column_name,
                CAST(ep.value AS NVARCHAR(MAX)) as comments
            FROM sys.extended_properties ep
            JOIN sys.tables t ON ep.major_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            JOIN sys.columns c ON ep.major_id = c.object_id AND ep.minor_id = c.column_id
            WHERE t.name = :table_name
              AND s.name = :schema
              AND ep.name = 'MS_Description'
            ORDER BY c.name
        """)

        with self._ensure_engine().connect() as conn:
            table_comment_df = pd.read_sql(
                table_comment_query, conn, params={"table_name": table_name, "schema": resolved_schema}
            )
            column_comments_df = pd.read_sql(
                column_comments_query, conn, params={"table_name": table_name, "schema": resolved_schema}
            )

            table_comment = None
            if not table_comment_df.empty and table_comment_df.iloc[0]["comments"]:
                table_comment = table_comment_df.iloc[0]["comments"]

            return {
                "table_comment": table_comment,
                "column_comments": column_comments_df,
            }

    def get_full_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive table information including structure, constraints, indexes, and comments.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            Dictionary with 'structure', 'constraints', 'indexes', and 'comments' DataFrames
        """
        return {
            "structure": self.get_table_structure(table_name, schema),
            "constraints": self.get_table_constraints(table_name, schema),
            "indexes": self.get_table_indexes(table_name, schema),
            "comments": self.get_table_comments(table_name, schema),
        }

    def get_foreign_keys(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get foreign key relationships for a table, including referenced table and column information.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            DataFrame with foreign key information including referenced tables and columns
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                fk.name AS fk_constraint_name,
                COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS fk_column,
                fkc.constraint_column_id AS fk_position,
                OBJECT_NAME(fkc.referenced_object_id) AS referenced_table,
                SCHEMA_NAME(t_ref.schema_id) AS referenced_schema,
                COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS referenced_column
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            JOIN sys.tables t ON fk.parent_object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            JOIN sys.tables t_ref ON fkc.referenced_object_id = t_ref.object_id
            WHERE t.name = :table_name
              AND s.name = :schema
            ORDER BY fk.name, fkc.constraint_column_id
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name, "schema": resolved_schema})
            return df

    def get_table_description(
        self, table_name: str, schema: Optional[str] = None
    ) -> str:
        """
        Generate a human-readable description of a table including comments and join information.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            A formatted string describing the table, its columns, and how to join with other tables
        """
        resolved_schema = self._get_schema(schema)
        
        # Get table structure
        structure = self.get_table_structure(table_name, schema)
        
        # Get comments
        comments_info = self.get_table_comments(table_name, schema)
        table_comment = comments_info.get("table_comment")
        column_comments_df = comments_info.get("column_comments", pd.DataFrame())
        
        # Get foreign keys
        foreign_keys = self.get_foreign_keys(table_name, schema)
        
        # Build column comments lookup
        column_comments: Dict[str, str] = {}
        if not column_comments_df.empty:
            for _, row in column_comments_df.iterrows():
                col_name = row.get("column_name")
                comment = row.get("comments")
                if col_name and comment:
                    column_comments[col_name.lower()] = comment
        
        # Start building the description
        paragraphs: List[str] = []
        
        # Opening paragraph - table introduction
        table_full_name = f"[{resolved_schema}].[{table_name}]"
        if table_comment:
            paragraphs.append(
                f"The {table_full_name} table {table_comment.lower().rstrip('.')}. "
                f"This table is located in the {resolved_schema} schema."
            )
        else:
            paragraphs.append(
                f"The {table_full_name} table is located in the {resolved_schema} schema."
            )
        
        # Column descriptions paragraph
        if not structure.empty:
            column_descriptions = []
            for _, row in structure.iterrows():
                col_name = row.get("column_name")
                data_type = row.get("data_type")
                nullable = row.get("nullable")
                
                # Build data type description
                data_length = row.get("data_length")
                data_precision = row.get("data_precision")
                data_scale = row.get("data_scale")
                
                type_desc = self._get_friendly_type_name(str(data_type), data_length, data_precision, data_scale)
                required_str = "required" if nullable == "NO" else "optional"
                
                col_comment = column_comments.get(col_name.lower() if col_name else "", "")
                
                if col_comment:
                    column_descriptions.append(
                        f"{col_name} ({type_desc}, {required_str}) which {col_comment.lower().rstrip('.')}"
                    )
                else:
                    column_descriptions.append(f"{col_name} ({type_desc}, {required_str})")
            
            num_cols = len(column_descriptions)
            if num_cols > 1:
                paragraphs.append(
                    f"The table contains {num_cols} columns: "
                    f"{', '.join(column_descriptions[:-1])}"
                    f", and {column_descriptions[-1]}."
                )
            else:
                paragraphs.append(
                    f"The table contains {num_cols} column: {column_descriptions[0]}."
                )
        
        # Foreign key relationships paragraph
        if not foreign_keys.empty:
            # Group by constraint name for multi-column FKs
            fk_groups: Dict[str, List[Dict[str, Any]]] = {}
            for _, row in foreign_keys.iterrows():
                fk_name = row.get("fk_constraint_name")
                if fk_name is not None:
                    if fk_name not in fk_groups:
                        fk_groups[fk_name] = []
                    fk_groups[fk_name].append(dict(row))
            
            relationship_descriptions = []
            for fk_name, fk_rows in fk_groups.items():
                first_row = fk_rows[0]
                ref_schema = first_row.get("referenced_schema")
                ref_table = first_row.get("referenced_table")
                
                # Build join condition description
                join_parts = []
                for fk_row in sorted(fk_rows, key=lambda x: x.get("fk_position") or 0):
                    fk_col = fk_row.get("fk_column")
                    ref_col = fk_row.get("referenced_column")
                    join_parts.append(f"{fk_col} to {ref_col}")
                
                join_desc = " and ".join(join_parts)
                relationship_descriptions.append(
                    f"the [{ref_schema}].[{ref_table}] table by matching {join_desc}"
                )
            
            num_rels = len(relationship_descriptions)
            if num_rels > 1:
                paragraphs.append(
                    f"This table can be joined with {', '.join(relationship_descriptions[:-1])}"
                    f", and {relationship_descriptions[-1]}."
                )
            else:
                paragraphs.append(
                    f"This table can be joined with {relationship_descriptions[0]}."
                )
            
            # Add SQL examples
            sql_examples = []
            for fk_name, fk_rows in fk_groups.items():
                first_row = fk_rows[0]
                ref_schema = first_row.get("referenced_schema")
                ref_table = first_row.get("referenced_table")
                
                join_conditions = []
                for fk_row in sorted(fk_rows, key=lambda x: x.get("fk_position") or 0):
                    fk_col = fk_row.get("fk_column")
                    ref_col = fk_row.get("referenced_column")
                    join_conditions.append(f"[{table_name}].[{fk_col}] = [{ref_table}].[{ref_col}]")
                
                sql_examples.append(f"JOIN [{ref_schema}].[{ref_table}] ON {' AND '.join(join_conditions)}")
            
            paragraphs.append(
                f"To perform these joins in SQL, you can use: {'; '.join(sql_examples)}."
            )
        else:
            paragraphs.append(
                "This table does not have any foreign key relationships defined, "
                "meaning it is either a standalone reference table or its relationships "
                "are managed at the application level."
            )
        
        # Technical section - connection information (at the end)
        host = self.config.get("host", "unknown")
        port = self.config.get("port", 1433)
        database = self._get_database()
        
        technical_info = (
            f"Technical Information: This data resides in a Microsoft SQL Server database. "
            f"Connection details: Host: {host}, Port: {port}, Database: {database}. "
            f"Schema: {resolved_schema}."
        )
        paragraphs.append(technical_info)
        
        return "\n\n".join(paragraphs)

    def _get_friendly_type_name(
        self, data_type: str, data_length: Any, data_precision: Any, data_scale: Any
    ) -> str:
        """Convert MSSQL data type to a friendly description."""
        type_map = {
            "varchar": "text",
            "nvarchar": "unicode text",
            "char": "fixed-length text",
            "nchar": "fixed-length unicode text",
            "text": "large text",
            "ntext": "large unicode text",
            "int": "integer",
            "bigint": "large integer",
            "smallint": "small integer",
            "tinyint": "tiny integer",
            "decimal": "decimal number",
            "numeric": "number",
            "money": "currency",
            "smallmoney": "small currency",
            "float": "floating point number",
            "real": "real number",
            "date": "date",
            "datetime": "date and time",
            "datetime2": "date and time",
            "smalldatetime": "date and time",
            "time": "time",
            "datetimeoffset": "date and time with timezone",
            "bit": "boolean",
            "binary": "binary data",
            "varbinary": "variable binary data",
            "image": "image data",
            "uniqueidentifier": "unique identifier (GUID)",
            "xml": "XML data",
        }
        
        friendly_type = type_map.get(data_type.lower(), data_type.lower())
        
        if data_type.lower() in ("varchar", "nvarchar", "char", "nchar") and data_length and pd.notna(data_length):
            if data_length == -1:
                friendly_type += " (max)"
            else:
                friendly_type += f" up to {int(data_length)} characters"
        elif data_type.lower() in ("decimal", "numeric") and data_precision and pd.notna(data_precision):
            if data_scale and pd.notna(data_scale) and int(data_scale) > 0:
                friendly_type = f"decimal with {int(data_precision)} digits and {int(data_scale)} decimal places"
            else:
                friendly_type = f"integer up to {int(data_precision)} digits"
        
        return friendly_type

    def __enter__(self) -> "MSSQLConnector":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()


# Example usage
if __name__ == "__main__":
    # Example 1: Using context manager
    print("Example 1: Using context manager")
    print("-" * 50)

    try:
        with MSSQLConnector.from_host("sql.example.com") as mssql:
            # List all tables
            tables = mssql.list_tables()
            print("Tables in schema:")
            print(tables)

            # Get structure of a specific table
            if not tables.empty:
                first_table = tables.iloc[0]["table_name"]
                structure = mssql.get_table_structure(first_table)
                print(f"\nStructure of {first_table}:")
                print(structure)

    except FileNotFoundError as e:
        print(f"Config file not found: {e}")
    except Exception as e:
        print(f"Connection error: {e}")

    # Example 2: Manual connection management
    print("\nExample 2: Manual connection management")
    print("-" * 50)

    try:
        mssql = MSSQLConnector.from_host("sql.example.com")
        mssql.connect()

        # Query specific table structure
        structure_df = mssql.get_table_structure("Employees")
        print("Employees table structure:")
        print(structure_df)

        # Get full table info
        full_info = mssql.get_full_table_info("Employees")
        print("\nFull table info:")
        for key, value in full_info.items():
            print(f"\n{key}:")
            print(value)

        mssql.disconnect()

    except FileNotFoundError as e:
        print(f"Config file not found: {e}")
    except Exception as e:
        print(f"Error: {e}")
