"""
Oracle Database Connector Module
================================================================================

A Python module for connecting to Oracle databases and querying table metadata
and data, with results returned as pandas DataFrames for easy analysis.
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
    - Oracle database connection management using SQLAlchemy with connection pooling
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
    oracle.connect(use_pool=True)  # Use connection pooling (default with SQLAlchemy)
    
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
    lib_dir = /path/to/oracle/instantclient  # Optional: path to Oracle Client libraries

DEPENDENCIES
------------
    - sqlalchemy >= 2.0.0
    - oracledb >= 2.0.0 (uses thick mode with Oracle Client libraries)
    - pandas >= 2.0.0
    - Oracle Instant Client libraries (required for thick mode)

Install with: pip install sqlalchemy oracledb pandas

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
_ORACLEDB_IMPORT_ERROR = None
try:
    import oracledb
except ImportError as e:
    oracledb = None  # type: ignore
    _ORACLEDB_IMPORT_ERROR = e

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import QueuePool, NullPool
except ImportError:
    raise ImportError(
        "sqlalchemy package is required. Install it with: pip install sqlalchemy"
    )


class OracleConnector:
    """
    A class to manage Oracle database connections and table operations using SQLAlchemy.
    """

    def __init__(self, config_path: str = "oracle_config.ini"):
        """
        Initialize the Oracle connector with configuration from a file.

        Args:
            config_path: Path to the configuration INI file
        """
        if _ORACLEDB_IMPORT_ERROR is not None:
            raise ImportError(
                "oracledb package is required. Install it with: pip install oracledb"
            ) from _ORACLEDB_IMPORT_ERROR
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.engine: Optional[Engine] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from the INI file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        parser = configparser.ConfigParser()
        parser.read(self.config_path)

        if "oracle" not in parser.sections():
            raise ValueError("Config file must contain an [oracle] section")

        config: Dict[str, Any] = dict(parser["oracle"])

        # Convert port to integer
        config["port"] = int(config.get("port", 1521))

        # Convert pool settings to integers if present
        if "min_connections" in config:
            config["min_connections"] = int(config["min_connections"])
        if "max_connections" in config:
            config["max_connections"] = int(config["max_connections"])

        return config

    def _get_connection_url(self) -> str:
        """Build the SQLAlchemy connection URL for Oracle."""
        username = self.config["username"]
        password = self.config["password"]
        host = self.config["host"]
        port = self.config["port"]
        
        if "service_name" in self.config:
            # Use service_name format
            return f"oracle+oracledb://{username}:{password}@{host}:{port}/?service_name={self.config['service_name']}"
        elif "sid" in self.config:
            # Use SID format
            return f"oracle+oracledb://{username}:{password}@{host}:{port}/{self.config['sid']}"
        else:
            raise ValueError("Config must specify either 'service_name' or 'sid'")

    def connect(self, use_pool: bool = True) -> "OracleConnector":
        """
        Establish a connection to the Oracle database using SQLAlchemy.

        Args:
            use_pool: If True (default), use connection pooling. If False, disable pooling.

        Returns:
            Self for method chaining
        """
        # Initialize Oracle Client in thick mode
        # lib_dir can be specified in config if Oracle Client is not in PATH
        lib_dir = self.config.get("lib_dir")
        try:
            oracledb.init_oracle_client(lib_dir=lib_dir)
        except oracledb.ProgrammingError:
            # Already initialized - ignore
            pass

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
        result = schema or self.config.get("schema") or self.config.get("username")
        if not result:
            raise ValueError("Schema not specified and no default schema or username in config")
        return result

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
            schema: Schema/owner of the table (defaults to config schema or current user)

        Returns:
            DataFrame with column information (name, type, nullable, etc.)
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
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
            schema: Schema/owner of the table

        Returns:
            DataFrame with constraint information
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
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
            schema: Schema/owner of the table

        Returns:
            DataFrame with index information
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
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
        """)

        with self._ensure_engine().connect() as conn:
            df = pd.read_sql(query, conn, params={"table_name": table_name, "schema": resolved_schema})
            return df

    def list_tables(self, schema: Optional[str] = None) -> pd.DataFrame:
        """
        List all tables in a schema.

        Args:
            schema: Schema/owner to list tables from

        Returns:
            DataFrame with table names and metadata
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                table_name,
                num_rows,
                last_analyzed,
                tablespace_name
            FROM all_tables
            WHERE owner = UPPER(:schema)
            ORDER BY table_name
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
            schema: Schema/owner of the table
            columns: List of columns to select (None = all columns)
            where_clause: Optional WHERE clause (without 'WHERE' keyword)
            limit: Maximum number of rows to fetch

        Returns:
            DataFrame with table data
        """
        resolved_schema = self._get_schema(schema)

        # Build column list
        col_str = ", ".join(columns) if columns else "*"

        # Build query
        query = f"SELECT {col_str} FROM {resolved_schema}.{table_name}"

        if where_clause:
            query += f" WHERE {where_clause}"

        if limit:
            # Use ROWNUM for broader Oracle compatibility
            if where_clause:
                query += f" AND ROWNUM <= {limit}"
            else:
                query += f" WHERE ROWNUM <= {limit}"

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
        resolved_schema = self._get_schema(schema)

        # Get table comment
        table_comment_query = text("""
            SELECT comments
            FROM all_tab_comments
            WHERE table_name = UPPER(:table_name)
              AND owner = UPPER(:schema)
        """)

        # Get column comments
        column_comments_query = text("""
            SELECT 
                column_name,
                comments
            FROM all_col_comments
            WHERE table_name = UPPER(:table_name)
              AND owner = UPPER(:schema)
            ORDER BY column_name
        """)

        with self._ensure_engine().connect() as conn:
            table_comment_df = pd.read_sql(
                table_comment_query, conn, params={"table_name": table_name, "schema": resolved_schema}
            )
            column_comments_df = pd.read_sql(
                column_comments_query, conn, params={"table_name": table_name, "schema": resolved_schema}
            )

            # Handle case-insensitive column names (Oracle may return uppercase or lowercase)
            table_comment = None
            if not table_comment_df.empty:
                # Get the comments column regardless of case
                comments_col = None
                for col in table_comment_df.columns:
                    if col.upper() == "COMMENTS":
                        comments_col = col
                        break
                if comments_col and table_comment_df.iloc[0][comments_col]:
                    table_comment = table_comment_df.iloc[0][comments_col]

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

    def get_foreign_keys(
        self, table_name: str, schema: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get foreign key relationships for a table, including referenced table and column information.

        Args:
            table_name: Name of the table
            schema: Schema/owner of the table

        Returns:
            DataFrame with foreign key information including referenced tables and columns
        """
        resolved_schema = self._get_schema(schema)

        query = text("""
            SELECT 
                a.constraint_name AS fk_constraint_name,
                a.column_name AS fk_column,
                a.position AS fk_position,
                c_pk.table_name AS referenced_table,
                c_pk.owner AS referenced_schema,
                b.column_name AS referenced_column
            FROM all_cons_columns a
            JOIN all_constraints c 
                ON a.constraint_name = c.constraint_name 
                AND a.owner = c.owner
            JOIN all_constraints c_pk 
                ON c.r_constraint_name = c_pk.constraint_name
                AND c.r_owner = c_pk.owner
            JOIN all_cons_columns b 
                ON c_pk.constraint_name = b.constraint_name 
                AND c_pk.owner = b.owner
                AND a.position = b.position
            WHERE c.constraint_type = 'R'
              AND a.table_name = UPPER(:table_name)
              AND a.owner = UPPER(:schema)
            ORDER BY a.constraint_name, a.position
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
            schema: Schema/owner of the table

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
                col_name = row.get("COLUMN_NAME") or row.get("column_name")
                comment = row.get("COMMENTS") or row.get("comments")
                if col_name and comment:
                    column_comments[col_name.upper()] = comment
        
        # Start building the essay
        paragraphs: List[str] = []
        
        # Opening paragraph - table introduction
        table_full_name = f"{resolved_schema}.{table_name.upper()}"
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
                col_name = row.get("COLUMN_NAME") or row.get("column_name")
                data_type = row.get("DATA_TYPE") or row.get("data_type")
                nullable = row.get("NULLABLE") or row.get("nullable")
                
                # Build data type description
                data_length = row.get("DATA_LENGTH") or row.get("data_length")
                data_precision = row.get("DATA_PRECISION") or row.get("data_precision")
                data_scale = row.get("DATA_SCALE") or row.get("data_scale")
                
                type_desc = self._get_friendly_type_name(str(data_type), data_length, data_precision, data_scale)
                required_str = "required" if nullable != "Y" else "optional"
                
                col_comment = column_comments.get(col_name.upper() if col_name else "", "")
                
                if col_comment:
                    column_descriptions.append(
                        f"{col_name} ({type_desc}, {required_str}) which {col_comment.lower().rstrip('.')}"
                    )
                else:
                    column_descriptions.append(f"{col_name} ({type_desc}, {required_str})")
            
            num_cols = len(column_descriptions)
            paragraphs.append(
                f"The table contains {num_cols} column{'s' if num_cols != 1 else ''}: "
                f"{', '.join(column_descriptions[:-1])}"
                f"{', and ' + column_descriptions[-1] if len(column_descriptions) > 1 else column_descriptions[0]}."
            )
        
        # Foreign key relationships paragraph
        if not foreign_keys.empty:
            # Group by constraint name for multi-column FKs
            fk_groups: Dict[str, List[Dict[str, Any]]] = {}
            for _, row in foreign_keys.iterrows():
                fk_name = row.get("FK_CONSTRAINT_NAME") or row.get("fk_constraint_name")
                if fk_name is not None:
                    if fk_name not in fk_groups:
                        fk_groups[fk_name] = []
                    fk_groups[fk_name].append(dict(row))
            
            relationship_descriptions = []
            for fk_name, fk_rows in fk_groups.items():
                first_row = fk_rows[0]
                ref_schema = first_row.get("REFERENCED_SCHEMA") or first_row.get("referenced_schema")
                ref_table = first_row.get("REFERENCED_TABLE") or first_row.get("referenced_table")
                
                # Build join condition description
                join_parts = []
                for fk_row in sorted(fk_rows, key=lambda x: x.get("FK_POSITION") or x.get("fk_position") or 0):
                    fk_col = fk_row.get("FK_COLUMN") or fk_row.get("fk_column")
                    ref_col = fk_row.get("REFERENCED_COLUMN") or fk_row.get("referenced_column")
                    join_parts.append(f"{fk_col} to {ref_col}")
                
                join_desc = " and ".join(join_parts)
                relationship_descriptions.append(
                    f"the {ref_schema}.{ref_table} table by matching {join_desc}"
                )
            
            num_rels = len(relationship_descriptions)
            paragraphs.append(
                f"This table can be joined with {', '.join(relationship_descriptions[:-1])}"
                f"{', and ' + relationship_descriptions[-1] if len(relationship_descriptions) > 1 else relationship_descriptions[0]}."
                if num_rels > 1 else
                f"This table can be joined with {relationship_descriptions[0]}."
            )
            
            # Add SQL examples
            sql_examples = []
            for fk_name, fk_rows in fk_groups.items():
                first_row = fk_rows[0]
                ref_schema = first_row.get("REFERENCED_SCHEMA") or first_row.get("referenced_schema")
                ref_table = first_row.get("REFERENCED_TABLE") or first_row.get("referenced_table")
                
                join_conditions = []
                for fk_row in sorted(fk_rows, key=lambda x: x.get("FK_POSITION") or x.get("fk_position") or 0):
                    fk_col = fk_row.get("FK_COLUMN") or fk_row.get("fk_column")
                    ref_col = fk_row.get("REFERENCED_COLUMN") or fk_row.get("referenced_column")
                    join_conditions.append(f"{table_name.upper()}.{fk_col} = {ref_table}.{ref_col}")
                
                sql_examples.append(f"JOIN {ref_schema}.{ref_table} ON {' AND '.join(join_conditions)}")
            
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
        port = self.config.get("port", 1521)
        service_name = self.config.get("service_name")
        sid = self.config.get("sid")
        db_identifier = service_name if service_name else sid
        db_type = "service" if service_name else "SID"
        
        technical_info = (
            f"Technical Information: This data resides in an Oracle Database. "
            f"Connection details: Host: {host}, Port: {port}, {db_type}: {db_identifier}. "
            f"Schema: {resolved_schema}."
        )
        paragraphs.append(technical_info)
        
        return "\n\n".join(paragraphs)

    def _get_friendly_type_name(
        self, data_type: str, data_length: Any, data_precision: Any, data_scale: Any
    ) -> str:
        """Convert Oracle data type to a friendly description."""
        type_map = {
            "VARCHAR2": "text",
            "NVARCHAR2": "unicode text",
            "CHAR": "fixed-length text",
            "NCHAR": "fixed-length unicode text",
            "NUMBER": "number",
            "INTEGER": "integer",
            "FLOAT": "decimal number",
            "DATE": "date",
            "TIMESTAMP": "timestamp",
            "CLOB": "large text",
            "NCLOB": "large unicode text",
            "BLOB": "binary data",
            "RAW": "binary data",
        }
        
        friendly_type = type_map.get(data_type, data_type.lower())
        
        if data_type in ("VARCHAR2", "NVARCHAR2", "CHAR", "NCHAR") and data_length and pd.notna(data_length):
            friendly_type += f" up to {int(data_length)} characters"
        elif data_type == "NUMBER" and data_precision and pd.notna(data_precision):
            if data_scale and pd.notna(data_scale) and int(data_scale) > 0:
                friendly_type = f"decimal with {int(data_precision)} digits and {int(data_scale)} decimal places"
            else:
                friendly_type = f"integer up to {int(data_precision)} digits"
        
        return friendly_type

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
                first_table = tables.iloc[0]["table_name"]
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

    # Example 3: Get human-readable table description
    print("\nExample 3: Human-readable table description")
    print("-" * 50)

    try:
        with OracleConnector("oracle_config.ini") as oracle:
            # Get essay-style description of a table
            description = oracle.get_table_description("EMPLOYEES")
            print("Table Description:")
            print(description)

            # You can also get the foreign keys separately
            print("\n\nForeign Keys DataFrame:")
            fk_df = oracle.get_foreign_keys("EMPLOYEES")
            print(fk_df)

    except FileNotFoundError as e:
        print(f"Config file not found: {e}")
    except Exception as e:
        print(f"Error: {e}")
