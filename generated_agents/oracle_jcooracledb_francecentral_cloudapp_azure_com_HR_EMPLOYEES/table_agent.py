"""
Table Agent for HR.EMPLOYEES
================================================================================

An AI-powered agent specialized for querying the HR.EMPLOYEES table.
This agent understands the table structure and can answer natural language
questions about the data.

DATABASE TYPE: ORACLE

TABLE DESCRIPTION:
The HR.EMPLOYEES table employees table. contains 107 rows. references with departments,
jobs, job_history tables. contains a self reference. This table is located in the HR schema.

The table contains 11 columns: EMPLOYEE_ID (integer up to 6 digits, required) which primary key of employees table, FIRST_NAME (text up to 20 characters, optional) which first name of the employee. a not null column, LAST_NAME (text up to 25 characters, required) which last name of the employee. a not null column, EMAIL (text up to 25 characters, required) which email id of the employee, PHONE_NUMBER (text up to 20 characters, optional) which phone number of the employee; includes country code and area code, HIRE_DATE (date, required) which date when the employee started on this job. a not null column, JOB_ID (text up to 10 characters, required) which current job of the employee; foreign key to job_id column of the
jobs table. a not null column, SALARY (decimal with 8 digits and 2 decimal places, optional) which monthly salary of the employee. must be greater
than zero (enforced by constraint emp_salary_min), COMMISSION_PCT (decimal with 2 digits and 2 decimal places, optional) which commission percentage of the employee; only employees in sales
department elgible for commission percentage, MANAGER_ID (integer up to 6 digits, optional) which manager id of the employee; has same domain as manager_id in
departments table. foreign key to employee_id column of employees table.
(useful for reflexive joins and connect by query), and DEPARTMENT_ID (integer up to 4 digits, optional) which department id where employee works; foreign key to department_id
column of the departments table.

This table can be joined with the HR.DEPARTMENTS table by matching DEPARTMENT_ID to DEPARTMENT_ID, the HR.JOBS table by matching JOB_ID to JOB_ID, and the HR.EMPLOYEES table by matching MANAGER_ID to EMPLOYEE_ID.

To perform these joins in SQL, you can use: JOIN HR.DEPARTMENTS ON EMPLOYEES.DEPARTMENT_ID = DEPARTMENTS.DEPARTMENT_ID; JOIN HR.JOBS ON EMPLOYEES.JOB_ID = JOBS.JOB_ID; JOIN HR.EMPLOYEES ON EMPLOYEES.MANAGER_ID = EMPLOYEES.EMPLOYEE_ID.

Technical Information: This data resides in an Oracle Database. Connection details: Host: jcooracledb.francecentral.cloudapp.azure.com, Port: 1521, service: XE. Schema: HR.

AVAILABLE COLUMNS:
    EMPLOYEE_ID, FIRST_NAME, LAST_NAME, EMAIL, PHONE_NUMBER, HIRE_DATE, JOB_ID, SALARY, COMMISSION_PCT, MANAGER_ID, DEPARTMENT_ID
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
    AI Agent specialized for the HR.EMPLOYEES table.
    Database Type: ORACLE
    """
    
    # Table metadata (embedded at generation time)
    SCHEMA = "HR"
    TABLE_NAME = "EMPLOYEES"
    FULL_TABLE_NAME = "HR.EMPLOYEES"
    DATABASE_TYPE = "oracle"
    SQL_SYNTAX = "Oracle SQL"
    TABLE_DESCRIPTION = """The HR.EMPLOYEES table employees table. contains 107 rows. references with departments,
jobs, job_history tables. contains a self reference. This table is located in the HR schema.

The table contains 11 columns: EMPLOYEE_ID (integer up to 6 digits, required) which primary key of employees table, FIRST_NAME (text up to 20 characters, optional) which first name of the employee. a not null column, LAST_NAME (text up to 25 characters, required) which last name of the employee. a not null column, EMAIL (text up to 25 characters, required) which email id of the employee, PHONE_NUMBER (text up to 20 characters, optional) which phone number of the employee; includes country code and area code, HIRE_DATE (date, required) which date when the employee started on this job. a not null column, JOB_ID (text up to 10 characters, required) which current job of the employee; foreign key to job_id column of the
jobs table. a not null column, SALARY (decimal with 8 digits and 2 decimal places, optional) which monthly salary of the employee. must be greater
than zero (enforced by constraint emp_salary_min), COMMISSION_PCT (decimal with 2 digits and 2 decimal places, optional) which commission percentage of the employee; only employees in sales
department elgible for commission percentage, MANAGER_ID (integer up to 6 digits, optional) which manager id of the employee; has same domain as manager_id in
departments table. foreign key to employee_id column of employees table.
(useful for reflexive joins and connect by query), and DEPARTMENT_ID (integer up to 4 digits, optional) which department id where employee works; foreign key to department_id
column of the departments table.

This table can be joined with the HR.DEPARTMENTS table by matching DEPARTMENT_ID to DEPARTMENT_ID, the HR.JOBS table by matching JOB_ID to JOB_ID, and the HR.EMPLOYEES table by matching MANAGER_ID to EMPLOYEE_ID.

To perform these joins in SQL, you can use: JOIN HR.DEPARTMENTS ON EMPLOYEES.DEPARTMENT_ID = DEPARTMENTS.DEPARTMENT_ID; JOIN HR.JOBS ON EMPLOYEES.JOB_ID = JOBS.JOB_ID; JOIN HR.EMPLOYEES ON EMPLOYEES.MANAGER_ID = EMPLOYEES.EMPLOYEE_ID.

Technical Information: This data resides in an Oracle Database. Connection details: Host: jcooracledb.francecentral.cloudapp.azure.com, Port: 1521, service: XE. Schema: HR."""
    COLUMNS = ["EMPLOYEE_ID", "FIRST_NAME", "LAST_NAME", "EMAIL", "PHONE_NUMBER", "HIRE_DATE", "JOB_ID", "SALARY", "COMMISSION_PCT", "MANAGER_ID", "DEPARTMENT_ID"]
    
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
