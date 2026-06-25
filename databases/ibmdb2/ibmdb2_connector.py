"""
IBM DB2 LUW Database Connector Module
================================================================================

A Python module for connecting to IBM DB2 LUW (Linux, Unix, Windows) databases 
and querying table metadata and data, with results returned as pandas DataFrames 
for easy analysis.
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
    - IBM DB2 database connection management using SQLAlchemy with connection pooling
    - Table structure/schema querying (columns, data types, constraints, indexes)
    - Table and column comment retrieval from DB2 catalog
    - SQL query execution with DataFrame results
    - Table data loading with filtering and pagination

USAGE
-----
Basic usage with context manager:

    from ibmdb2_connector import IBMDB2Connector

    with IBMDB2Connector("ibmdb2_config.ini") as db2:
        # List all tables
        tables = db2.list_tables()
        
        # Get table structure
        structure = db2.get_table_structure("EMPLOYEES")
        
        # Query data into DataFrame
        df = db2.table_to_dataframe("EMPLOYEES", limit=100)
        
        # Execute custom SQL
        result = db2.query_to_dataframe("SELECT * FROM EMPLOYEES WHERE SALARY > 50000")

Manual connection management:

    db2 = IBMDB2Connector("ibmdb2_config.ini")
    db2.connect(use_pool=True)  # Use connection pooling
    
    # ... perform operations ...
    
    db2.disconnect()

CONFIGURATION FILE FORMAT (ibmdb2_config.ini)
--------------------------------------------
    [ibmdb2]
    host = localhost
    port = 50000
    database = sample
    username = db2inst1
    password = your_password
    schema = DB2INST1
    country = US

DEPENDENCIES
------------
    - sqlalchemy >= 2.0.0
    - ibm_db_sa >= 0.4.0
    - ibm_db >= 3.0.0
    - pandas >= 2.0.0

Install with: pip install sqlalchemy ibm_db ibm_db_sa pandas

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

import configparser
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List

# Defer import error to class instantiation for graceful package loading
_IBMDB_IMPORT_ERROR = None
try:
    import ibm_db
    import ibm_db_sa
except ImportError as e:
    ibm_db = None  # type: ignore
    ibm_db_sa = None  # type: ignore
    _IBMDB_IMPORT_ERROR = e

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import QueuePool, NullPool
except ImportError:
    raise ImportError(
        "sqlalchemy package is required. Install it with: pip install sqlalchemy"
    )


class IBMDB2Connector:
    """
    A class to manage IBM DB2 LUW database connections and table operations using SQLAlchemy.
    """

    def __init__(self, config_path: str = "ibmdb2_config.ini"):
        """
        Initialize the IBM DB2 connector with configuration from a file.

        Args:
            config_path: Path to the configuration INI file
        """
        if _IBMDB_IMPORT_ERROR is not None:
            raise ImportError(
                "ibm_db and ibm_db_sa packages are required. Install with: pip install ibm_db ibm_db_sa"
            ) from _IBMDB_IMPORT_ERROR
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.engine: Optional[Engine] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the INI file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        parser = configparser.ConfigParser()
        parser.read(self.config_path)

        if "ibmdb2" not in parser.sections():
            raise ValueError("Config file must contain an [ibmdb2] section")

        config: Dict[str, Any] = dict(parser["ibmdb2"])

        # Convert port to integer
        config["port"] = int(config.get("port", 50000))

        # Convert pool settings to integers if present
        if "min_connections" in config:
            config["min_connections"] = int(config["min_connections"])
        if "max_connections" in config:
            config["max_connections"] = int(config["max_connections"])

        # Convert boolean settings
        if "ssl" in config:
            config["ssl"] = config["ssl"].lower() in ("true", "yes", "1")

        return config

    def _get_connection_url(self) -> str:
        """Build the SQLAlchemy connection URL for IBM DB2."""
        host = self.config["host"]
        port = self.config["port"]
        database = self.config.get("database", "sample")
        username = self.config["username"]
        password = self.config["password"]
        
        # Build the DB2 connection URL for ibm_db_sa
        # Format: ibm_db_sa://user:password@host:port/database
        url = f"ibm_db_sa://{username}:{password}@{host}:{port}/{database}"
        
        # Add SSL if configured
        if self.config.get("ssl"):
            url += "?Security=SSL"
        
        return url

    def connect(self, use_pool: bool = True) -> "IBMDB2Connector":
        """
        Establish a connection to the IBM DB2 database using SQLAlchemy.

        Args:
            use_pool: If True (default), use connection pooling. If False, disable pooling.

        Returns:
            Self for method chaining
        """
        connection_url = self._get_connection_url()

        if use_pool:
            self.engine = create_engine(
                connection_url,
                poolclass=QueuePool,
                pool_size=self.config.get("min_connections", 1),
                max_overflow=self.config.get("max_connections", 5) - self.config.get("min_connections", 1),
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
        """Get the schema to use, defaulting to config schema or username."""
        return (schema or self.config.get("schema") or self.config.get("username", "")).upper()

    def _get_database(self) -> str:
        """Get the database name from config."""
        return self.config.get("database", "sample")

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
            schema: Schema of the table (defaults to config schema or username)

        Returns:
            DataFrame with column information (name, type, nullable, etc.)
        """
        resolved_schema = self._get_schema(schema)
        table_name_upper = table_name.upper()

        query = text("""
            SELECT 
                COLNAME as column_name,
                TYPENAME as data_type,
                LENGTH as data_length,
                SCALE as data_scale,
                CASE WHEN NULLS = 'Y' THEN 'YES' ELSE 'NO' END as nullable,
                DEFAULT as data_default,
                COLNO as column_id
            FROM SYSCAT.COLUMNS
            WHERE TABNAME = :table_name
              AND TABSCHEMA = :schema
            ORDER BY COLNO
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name_upper, "schema": resolved_schema})
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
        table_name_upper = table_name.upper()

        query = text("""
            SELECT 
                tc.CONSTNAME as constraint_name,
                tc.TYPE as constraint_type,
                kc.COLNAME as column_name,
                kc.COLSEQ as position
            FROM SYSCAT.TABCONST tc
            LEFT JOIN SYSCAT.KEYCOLUSE kc
                ON tc.CONSTNAME = kc.CONSTNAME
                AND tc.TABSCHEMA = kc.TABSCHEMA
                AND tc.TABNAME = kc.TABNAME
            WHERE tc.TABNAME = :table_name
              AND tc.TABSCHEMA = :schema
            ORDER BY tc.CONSTNAME, kc.COLSEQ
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name_upper, "schema": resolved_schema})
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
        table_name_upper = table_name.upper()

        query = text("""
            SELECT 
                i.INDNAME as index_name,
                i.INDEXTYPE as index_type,
                CASE WHEN i.UNIQUERULE = 'D' THEN 'NONUNIQUE' 
                     WHEN i.UNIQUERULE = 'U' THEN 'UNIQUE'
                     WHEN i.UNIQUERULE = 'P' THEN 'PRIMARY'
                     ELSE i.UNIQUERULE END as uniqueness,
                ic.COLNAME as column_name,
                ic.COLSEQ as column_position
            FROM SYSCAT.INDEXES i
            JOIN SYSCAT.INDEXCOLUSE ic 
                ON i.INDSCHEMA = ic.INDSCHEMA 
                AND i.INDNAME = ic.INDNAME
            WHERE i.TABNAME = :table_name
              AND i.TABSCHEMA = :schema
            ORDER BY i.INDNAME, ic.COLSEQ
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name_upper, "schema": resolved_schema})
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
                t.TABNAME as table_name,
                t.CARD as num_rows,
                t.STATS_TIME as last_analyzed
            FROM SYSCAT.TABLES t
            WHERE t.TABSCHEMA = :schema
              AND t.TYPE = 'T'
            ORDER BY t.TABNAME
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
        table_name_upper = table_name.upper()

        # Build column list
        col_str = ", ".join(columns) if columns else "*"

        # Build query
        query = f"SELECT {col_str} FROM \"{resolved_schema}\".\"{table_name_upper}\""

        if where_clause:
            query += f" WHERE {where_clause}"

        # DB2 uses FETCH FIRST n ROWS ONLY for limiting
        if limit:
            query += f" FETCH FIRST {limit} ROWS ONLY"

        return self.query_to_dataframe(query)

    def get_table_comments(
        self, table_name: str, schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get table and column comments/descriptions from DB2 catalog.

        Args:
            table_name: Name of the table
            schema: Schema of the table

        Returns:
            Dictionary with 'table_comment' and 'column_comments' DataFrame
        """
        resolved_schema = self._get_schema(schema)
        table_name_upper = table_name.upper()

        # Get table comment
        table_comment_query = text("""
            SELECT REMARKS as comments
            FROM SYSCAT.TABLES
            WHERE TABNAME = :table_name
              AND TABSCHEMA = :schema
        """)

        # Get column comments
        column_comments_query = text("""
            SELECT 
                COLNAME as column_name,
                REMARKS as comments
            FROM SYSCAT.COLUMNS
            WHERE TABNAME = :table_name
              AND TABSCHEMA = :schema
              AND REMARKS IS NOT NULL
            ORDER BY COLNO
        """)

        with self._ensure_engine().connect() as conn:
            table_comment_df = pd.read_sql(
                table_comment_query, conn, params={"table_name": table_name_upper, "schema": resolved_schema}
            )
            column_comments_df = pd.read_sql(
                column_comments_query, conn, params={"table_name": table_name_upper, "schema": resolved_schema}
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
        table_name_upper = table_name.upper()

        query = text("""
            SELECT 
                r.CONSTNAME AS fk_constraint_name,
                kc.COLNAME AS fk_column,
                kc.COLSEQ AS fk_position,
                r.REFTABNAME AS referenced_table,
                r.REFTABSCHEMA AS referenced_schema,
                rkc.COLNAME AS referenced_column
            FROM SYSCAT.REFERENCES r
            JOIN SYSCAT.KEYCOLUSE kc
                ON r.CONSTNAME = kc.CONSTNAME
                AND r.TABSCHEMA = kc.TABSCHEMA
                AND r.TABNAME = kc.TABNAME
            JOIN SYSCAT.KEYCOLUSE rkc
                ON r.REFKEYNAME = rkc.CONSTNAME
                AND r.REFTABSCHEMA = rkc.TABSCHEMA
                AND r.REFTABNAME = rkc.TABNAME
                AND kc.COLSEQ = rkc.COLSEQ
            WHERE r.TABNAME = :table_name
              AND r.TABSCHEMA = :schema
            ORDER BY r.CONSTNAME, kc.COLSEQ
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name_upper, "schema": resolved_schema})
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
        table_name_upper = table_name.upper()
        
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
                if row["comments"]:
                    column_comments[row["column_name"]] = row["comments"]
        
        # Build the description
        lines = []
        lines.append(f"Table: {resolved_schema}.{table_name_upper}")
        
        if table_comment:
            lines.append(f"Description: {table_comment}")
        
        lines.append("")
        lines.append("Columns:")
        
        for _, col in structure.iterrows():
            col_name = col["column_name"]
            col_type = col["data_type"]
            length = col.get("data_length")
            scale = col.get("data_scale")
            nullable = col["nullable"]
            
            # Build type string
            if pd.notna(length) and length:
                if pd.notna(scale) and scale:
                    type_str = f"{col_type}({int(length)},{int(scale)})"
                else:
                    type_str = f"{col_type}({int(length)})"
            else:
                type_str = col_type
            
            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            col_line = f"  - {col_name}: {type_str} {null_str}"
            
            if col_name in column_comments:
                col_line += f" -- {column_comments[col_name]}"
            
            lines.append(col_line)
        
        # Add foreign key information
        if not foreign_keys.empty:
            lines.append("")
            lines.append("Foreign Keys (JOIN Information):")
            
            current_fk = None
            for _, fk in foreign_keys.iterrows():
                fk_name = fk["fk_constraint_name"]
                if fk_name != current_fk:
                    current_fk = fk_name
                    ref_table = fk["referenced_table"]
                    ref_schema = fk["referenced_schema"]
                    lines.append(f"  - {fk_name}: References {ref_schema}.{ref_table}")
                
                lines.append(f"      {fk['fk_column']} -> {fk['referenced_column']}")
        
        return "\n".join(lines)

    def __enter__(self) -> "IBMDB2Connector":
        """Context manager entry - connect to database."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - disconnect from database."""
        self.disconnect()
