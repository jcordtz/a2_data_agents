"""
Oracle Database Connector Module
================================================================================

A Python module for connecting to Oracle databases and querying table metadata
and data, with results returned as pandas DataFrames for easy analysis.

FUNCTIONALITY
-------------
This module provides:
    - Oracle database connection management (single connections and connection pools)
    - Table structure/schema querying (columns, data types, constraints, indexes)
    - Table and column comment retrieval from Oracle metadata
    - SQL query execution with DataFrame results
    - Table data loading with filtering and pagination

USAGE
-----
Basic usage with context manager:

    from oracle_connector import OracleConnector

    with OracleConnector("oracle_config.ini") as oracle:
        # List all tables
        tables = oracle.list_tables()
        
        # Get table structure
        structure = oracle.get_table_structure("EMPLOYEES")
        
        # Query data into DataFrame
        df = oracle.table_to_dataframe("EMPLOYEES", limit=100)
        
        # Execute custom SQL
        result = oracle.query_to_dataframe("SELECT * FROM EMPLOYEES WHERE SALARY > 50000")

Manual connection management:

    oracle = OracleConnector("oracle_config.ini")
    oracle.connect(use_pool=True)  # Use connection pooling
    
    # ... perform operations ...
    
    oracle.disconnect()

CONFIGURATION FILE FORMAT (oracle_config.ini)
---------------------------------------------
    [oracle]
    host = localhost
    port = 1521
    service_name = ORCL
    username = your_username
    password = your_password
    schema = your_schema
    country = DK

DEPENDENCIES
------------
    - oracledb >= 2.0.0
    - pandas >= 2.0.0

Install with: pip install oracledb pandas

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

try:
    import oracledb
except ImportError:
    raise ImportError(
        "oracledb package is required. Install it with: pip install oracledb"
    )


class OracleConnector:
    """
    A class to manage Oracle database connections and table operations.
    """

    def __init__(self, config_path: str = "oracle_config.ini"):
        """
        Initialize the Oracle connector with configuration from a file.

        Args:
            config_path: Path to the configuration INI file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.connection: Optional[oracledb.Connection] = None
        self.pool: Optional[oracledb.ConnectionPool] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the INI file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        parser = configparser.ConfigParser()
        parser.read(self.config_path)

        if "oracle" not in parser.sections():
            raise ValueError("Config file must contain an [oracle] section")

        config = dict(parser["oracle"])

        # Convert port to integer
        config["port"] = int(config.get("port", 1521))

        # Convert pool settings to integers if present
        if "min_connections" in config:
            config["min_connections"] = int(config["min_connections"])
        if "max_connections" in config:
            config["max_connections"] = int(config["max_connections"])

        return config

    def _get_dsn(self) -> str:
        """Build the Oracle DSN (Data Source Name) string."""
        if "service_name" in self.config:
            return oracledb.makedsn(
                host=self.config["host"],
                port=self.config["port"],
                service_name=self.config["service_name"],
            )
        elif "sid" in self.config:
            return oracledb.makedsn(
                host=self.config["host"],
                port=self.config["port"],
                sid=self.config["sid"],
            )
        else:
            raise ValueError("Config must specify either 'service_name' or 'sid'")

    def connect(self, use_pool: bool = False) -> "OracleConnector":
        """
        Establish a connection to the Oracle database.

        Args:
            use_pool: If True, create a connection pool instead of single connection

        Returns:
            Self for method chaining
        """
        dsn = self._get_dsn()

        if use_pool:
            self.pool = oracledb.create_pool(
                user=self.config["username"],
                password=self.config["password"],
                dsn=dsn,
                min=self.config.get("min_connections", 1),
                max=self.config.get("max_connections", 5),
            )
        else:
            self.connection = oracledb.connect(
                user=self.config["username"],
                password=self.config["password"],
                dsn=dsn,
            )

        return self

    def get_connection(self) -> oracledb.Connection:
        """Get a database connection (from pool or direct)."""
        if self.pool:
            return self.pool.acquire()
        elif self.connection:
            return self.connection
        else:
            raise ConnectionError("Not connected. Call connect() first.")

    def disconnect(self) -> None:
        """Close the database connection or pool."""
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.pool:
            self.pool.close()
            self.pool = None

    def get_table_structure(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query and return the structure of a table as a DataFrame.

        Args:
            table_name: Name of the table to describe
            schema: Schema/owner of the table (defaults to config schema or current user)

        Returns:
            DataFrame with column information (name, type, nullable, etc.)
        """
        schema = schema or self.config.get("schema") or self.config["username"]

        query = """
            SELECT 
                column_name,
                data_type,
                data_length,
                data_precision,
                data_scale,
                nullable,
                data_default,
                column_id
            FROM all_tab_columns
            WHERE table_name = UPPER(:table_name)
              AND owner = UPPER(:schema)
            ORDER BY column_id
        """

        conn = self.get_connection()
        try:
            df = pd.read_sql(
                query, conn, params={"table_name": table_name, "schema": schema}
            )
            return df
        finally:
            if self.pool:
                self.pool.release(conn)

    def get_table_constraints(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query and return the constraints of a table as a DataFrame.

        Args:
            table_name: Name of the table
            schema: Schema/owner of the table

        Returns:
            DataFrame with constraint information
        """
        schema = schema or self.config.get("schema") or self.config["username"]

        query = """
            SELECT 
                c.constraint_name,
                c.constraint_type,
                c.status,
                cc.column_name,
                cc.position
            FROM all_constraints c
            JOIN all_cons_columns cc 
                ON c.constraint_name = cc.constraint_name 
                AND c.owner = cc.owner
            WHERE c.table_name = UPPER(:table_name)
              AND c.owner = UPPER(:schema)
            ORDER BY c.constraint_name, cc.position
        """

        conn = self.get_connection()
        try:
            df = pd.read_sql(
                query, conn, params={"table_name": table_name, "schema": schema}
            )
            return df
        finally:
            if self.pool:
                self.pool.release(conn)

    def get_table_indexes(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query and return the indexes of a table as a DataFrame.

        Args:
            table_name: Name of the table
            schema: Schema/owner of the table

        Returns:
            DataFrame with index information
        """
        schema = schema or self.config.get("schema") or self.config["username"]

        query = """
            SELECT 
                i.index_name,
                i.index_type,
                i.uniqueness,
                ic.column_name,
                ic.column_position
            FROM all_indexes i
            JOIN all_ind_columns ic 
                ON i.index_name = ic.index_name 
                AND i.owner = ic.index_owner
            WHERE i.table_name = UPPER(:table_name)
              AND i.owner = UPPER(:schema)
            ORDER BY i.index_name, ic.column_position
        """

        conn = self.get_connection()
        try:
            df = pd.read_sql(
                query, conn, params={"table_name": table_name, "schema": schema}
            )
            return df
        finally:
            if self.pool:
                self.pool.release(conn)

    def list_tables(self, schema: Optional[str] = None) -> pd.DataFrame:
        """
        List all tables in a schema.

        Args:
            schema: Schema/owner to list tables from

        Returns:
            DataFrame with table names and metadata
        """
        schema = schema or self.config.get("schema") or self.config["username"]

        query = """
            SELECT 
                table_name,
                num_rows,
                last_analyzed,
                tablespace_name
            FROM all_tables
            WHERE owner = UPPER(:schema)
            ORDER BY table_name
        """

        conn = self.get_connection()
        try:
            df = pd.read_sql(query, conn, params={"schema": schema})
            return df
        finally:
            if self.pool:
                self.pool.release(conn)

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
        conn = self.get_connection()
        try:
            df = pd.read_sql(query, conn, params=params or {})
            return df
        finally:
            if self.pool:
                self.pool.release(conn)

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
            schema: Schema/owner of the table
            columns: List of columns to select (None = all columns)
            where_clause: Optional WHERE clause (without 'WHERE' keyword)
            limit: Maximum number of rows to fetch

        Returns:
            DataFrame with table data
        """
        schema = schema or self.config.get("schema") or self.config["username"]

        # Build column list
        col_str = ", ".join(columns) if columns else "*"

        # Build query
        query = f"SELECT {col_str} FROM {schema}.{table_name}"

        if where_clause:
            query += f" WHERE {where_clause}"

        if limit:
            query += f" FETCH FIRST {limit} ROWS ONLY"

        return self.query_to_dataframe(query)

    def get_table_comments(
        self, table_name: str, schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get table and column comments/descriptions from Oracle metadata.

        Args:
            table_name: Name of the table
            schema: Schema/owner of the table

        Returns:
            Dictionary with 'table_comment' and 'column_comments' DataFrame
        """
        schema = schema or self.config.get("schema") or self.config["username"]

        # Get table comment
        table_comment_query = """
            SELECT comments
            FROM all_tab_comments
            WHERE table_name = UPPER(:table_name)
              AND owner = UPPER(:schema)
        """

        # Get column comments
        column_comments_query = """
            SELECT 
                column_name,
                comments
            FROM all_col_comments
            WHERE table_name = UPPER(:table_name)
              AND owner = UPPER(:schema)
            ORDER BY column_name
        """

        conn = self.get_connection()
        try:
            table_comment_df = pd.read_sql(
                table_comment_query, conn, params={"table_name": table_name, "schema": schema}
            )
            column_comments_df = pd.read_sql(
                column_comments_query, conn, params={"table_name": table_name, "schema": schema}
            )

            table_comment = (
                table_comment_df.iloc[0]["COMMENTS"]
                if not table_comment_df.empty and table_comment_df.iloc[0]["COMMENTS"]
                else None
            )

            return {
                "table_comment": table_comment,
                "column_comments": column_comments_df,
            }
        finally:
            if self.pool:
                self.pool.release(conn)

    def get_full_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive table information including structure, constraints, indexes, and comments.

        Args:
            table_name: Name of the table
            schema: Schema/owner of the table

        Returns:
            Dictionary with 'structure', 'constraints', 'indexes', and 'comments' DataFrames
        """
        return {
            "structure": self.get_table_structure(table_name, schema),
            "constraints": self.get_table_constraints(table_name, schema),
            "indexes": self.get_table_indexes(table_name, schema),
            "comments": self.get_table_comments(table_name, schema),
        }

    def __enter__(self) -> "OracleConnector":
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
        with OracleConnector("oracle_config.ini") as oracle:
            # List all tables
            tables = oracle.list_tables()
            print("Tables in schema:")
            print(tables)

            # Get structure of a specific table
            if not tables.empty:
                first_table = tables.iloc[0]["TABLE_NAME"]
                structure = oracle.get_table_structure(first_table)
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
        oracle = OracleConnector("oracle_config.ini")
        oracle.connect()

        # Query specific table structure
        structure_df = oracle.get_table_structure("EMPLOYEES")
        print("EMPLOYEES table structure:")
        print(structure_df)

        # Load table data into DataFrame for querying
        employees_df = oracle.table_to_dataframe(
            "EMPLOYEES", columns=["EMPLOYEE_ID", "FIRST_NAME", "LAST_NAME"], limit=10
        )
        print("\nFirst 10 employees:")
        print(employees_df)

        # Now you can use pandas to query the DataFrame
        if not employees_df.empty:
            # Example pandas operations
            print("\nQuerying the DataFrame:")
            print(employees_df.describe())

        oracle.disconnect()

    except FileNotFoundError as e:
        print(f"Config file not found: {e}")
    except Exception as e:
        print(f"Error: {e}")
