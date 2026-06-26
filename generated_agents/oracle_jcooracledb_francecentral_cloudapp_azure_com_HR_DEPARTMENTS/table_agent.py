"""
Table Agent for HR.DEPARTMENTS
================================================================================

An AI-powered agent specialized for querying the HR.DEPARTMENTS table.
This agent understands the table structure and can answer natural language
questions about the data.

DATABASE TYPE: ORACLE

TABLE DESCRIPTION:
The HR.DEPARTMENTS table departments table that shows details of departments where employees
work. contains 27 rows; references with locations, employees, and job_history tables. This table is located in the HR schema.

The table contains 4 columns: DEPARTMENT_ID (integer up to 4 digits, required) which primary key column of departments table, DEPARTMENT_NAME (text up to 30 characters, required) which a not null column that shows name of a department. administration,
marketing, purchasing, human resources, shipping, it, executive, public
relations, sales, finance, and accounting. , MANAGER_ID (integer up to 6 digits, optional) which manager_id of a department. foreign key to employee_id column of employees table. the manager_id column of the employee table references this column, and LOCATION_ID (integer up to 4 digits, optional) which location id where a department is located. foreign key to location_id column of locations table.

This table can be joined with the HR.LOCATIONS table by matching LOCATION_ID to LOCATION_ID, and the HR.EMPLOYEES table by matching MANAGER_ID to EMPLOYEE_ID.

To perform these joins in SQL, you can use: JOIN HR.LOCATIONS ON DEPARTMENTS.LOCATION_ID = LOCATIONS.LOCATION_ID; JOIN HR.EMPLOYEES ON DEPARTMENTS.MANAGER_ID = EMPLOYEES.EMPLOYEE_ID.

Technical Information: This data resides in an Oracle Database. Connection details: Host: jcooracledb.francecentral.cloudapp.azure.com, Port: 1521, service: XE. Schema: HR.

AVAILABLE COLUMNS:
    DEPARTMENT_ID, DEPARTMENT_NAME, MANAGER_ID, LOCATION_ID
"""

import configparser
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from openai import AzureOpenAI

from oracle_connector import OracleConnector


@dataclass
class AgentResponse:
    """Response from the table agent."""
    answer: str
    sql_executed: Optional[str] = None
    data: Optional[pd.DataFrame] = None
    error: Optional[str] = None


class TableAgent:
    """
    AI Agent specialized for the HR.DEPARTMENTS table.
    Database Type: ORACLE
    """
    
    # Table metadata (embedded at generation time)
    SCHEMA = "HR"
    TABLE_NAME = "DEPARTMENTS"
    FULL_TABLE_NAME = "HR.DEPARTMENTS"
    DATABASE_TYPE = "oracle"
    SQL_SYNTAX = "Oracle SQL"
    TABLE_DESCRIPTION = """The HR.DEPARTMENTS table departments table that shows details of departments where employees
work. contains 27 rows; references with locations, employees, and job_history tables. This table is located in the HR schema.

The table contains 4 columns: DEPARTMENT_ID (integer up to 4 digits, required) which primary key column of departments table, DEPARTMENT_NAME (text up to 30 characters, required) which a not null column that shows name of a department. administration,
marketing, purchasing, human resources, shipping, it, executive, public
relations, sales, finance, and accounting. , MANAGER_ID (integer up to 6 digits, optional) which manager_id of a department. foreign key to employee_id column of employees table. the manager_id column of the employee table references this column, and LOCATION_ID (integer up to 4 digits, optional) which location id where a department is located. foreign key to location_id column of locations table.

This table can be joined with the HR.LOCATIONS table by matching LOCATION_ID to LOCATION_ID, and the HR.EMPLOYEES table by matching MANAGER_ID to EMPLOYEE_ID.

To perform these joins in SQL, you can use: JOIN HR.LOCATIONS ON DEPARTMENTS.LOCATION_ID = LOCATIONS.LOCATION_ID; JOIN HR.EMPLOYEES ON DEPARTMENTS.MANAGER_ID = EMPLOYEES.EMPLOYEE_ID.

Technical Information: This data resides in an Oracle Database. Connection details: Host: jcooracledb.francecentral.cloudapp.azure.com, Port: 1521, service: XE. Schema: HR."""
    COLUMNS = ["DEPARTMENT_ID", "DEPARTMENT_NAME", "MANAGER_ID", "LOCATION_ID"]
    
    def __init__(self, config_path: str = "agent_config.ini"):
        """Initialize the table agent."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.db = OracleConnector(config_path)
        self.db.connect()
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=self.config.get("api_key") or os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version=self.config.get("api_version", "2024-02-15-preview"),
            azure_endpoint=self.config.get("endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = self.config.get("deployment_name") or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
        
        # System prompt
        self.system_prompt = self._build_system_prompt()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from INI file."""
        config = {}
        
        if self.config_path.exists():
            parser = configparser.ConfigParser()
            parser.read(self.config_path)
            
            if "azure_openai" in parser.sections():
                config.update(dict(parser["azure_openai"]))
            if "oracle" in parser.sections():
                config.update(dict(parser["oracle"]))
            if "agent" in parser.sections():
                config.update(dict(parser["agent"]))
        
        return config
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with table context."""
        return f"""You are an AI data analyst assistant specialized in querying the {self.FULL_TABLE_NAME} table.

DATABASE TYPE: {self.DATABASE_TYPE.upper()}

TABLE INFORMATION:
{self.TABLE_DESCRIPTION}

YOUR CAPABILITIES:
1. Answer questions about the data in this table
2. Generate SQL queries to retrieve data
3. Explain the table structure and relationships
4. Provide statistical analysis of the data

RULES:
1. Only query the {self.FULL_TABLE_NAME} table and its related tables via joins
2. Always use proper {self.SQL_SYNTAX} syntax
3. Limit results to 100 rows unless specifically asked for more
4. Be concise but informative in your responses
5. If you cannot answer a question with the available data, explain why

When you need to execute SQL, respond with a JSON object:
{"action": "execute_sql", "sql": "YOUR SQL QUERY HERE"}

When you have the final answer, just respond normally with text."""
    
    def ask(self, question: str) -> AgentResponse:
        """
        Ask a question about the table.
        
        Args:
            question: Natural language question
            
        Returns:
            AgentResponse with answer, SQL, and data
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": question})
        
        # Build messages for API call
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history
        ]
        
        try:
            # Get response from Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=float(self.config.get("temperature", 0.0)),
                max_tokens=2000
            )
            
            assistant_message = response.choices[0].message.content
            
            # Check if response contains SQL to execute
            if '"action": "execute_sql"' in assistant_message or "'action': 'execute_sql'" in assistant_message:
                return self._handle_sql_action(assistant_message)
            
            # Regular text response
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return AgentResponse(answer=assistant_message)
            
        except Exception as e:
            return AgentResponse(
                answer=f"Error processing request: {str(e)}",
                error=str(e)
            )
    
    def _handle_sql_action(self, response: str) -> AgentResponse:
        """Handle SQL execution action from the model."""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response)
            
            if not json_match:
                return AgentResponse(answer=response)
            
            action_data = json.loads(json_match.group())
            sql = action_data.get("sql", "")
            
            if not sql:
                return AgentResponse(answer=response)
            
            # Execute SQL
            df = self.db.query_to_dataframe(sql)
            
            # Generate summary
            summary = self._summarize_results(df, sql)
            
            self.conversation_history.append({
                "role": "assistant",
                "content": f"Executed SQL: {sql}\n\nResults: {summary}"
            })
            
            return AgentResponse(
                answer=summary,
                sql_executed=sql,
                data=df
            )
            
        except Exception as e:
            error_msg = f"Error executing SQL: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return AgentResponse(answer=error_msg, error=str(e))
    
    def _summarize_results(self, df: pd.DataFrame, sql: str) -> str:
        """Generate a summary of query results."""
        if df.empty:
            return "The query returned no results."
        
        summary_parts = [f"Query returned {len(df)} row(s)."]
        
        if len(df) <= 10:
            summary_parts.append(f"\n\nResults:\n{df.to_string()}")
        else:
            summary_parts.append(f"\n\nFirst 10 rows:\n{df.head(10).to_string()}")
        
        return "\n".join(summary_parts)
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get table structure and description."""
        structure = self.db.get_table_structure(self.TABLE_NAME, self.SCHEMA)
        
        return {
            "schema": self.SCHEMA,
            "table_name": self.TABLE_NAME,
            "description": self.TABLE_DESCRIPTION,
            "columns": self.COLUMNS,
            "structure": structure.to_dict(orient="records") if not structure.empty else []
        }
    
    def reset_conversation(self) -> None:
        """Reset conversation history."""
        self.conversation_history = []
    
    def close(self) -> None:
        """Close database connection."""
        self.db.disconnect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
