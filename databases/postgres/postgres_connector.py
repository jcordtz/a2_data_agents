"""
PostgreSQL Database Connector Module
================================================================================

A Python module for connecting to PostgreSQL databases and querying 
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
    - PostgreSQL database connection management using SQLAlchemy with connection pooling
    - Table structure/schema querying (columns, data types, constraints, indexes)
    - Table and column comment retrieval from PostgreSQL system catalogs
    - SQL query execution with DataFrame results
    - Table data loading with filtering and pagination

USAGE
-----
Basic usage with context manager:

    from postgres_connector import PostgresConnector

    with PostgresConnector.from_host("sales-db.example.com") as pg:
        # List all tables
        tables = pg.list_tables()
        
        # Get table structure
        structure = pg.get_table_structure("employees")
        
        # Query data into DataFrame
        df = pg.table_to_dataframe("employees", limit=100)
        
        # Execute custom SQL
        result = pg.query_to_dataframe("SELECT * FROM employees WHERE salary > 50000")

Manual connection management:

    pg = PostgresConnector.from_host("sales-db.example.com")
    pg.connect(use_pool=True)  # Use connection pooling (default with SQLAlchemy)
    
    # ... perform operations ...
    
    pg.disconnect()

CONFIGURATION
-------------
Connection configuration is stored in XML files under the security/ directory.
See security/postgres_connections.xml for examples of supported authentication methods:
    - password: Traditional username/password
    - azure_keyvault: Credentials from Key Vault
    - certificate: Client certificate authentication
    - entra_id_managed_identity: Azure AD Managed Identity
    - entra_id_service_principal: Azure AD service principal

DEPENDENCIES
------------
    - sqlalchemy >= 2.0.0
    - psycopg2-binary >= 2.9.0 (or psycopg2)
    - pandas >= 2.0.0

Install with: pip install sqlalchemy psycopg2-binary pandas

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
_PSYCOPG2_IMPORT_ERROR = None
try:
    import psycopg2
except ImportError as e:
    psycopg2 = None  # type: ignore
    _PSYCOPG2_IMPORT_ERROR = e

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import QueuePool, NullPool
except ImportError:
    raise ImportError(
        "sqlalchemy package is required. Install it with: pip install sqlalchemy"
    )


class PostgresConnector:
    """
    A class to manage PostgreSQL database connections and table operations using SQLAlchemy.
    
    Configuration is loaded from XML files in the security/ directory via hostname lookup.
    Use the from_host() class method to create instances.
    
    Example:
        connector = PostgresConnector.from_host("sales-db.example.com")
    """

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize the PostgreSQL connector with configuration dictionary.

        Args:
            config_dict: Dictionary with connection configuration.
                        Use PostgresConnector.from_host() to create instances.
        """
        if _PSYCOPG2_IMPORT_ERROR is not None:
            raise ImportError(
                "psycopg2 package is required. Install it with: pip install psycopg2-binary"
            ) from _PSYCOPG2_IMPORT_ERROR
        
        self.config = config_dict
        self.engine: Optional[Engine] = None

    @classmethod
    def from_host(cls, host: str, security_dir: Optional[str] = None, connection_id: Optional[str] = None) -> "PostgresConnector":
        """
        Create a PostgresConnector by looking up connection configuration from XML files.
        
        Args:
            host: Database hostname to look up (e.g., "sales-db.example.com")
            security_dir: Optional path to security directory containing XML files.
                         Defaults to the project's security/ directory.
            connection_id: Optional specific connection ID to use
        
        Returns:
            Configured PostgresConnector instance
        
        Example:
            connector = PostgresConnector.from_host("sales-db.example.com")
            connector = PostgresConnector.from_host("analytics.example.com", connection_id="postgres_analytics_example_analytics_mi")
        """
        # Import here to avoid circular imports
        from security.connection_loader import ConnectionLoader
        
        loader = ConnectionLoader(security_dir)
        config = loader.get_connection_for_ini("postgres", host, connection_id)
        
        return cls(config_dict=config)

    def _get_connection_url(self) -> str:
        """Build the SQLAlchemy connection URL for PostgreSQL."""
        username = quote_plus(self.config["username"])
        password = quote_plus(self.config["password"])
        host = self.config["host"]
        port = self.config["port"]
        database = self.config.get("database", "postgres")
        
        base_url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        
        # Add optional parameters
        params = []
        if "sslmode" in self.config:
            params.append(f"sslmode={self.config['sslmode']}")
        if "application_name" in self.config:
            params.append(f"application_name={quote_plus(self.config['application_name'])}")
        
        if params:
            base_url += "?" + "&".join(params)
        
        return base_url

    def connect(self, use_pool: bool = True) -> "PostgresConnector":
        """
        Establish a connection to the PostgreSQL database using SQLAlchemy.

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
        """Get the schema to use, defaulting to config schema or 'public'."""
        return schema or self.config.get("schema", "public")

    def _get_database(self) -> str:
        """Get the database name from config."""
        return self.config.get("database", "postgres")

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
            schema: Schema of the table (defaults to config schema or 'public')

        Returns:
            DataFrame with column information (name, type, nullable, etc.)
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                c.column_name,
                c.data_type,
                c.character_maximum_length as data_length,
                c.numeric_precision as data_precision,
                c.numeric_scale as data_scale,
                c.is_nullable as nullable,
                c.column_default as data_default,
                c.ordinal_position as column_id
            FROM information_schema.columns c
            WHERE c.table_name = :table_name
              AND c.table_schema = :schema
            ORDER BY c.ordinal_position
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
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name,
                kcu.ordinal_position as position
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
                AND tc.table_name = kcu.table_name
            WHERE tc.table_name = :table_name
              AND tc.table_schema = :schema
            ORDER BY tc.constraint_name, kcu.ordinal_position
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
                i.relname as index_name,
                am.amname as index_type,
                CASE WHEN ix.indisunique THEN 'UNIQUE' ELSE 'NONUNIQUE' END as uniqueness,
                a.attname as column_name,
                array_position(ix.indkey, a.attnum) as column_position
            FROM pg_index ix
            JOIN pg_class t ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_am am ON am.oid = i.relam
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = :table_name
              AND n.nspname = :schema
            ORDER BY i.relname, array_position(ix.indkey, a.attnum)
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
                t.table_name,
                c.reltuples::bigint as num_rows,
                pg_stat_user_tables.last_analyze as last_analyzed
            FROM information_schema.tables t
            LEFT JOIN pg_class c ON c.relname = t.table_name
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
            LEFT JOIN pg_stat_user_tables ON pg_stat_user_tables.relname = t.table_name 
                AND pg_stat_user_tables.schemaname = t.table_schema
            WHERE t.table_schema = :schema
              AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name
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
        col_str = ", ".join(f'"{c}"' for c in columns) if columns else "*"

        # Build query
        query = f'SELECT {col_str} FROM "{resolved_schema}"."{table_name}"'

        if where_clause:
            query += f" WHERE {where_clause}"

        if limit:
            query += f" LIMIT {limit}"

        return self.query_to_dataframe(query)

    def get_table_comments(
        self, table_name: str, schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get table and column comments/descriptions from PostgreSQL system catalogs.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            Dictionary with 'table_comment' and 'column_comments' DataFrame
        """
        resolved_schema = self._get_schema(schema)

        # Get table comment
        table_comment_query = text("""
            SELECT obj_description(
                (SELECT c.oid FROM pg_class c 
                 JOIN pg_namespace n ON n.oid = c.relnamespace 
                 WHERE c.relname = :table_name AND n.nspname = :schema),
                'pg_class'
            ) as comments
        """)

        # Get column comments
        column_comments_query = text("""
            SELECT 
                a.attname as column_name,
                col_description(c.oid, a.attnum) as comments
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = c.oid
            WHERE c.relname = :table_name
              AND n.nspname = :schema
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
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
                tc.constraint_name AS fk_constraint_name,
                kcu.column_name AS fk_column,
                kcu.ordinal_position AS fk_position,
                ccu.table_name AS referenced_table,
                ccu.table_schema AS referenced_schema,
                ccu.column_name AS referenced_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = :table_name
              AND tc.table_schema = :schema
            ORDER BY tc.constraint_name, kcu.ordinal_position
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
        table_full_name = f'"{resolved_schema}"."{table_name}"'
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
                    f'the "{ref_schema}"."{ref_table}" table by matching {join_desc}'
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
                    join_conditions.append(f'"{table_name}"."{fk_col}" = "{ref_table}"."{ref_col}"')
                
                sql_examples.append(f'JOIN "{ref_schema}"."{ref_table}" ON {" AND ".join(join_conditions)}')
            
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
        port = self.config.get("port", 5432)
        database = self._get_database()
        
        technical_info = (
            f"Technical Information: This data resides in a PostgreSQL database. "
            f"Connection details: Host: {host}, Port: {port}, Database: {database}. "
            f"Schema: {resolved_schema}."
        )
        paragraphs.append(technical_info)
        
        return "\n\n".join(paragraphs)

    def _get_friendly_type_name(
        self, data_type: str, data_length: Any, data_precision: Any, data_scale: Any
    ) -> str:
        """Convert PostgreSQL data type to a friendly description."""
        type_map = {
            "character varying": "text",
            "varchar": "text",
            "character": "fixed-length text",
            "char": "fixed-length text",
            "text": "text",
            "integer": "integer",
            "int": "integer",
            "int4": "integer",
            "bigint": "large integer",
            "int8": "large integer",
            "smallint": "small integer",
            "int2": "small integer",
            "numeric": "number",
            "decimal": "decimal number",
            "real": "real number",
            "float4": "real number",
            "double precision": "floating point number",
            "float8": "floating point number",
            "money": "currency",
            "date": "date",
            "timestamp without time zone": "timestamp",
            "timestamp with time zone": "timestamp with timezone",
            "time without time zone": "time",
            "time with time zone": "time with timezone",
            "interval": "time interval",
            "boolean": "boolean",
            "bool": "boolean",
            "bytea": "binary data",
            "uuid": "unique identifier (UUID)",
            "json": "JSON data",
            "jsonb": "binary JSON data",
            "xml": "XML data",
            "array": "array",
            "inet": "IP address",
            "cidr": "network address",
            "macaddr": "MAC address",
        }
        
        friendly_type = type_map.get(data_type.lower(), data_type.lower())
        
        if data_type.lower() in ("character varying", "varchar", "character", "char") and data_length and pd.notna(data_length):
            friendly_type += f" up to {int(data_length)} characters"
        elif data_type.lower() in ("numeric", "decimal") and data_precision and pd.notna(data_precision):
            if data_scale and pd.notna(data_scale) and int(data_scale) > 0:
                friendly_type = f"decimal with {int(data_precision)} digits and {int(data_scale)} decimal places"
            else:
                friendly_type = f"integer up to {int(data_precision)} digits"
        
        return friendly_type

    def __enter__(self) -> "PostgresConnector":
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
        with PostgresConnector.from_host("sales-db.example.com") as pg:
            # List all tables
            tables = pg.list_tables()
            print("Tables in schema:")
            print(tables)

            # Get structure of a specific table
            if not tables.empty:
                first_table = tables.iloc[0]["table_name"]
                structure = pg.get_table_structure(first_table)
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
        pg = PostgresConnector.from_host("sales-db.example.com")
        pg.connect()

        # Query specific table structure
        structure_df = pg.get_table_structure("employees")
        print("employees table structure:")
        print(structure_df)

        # Get full table info
        full_info = pg.get_full_table_info("employees")
        print("\nFull table info:")
        for key, value in full_info.items():
            print(f"\n{key}:")
            print(value)

        pg.disconnect()

    except FileNotFoundError as e:
        print(f"Config file not found: {e}")
    except Exception as e:
        print(f"Error: {e}")
