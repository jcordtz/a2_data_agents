"""
Azure AI Data Agent
================================================================================

An intelligent AI agent powered by Azure OpenAI that enables natural language
querying of Oracle databases. The agent interprets user questions, generates
appropriate SQL queries, and returns results as pandas DataFrames.

FUNCTIONALITY
-------------
This module provides:
    - Natural language to SQL translation using Azure OpenAI
    - Automatic table discovery and schema understanding
    - Multi-language support with automatic translation (30+ languages)
    - Table capability descriptions in business-friendly language
    - Statistical analysis tools (describe, correlation, groupby, etc.)
    - Conversation memory for context-aware follow-up questions

USAGE
-----
Basic usage with context manager:

    from data_agent import DataAgent

    with DataAgent("agent_config.ini") as agent:
        # Ask questions in natural language
        response = agent.ask("What tables are available?")
        print(response.answer)
        
        # Query data
        response = agent.ask("Show me the top 10 employees by salary")
        print(response.answer)
        if response.data is not None:
            print(response.data)
        
        # Get table descriptions in configured language
        description = agent.describe_table_capabilities("EMPLOYEES")
        print(description.description)

Manual connection management:

    agent = DataAgent("agent_config.ini")
    
    response = agent.ask("How many records are in the ORDERS table?")
    print(response.answer)
    
    # Reset conversation for new context
    agent.reset_conversation()
    
    agent.close()

CONFIGURATION FILE FORMAT (agent_config.ini)
--------------------------------------------
    [azure_openai]
    endpoint = https://your-resource.openai.azure.com/
    api_key = your-api-key
    api_version = 2024-02-15-preview
    deployment_name = gpt-4o

    [oracle]
    host = your-oracle-host
    port = 1521
    service_name = ORCL
    username = your_username
    password = your_password
    schema = your_schema
    country = DK  # Language for responses (DK=Danish, US=English, etc.)

    [agent]
    max_iterations = 10
    temperature = 0.0
    system_prompt = You are a helpful data analyst assistant.

SUPPORTED LANGUAGES
-------------------
Set the 'country' parameter to change response language:
    US/GB (English), DK (Danish), DE (German), FR (French), ES (Spanish),
    NL (Dutch), IT (Italian), PT/BR (Portuguese), JP (Japanese),
    CN/TW (Chinese), KR (Korean), and many more.

DEPENDENCIES
------------
    - openai >= 1.12.0
    - pandas >= 2.0.0
    - oracledb >= 2.0.0

Install with: pip install openai pandas oracledb

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

import json
import configparser
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field

import pandas as pd
from openai import AzureOpenAI

from oracle_connector import OracleConnector


# Country code to language mapping for natural language descriptions
COUNTRY_LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "US": {"language": "English", "locale": "en-US"},
    "GB": {"language": "English", "locale": "en-GB"},
    "DE": {"language": "German", "locale": "de-DE"},
    "AT": {"language": "German", "locale": "de-AT"},
    "CH": {"language": "German", "locale": "de-CH"},
    "FR": {"language": "French", "locale": "fr-FR"},
    "CA": {"language": "French", "locale": "fr-CA"},
    "ES": {"language": "Spanish", "locale": "es-ES"},
    "MX": {"language": "Spanish", "locale": "es-MX"},
    "NL": {"language": "Dutch", "locale": "nl-NL"},
    "BE": {"language": "Dutch", "locale": "nl-BE"},
    "IT": {"language": "Italian", "locale": "it-IT"},
    "PT": {"language": "Portuguese", "locale": "pt-PT"},
    "BR": {"language": "Portuguese", "locale": "pt-BR"},
    "JP": {"language": "Japanese", "locale": "ja-JP"},
    "CN": {"language": "Chinese (Simplified)", "locale": "zh-CN"},
    "TW": {"language": "Chinese (Traditional)", "locale": "zh-TW"},
    "KR": {"language": "Korean", "locale": "ko-KR"},
    "RU": {"language": "Russian", "locale": "ru-RU"},
    "PL": {"language": "Polish", "locale": "pl-PL"},
    "SE": {"language": "Swedish", "locale": "sv-SE"},
    "NO": {"language": "Norwegian", "locale": "no-NO"},
    "DK": {"language": "Danish", "locale": "da-DK"},
    "FI": {"language": "Finnish", "locale": "fi-FI"},
    "TR": {"language": "Turkish", "locale": "tr-TR"},
    "AR": {"language": "Arabic", "locale": "ar-SA"},
    "IN": {"language": "Hindi", "locale": "hi-IN"},
    "TH": {"language": "Thai", "locale": "th-TH"},
    "VN": {"language": "Vietnamese", "locale": "vi-VN"},
    "ID": {"language": "Indonesian", "locale": "id-ID"},
    "GR": {"language": "Greek", "locale": "el-GR"},
    "CZ": {"language": "Czech", "locale": "cs-CZ"},
    "HU": {"language": "Hungarian", "locale": "hu-HU"},
    "RO": {"language": "Romanian", "locale": "ro-RO"},
    "UA": {"language": "Ukrainian", "locale": "uk-UA"},
    "IL": {"language": "Hebrew", "locale": "he-IL"},
}


@dataclass
class AgentResponse:
    """Response from the AI agent."""
    answer: str
    data: Optional[pd.DataFrame] = None
    sql_executed: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class TableDescription:
    """Description of a table's capabilities and content."""
    table_name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    column_descriptions: Dict[str, str] = field(default_factory=dict)
    language: str = "English"
    country_code: str = "US"


class DataAgent:
    """
    AI Agent that can query Oracle databases using natural language.
    Uses Azure OpenAI for understanding queries and generating SQL.
    """

    def __init__(self, config_path: str = "agent_config.ini"):
        """
        Initialize the data agent.

        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.client = self._init_openai_client()
        self.oracle = OracleConnector(config_path)
        self.oracle.connect()
        
        # Define available tools/functions
        self.tools = self._define_tools()
        self.tool_functions = self._map_tool_functions()
        
        # Conversation history
        self.messages: List[Dict[str, Any]] = []
        self._init_system_prompt()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from INI file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        parser = configparser.ConfigParser()
        parser.read(path)

        config = {
            "azure_openai": dict(parser["azure_openai"]),
            "oracle": dict(parser["oracle"]),
            "agent": dict(parser["agent"]),
        }
        return config

    def _init_openai_client(self) -> AzureOpenAI:
        """Initialize the Azure OpenAI client."""
        azure_config = self.config["azure_openai"]
        return AzureOpenAI(
            azure_endpoint=azure_config["endpoint"],
            api_key=azure_config["api_key"],
            api_version=azure_config["api_version"],
        )

    def _get_target_language(self) -> Dict[str, str]:
        """Get the target language based on country code from config."""
        country_code = self.config["oracle"].get("country", "US").upper()
        return COUNTRY_LANGUAGE_MAP.get(
            country_code, 
            {"language": "English", "locale": "en-US"}
        )

    def translate_text(self, text: str, target_language: Optional[str] = None) -> str:
        """
        Translate text to the target language using Azure OpenAI.

        Args:
            text: The text to translate
            target_language: Target language (uses config country if not specified)

        Returns:
            Translated text
        """
        if not target_language:
            lang_info = self._get_target_language()
            target_language = lang_info["language"]

        # Skip translation if already in English and target is English
        if target_language.lower().startswith("english"):
            return text

        try:
            response = self.client.chat.completions.create(
                model=self.config["azure_openai"]["deployment_name"],
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional translator. Translate the following text to {target_language}. "
                                   f"Preserve technical terms and table/column names. Return only the translation."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content or text
        except Exception as e:
            return f"{text}\n\n[Translation error: {str(e)}]"

    def describe_table_capabilities(
        self, 
        table_name: str, 
        schema: Optional[str] = None,
        translate: bool = True
    ) -> TableDescription:
        """
        Generate a natural language description of a table's capabilities and content.

        Args:
            table_name: Name of the table to describe
            schema: Schema/owner of the table
            translate: Whether to translate to the configured language

        Returns:
            TableDescription with detailed information
        """
        # Get table metadata
        structure = self.oracle.get_table_structure(table_name, schema)
        comments = self.oracle.get_table_comments(table_name, schema)
        constraints = self.oracle.get_table_constraints(table_name, schema)

        # Build context for AI description generation
        table_comment = comments.get("table_comment", "No description available")
        column_comments_df = comments.get("column_comments", pd.DataFrame())

        # Prepare column info
        column_info = []
        column_descriptions = {}
        for _, row in structure.iterrows():
            col_name = row["COLUMN_NAME"]
            col_type = row["DATA_TYPE"]
            nullable = "optional" if row["NULLABLE"] == "Y" else "required"
            
            # Get column comment if available
            col_comment = ""
            if not column_comments_df.empty:
                col_row = column_comments_df[column_comments_df["COLUMN_NAME"] == col_name]
                if not col_row.empty and col_row.iloc[0]["COMMENTS"]:
                    col_comment = f" - {col_row.iloc[0]['COMMENTS']}"
                    column_descriptions[col_name] = col_row.iloc[0]["COMMENTS"]
            
            column_info.append(f"  - {col_name} ({col_type}, {nullable}){col_comment}")

        # Identify key columns from constraints
        pk_columns = []
        fk_info = []
        if not constraints.empty:
            pk_rows = constraints[constraints["CONSTRAINT_TYPE"] == "P"]
            pk_columns = pk_rows["COLUMN_NAME"].tolist() if not pk_rows.empty else []
            
            fk_rows = constraints[constraints["CONSTRAINT_TYPE"] == "R"]
            if not fk_rows.empty:
                fk_info = fk_rows[["CONSTRAINT_NAME", "COLUMN_NAME"]].to_dict("records")

        # Generate description using Azure OpenAI
        prompt = f"""
Analyze this Oracle database table and provide a clear, natural language description of:
1. What this table stores and its purpose
2. What capabilities/queries it enables
3. How it might relate to other data

Table: {table_name}
Table Description: {table_comment or 'Not provided'}
Primary Key Columns: {', '.join(pk_columns) if pk_columns else 'None identified'}
Foreign Keys: {json.dumps(fk_info) if fk_info else 'None'}

Columns:
{chr(10).join(column_info)}

Provide a business-friendly description that a non-technical user could understand.
Include specific examples of questions that could be answered using this table.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.config["azure_openai"]["deployment_name"],
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data analyst who explains database tables in clear, business-friendly language."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
            )
            description = response.choices[0].message.content or "Unable to generate description."
        except Exception as e:
            description = f"Error generating description: {str(e)}"

        # Extract capabilities (questions that can be answered)
        capabilities = self._extract_capabilities(table_name, structure, constraints)

        # Get language info
        lang_info = self._get_target_language()
        
        # Translate if needed and requested
        if translate and not lang_info["language"].lower().startswith("english"):
            description = self.translate_text(description, lang_info["language"])
            capabilities = [self.translate_text(cap, lang_info["language"]) for cap in capabilities]
            column_descriptions = {
                k: self.translate_text(v, lang_info["language"]) 
                for k, v in column_descriptions.items()
            }

        return TableDescription(
            table_name=table_name,
            description=description,
            capabilities=capabilities,
            column_descriptions=column_descriptions,
            language=lang_info["language"],
            country_code=self.config["oracle"].get("country", "US").upper()
        )

    def _extract_capabilities(
        self, 
        table_name: str, 
        structure: pd.DataFrame, 
        constraints: pd.DataFrame
    ) -> List[str]:
        """
        Extract a list of capabilities/questions that can be answered using this table.
        """
        capabilities = []
        
        # Basic capabilities based on columns
        capabilities.append(f"Query and filter records from {table_name}")
        
        # Check for common column patterns
        column_names = structure["COLUMN_NAME"].str.upper().tolist()
        
        if any("DATE" in col or "TIME" in col for col in column_names):
            capabilities.append("Perform time-based analysis and filtering")
        
        if any("AMOUNT" in col or "PRICE" in col or "COST" in col or "SALARY" in col for col in column_names):
            capabilities.append("Calculate totals, averages, and financial summaries")
        
        if any("STATUS" in col or "STATE" in col or "TYPE" in col for col in column_names):
            capabilities.append("Group and categorize records by status or type")
        
        if any("NAME" in col or "DESCRIPTION" in col for col in column_names):
            capabilities.append("Search and filter by name or description")
        
        if any("ID" in col for col in column_names):
            capabilities.append("Look up specific records by identifier")
        
        # Check for foreign keys indicating relationships
        if not constraints.empty:
            fk_count = len(constraints[constraints["CONSTRAINT_TYPE"] == "R"])
            if fk_count > 0:
                capabilities.append(f"Join with {fk_count} related table(s) for comprehensive analysis")
        
        return capabilities

    def _init_system_prompt(self) -> None:
        """Initialize the system prompt with database context."""
        # Get available tables for context
        try:
            tables_df = self.oracle.list_tables()
            tables_list = tables_df["TABLE_NAME"].tolist() if not tables_df.empty else []
            tables_context = f"Available tables: {', '.join(tables_list)}" if tables_list else "No tables found."
        except Exception:
            tables_context = "Unable to retrieve table list."

        system_prompt = f"""
{self.config['agent'].get('system_prompt', 'You are a helpful data analyst assistant.')}

You have access to an Oracle database with the following context:
{tables_context}

You can use the available tools to:
1. List tables in the database
2. Get the structure of a specific table
3. Execute SQL queries
4. Load table data into a DataFrame

When the user asks a question about data:
1. First understand what tables and columns are relevant
2. Use get_table_structure to understand the schema
3. Write and execute appropriate SQL queries
4. Explain the results clearly

Always validate your SQL before executing. Use parameterized queries when possible.
For large result sets, consider using LIMIT/FETCH FIRST clauses.
"""
        self.messages = [{"role": "system", "content": system_prompt}]

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define the tools available to the AI agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_tables",
                    "description": "List all tables available in the database schema",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schema": {
                                "type": "string",
                                "description": "Optional schema name. Uses default if not specified.",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_table_structure",
                    "description": "Get the column structure and metadata of a specific table",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe",
                            },
                            "schema": {
                                "type": "string",
                                "description": "Optional schema name",
                            },
                        },
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_query",
                    "description": "Execute a SQL SELECT query and return results. Only SELECT statements are allowed for safety.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The SQL SELECT query to execute",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_table_data",
                    "description": "Load data from a table with optional filtering",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to query",
                            },
                            "columns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of columns to select. All columns if not specified.",
                            },
                            "where_clause": {
                                "type": "string",
                                "description": "WHERE clause without the WHERE keyword",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of rows to return",
                            },
                        },
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_table_constraints",
                    "description": "Get the constraints (primary keys, foreign keys, etc.) of a table",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table",
                            },
                        },
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_dataframe",
                    "description": "Perform statistical analysis on query results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL query to get data for analysis",
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["describe", "correlation", "value_counts", "groupby"],
                                "description": "Type of analysis to perform",
                            },
                            "column": {
                                "type": "string",
                                "description": "Column to analyze (for value_counts)",
                            },
                            "group_column": {
                                "type": "string",
                                "description": "Column to group by (for groupby analysis)",
                            },
                            "agg_column": {
                                "type": "string",
                                "description": "Column to aggregate (for groupby analysis)",
                            },
                            "agg_func": {
                                "type": "string",
                                "enum": ["sum", "mean", "count", "min", "max"],
                                "description": "Aggregation function (for groupby analysis)",
                            },
                        },
                        "required": ["query", "analysis_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "describe_table",
                    "description": "Get a natural language description of a table's purpose, capabilities, and content. Returns a business-friendly explanation of what the table stores and what questions can be answered using it. The description is automatically translated to the language configured for the user's country.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe",
                            },
                            "schema": {
                                "type": "string",
                                "description": "Optional schema name",
                            },
                        },
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "translate_response",
                    "description": "Translate any text to the user's configured language based on their country setting",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to translate",
                            },
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_table_comments",
                    "description": "Get the Oracle database comments/descriptions for a table and its columns",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table",
                            },
                            "schema": {
                                "type": "string",
                                "description": "Optional schema name",
                            },
                        },
                        "required": ["table_name"],
                    },
                },
            },
        ]

    def _map_tool_functions(self) -> Dict[str, Callable]:
        """Map tool names to their implementation functions."""
        return {
            "list_tables": self._tool_list_tables,
            "get_table_structure": self._tool_get_table_structure,
            "execute_query": self._tool_execute_query,
            "get_table_data": self._tool_get_table_data,
            "get_table_constraints": self._tool_get_table_constraints,
            "analyze_dataframe": self._tool_analyze_dataframe,
            "describe_table": self._tool_describe_table,
            "translate_response": self._tool_translate_response,
            "get_table_comments": self._tool_get_table_comments,
        }

    def _tool_list_tables(self, schema: Optional[str] = None) -> str:
        """Tool: List all tables."""
        try:
            df = self.oracle.list_tables(schema)
            if df.empty:
                return "No tables found in the schema."
            return df.to_string()
        except Exception as e:
            return f"Error listing tables: {str(e)}"

    def _tool_get_table_structure(
        self, table_name: str, schema: Optional[str] = None
    ) -> str:
        """Tool: Get table structure."""
        try:
            df = self.oracle.get_table_structure(table_name, schema)
            if df.empty:
                return f"Table '{table_name}' not found or has no columns."
            return df.to_string()
        except Exception as e:
            return f"Error getting table structure: {str(e)}"

    def _tool_execute_query(self, query: str) -> str:
        """Tool: Execute a SQL query (SELECT only for safety)."""
        # Safety check - only allow SELECT statements
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
            return "Error: Only SELECT queries are allowed for safety. Use SELECT or WITH clauses."

        try:
            df = self.oracle.query_to_dataframe(query)
            self._last_result_df = df  # Store for potential further analysis
            
            if df.empty:
                return "Query executed successfully but returned no results."
            
            # Limit output for large results
            if len(df) > 100:
                return f"Query returned {len(df)} rows. Showing first 100:\n{df.head(100).to_string()}"
            return df.to_string()
        except Exception as e:
            return f"Error executing query: {str(e)}"

    def _tool_get_table_data(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where_clause: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Tool: Get data from a table."""
        try:
            df = self.oracle.table_to_dataframe(
                table_name, columns=columns, where_clause=where_clause, limit=limit or 100
            )
            self._last_result_df = df
            
            if df.empty:
                return "No data found matching the criteria."
            return df.to_string()
        except Exception as e:
            return f"Error getting table data: {str(e)}"

    def _tool_get_table_constraints(self, table_name: str) -> str:
        """Tool: Get table constraints."""
        try:
            df = self.oracle.get_table_constraints(table_name)
            if df.empty:
                return f"No constraints found for table '{table_name}'."
            return df.to_string()
        except Exception as e:
            return f"Error getting constraints: {str(e)}"

    def _tool_describe_table(
        self, table_name: str, schema: Optional[str] = None
    ) -> str:
        """Tool: Get natural language description of a table."""
        try:
            description = self.describe_table_capabilities(table_name, schema, translate=True)
            
            result = f"""## {description.table_name} - Table Description

**Language:** {description.language} ({description.country_code})

### Overview
{description.description}

### Capabilities
This table enables you to:
"""
            for cap in description.capabilities:
                result += f"- {cap}\n"
            
            if description.column_descriptions:
                result += "\n### Column Details\n"
                for col, desc in description.column_descriptions.items():
                    result += f"- **{col}**: {desc}\n"
            
            return result
        except Exception as e:
            return f"Error describing table: {str(e)}"

    def _tool_translate_response(self, text: str) -> str:
        """Tool: Translate text to user's configured language."""
        try:
            lang_info = self._get_target_language()
            translated = self.translate_text(text, lang_info["language"])
            return f"[Translated to {lang_info['language']}]\n\n{translated}"
        except Exception as e:
            return f"Error translating: {str(e)}"

    def _tool_get_table_comments(
        self, table_name: str, schema: Optional[str] = None
    ) -> str:
        """Tool: Get table and column comments from Oracle."""
        try:
            comments = self.oracle.get_table_comments(table_name, schema)
            
            result = f"Table: {table_name}\n"
            result += f"Table Comment: {comments['table_comment'] or 'No comment defined'}\n\n"
            result += "Column Comments:\n"
            
            col_comments = comments["column_comments"]
            if col_comments.empty:
                result += "No column comments defined.\n"
            else:
                for _, row in col_comments.iterrows():
                    comment = row["COMMENTS"] or "No comment"
                    result += f"  - {row['COLUMN_NAME']}: {comment}\n"
            
            return result
        except Exception as e:
            return f"Error getting table comments: {str(e)}"

    def _tool_analyze_dataframe(
        self,
        query: str,
        analysis_type: str,
        column: Optional[str] = None,
        group_column: Optional[str] = None,
        agg_column: Optional[str] = None,
        agg_func: str = "count",
    ) -> str:
        """Tool: Analyze data from a query."""
        try:
            df = self.oracle.query_to_dataframe(query)
            
            if df.empty:
                return "No data to analyze."

            if analysis_type == "describe":
                return df.describe().to_string()
            
            elif analysis_type == "correlation":
                numeric_cols = df.select_dtypes(include=["number"]).columns
                if len(numeric_cols) < 2:
                    return "Need at least 2 numeric columns for correlation."
                return df[numeric_cols].corr().to_string()
            
            elif analysis_type == "value_counts":
                if not column:
                    return "Column name required for value_counts."
                if column not in df.columns:
                    return f"Column '{column}' not found. Available: {list(df.columns)}"
                return df[column].value_counts().to_string()
            
            elif analysis_type == "groupby":
                if not group_column or not agg_column:
                    return "group_column and agg_column are required for groupby."
                result = df.groupby(group_column)[agg_column].agg(agg_func)
                return result.to_string()
            
            else:
                return f"Unknown analysis type: {analysis_type}"

        except Exception as e:
            return f"Error in analysis: {str(e)}"

    def _execute_tool_call(self, tool_call: Any) -> str:
        """Execute a single tool call and return the result."""
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        if function_name not in self.tool_functions:
            return f"Unknown tool: {function_name}"

        tool_func = self.tool_functions[function_name]
        return tool_func(**function_args)

    def ask(self, question: str) -> AgentResponse:
        """
        Ask the agent a question about the data.

        Args:
            question: Natural language question

        Returns:
            AgentResponse with the answer and any data
        """
        self.messages.append({"role": "user", "content": question})
        
        tool_calls_made = []
        sql_executed = None
        
        max_iterations = int(self.config["agent"].get("max_iterations", 10))
        
        for _ in range(max_iterations):
            response = self.client.chat.completions.create(
                model=self.config["azure_openai"]["deployment_name"],
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=float(self.config["agent"].get("temperature", 0.0)),
            )

            message = response.choices[0].message

            # If no tool calls, we have the final answer
            if not message.tool_calls:
                self.messages.append({"role": "assistant", "content": message.content})
                return AgentResponse(
                    answer=message.content or "I couldn't generate a response.",
                    data=getattr(self, "_last_result_df", None),
                    sql_executed=sql_executed,
                    tool_calls=tool_calls_made if tool_calls_made else None,
                )

            # Process tool calls
            self.messages.append(message)

            for tool_call in message.tool_calls:
                tool_result = self._execute_tool_call(tool_call)
                
                # Track tool calls and SQL
                call_info = {
                    "tool": tool_call.function.name,
                    "args": json.loads(tool_call.function.arguments),
                }
                tool_calls_made.append(call_info)
                
                if tool_call.function.name == "execute_query":
                    sql_executed = json.loads(tool_call.function.arguments).get("query")

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

        return AgentResponse(
            answer="I reached the maximum number of iterations without completing the task.",
            tool_calls=tool_calls_made,
        )

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self._init_system_prompt()
        self._last_result_df = None

    def close(self) -> None:
        """Clean up resources."""
        self.oracle.disconnect()

    def __enter__(self) -> "DataAgent":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    print("Data Agent Example")
    print("=" * 60)

    try:
        with DataAgent("agent_config.ini") as agent:
            # Example questions
            questions = [
                "What tables are available in the database?",
                "Show me the structure of the EMPLOYEES table",
                "How many employees are there in each department?",
                "What is the average salary by job title?",
            ]

            for question in questions:
                print(f"\nQ: {question}")
                print("-" * 40)
                response = agent.ask(question)
                print(f"A: {response.answer}")
                
                if response.sql_executed:
                    print(f"\nSQL: {response.sql_executed}")
                
                if response.data is not None:
                    print(f"\nData shape: {response.data.shape}")

    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Error: {e}")
