#!/usr/bin/env python3
"""
Purview Handler
================================================================================

Microsoft Purview Data Governance integration module.
This script looks up table assets and their column assets in Purview and 
retrieves their descriptions, formatting them as easy-to-read essay-style prose.

================================================================================
DISCLAIMER
================================================================================
This code was generated with AI assistance (AI-generated code).
It is provided "AS-IS" under the MIT License without warranty of any kind.

LICENSE: MIT License - Copyright (c) 2026
See LICENSE file in project root for full license text.
================================================================================

USAGE:
    python purview_handler.py --db-type oracle --host db.example.com --port 1521 \
        --service-name ORCL --schema HR --table_name EMPLOYEES
    
    Or programmatically:
    
    from purview.purview_handler import lookup_asset_description
    
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

ALL PARAMETERS ARE REQUIRED:
    - db_type: Database type (oracle, mssql, postgres, db2)
    - host: Database server hostname
    - port: Database server port
    - service_name: Service name (Oracle) or database name (others)
    - schema: Database schema name
    - table_name: Table name

DEPENDENCIES:
    pip install azure-identity azure-purview-catalog

CONFIGURATION:
    See purview_config.ini for Purview connection parameters.
"""

import argparse
import configparser
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# Azure SDK imports
try:
    from azure.identity import ClientSecretCredential
    from azure.purview.catalog import PurviewCatalogClient
    from azure.core.exceptions import HttpResponseError
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s'
)
logger = logging.getLogger("purview_handler")


@dataclass
class PurviewConfig:
    """Configuration for Purview connection."""
    account_name: str
    tenant_id: str
    client_id: str
    client_secret: str
    
    @property
    def endpoint(self) -> str:
        """Get the Purview catalog endpoint URL."""
        return f"https://{self.account_name}.purview.azure.com"


# Database type mappings for qualified name formats
DATABASE_TYPE_MAPPINGS: Dict[str, str] = {
    "oracle": "oracle://{host}:{port}/{service}/{schema}/{table}",
    "mssql": "mssql://{host}:{port}/{database}/{schema}/{table}",
    "postgres": "postgresql://{host}:{port}/{database}/{schema}/{table}",
    "db2": "db2://{host}:{port}/{database}/{schema}/{table}"
}


def build_qualified_name(
    database_type: str,
    host: str,
    service_name: str,
    schema: str,
    table_name: str,
    port: int
) -> str:
    """
    Build a Purview-compatible fully qualified name for a database table.
    
    All parameters are required.
    
    Args:
        database_type: Type of database (oracle, mssql, postgres, db2) (required)
        host: Database server hostname (required)
        service_name: Service name (Oracle) or database name (others) (required)
        schema: Database schema name (required)
        table_name: Table name (required)
        port: Database server port (required)
        
    Returns:
        Fully qualified name string for Purview lookup
        
    Raises:
        ValueError: If database_type is not supported or required params are missing
    """
    db_type = database_type.lower()
    
    if db_type not in DATABASE_TYPE_MAPPINGS:
        raise ValueError(f"Unsupported database type: '{database_type}'")
    
    qualified_name = DATABASE_TYPE_MAPPINGS[db_type].format(
        host=host,
        port=port,
        service=service_name,
        database=service_name,
        schema=schema,
        table=table_name
    )
    
    return qualified_name


class PurviewClient:
    """Client for looking up assets in Microsoft Purview."""
    
    def __init__(self, config_path: str = "purview_config.ini"):
        """
        Initialize the Purview client.
        
        Args:
            config_path: Path to the configuration file
        """
        if not AZURE_SDK_AVAILABLE:
            raise ImportError(
                "Azure SDK packages not installed. Install with:\n"
                "pip install azure-identity azure-purview-catalog"
            )
        
        self.config = self._load_config(config_path)
        self.credential = ClientSecretCredential(
            tenant_id=self.config.tenant_id,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret
        )
        self.catalog_client = PurviewCatalogClient(
            endpoint=self.config.endpoint,
            credential=self.credential
        )
        
        logger.info(f"Purview client initialized for account: {self.config.account_name}")
    
    def _load_config(self, config_path: str) -> PurviewConfig:
        """Load configuration from INI file."""
        path = Path(config_path)
        if not path.exists():
            path = Path(__file__).parent / config_path
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        parser = configparser.ConfigParser()
        parser.read(path)
        
        return PurviewConfig(
            account_name=parser.get("purview", "account_name"),
            tenant_id=parser.get("purview", "tenant_id"),
            client_id=parser.get("purview", "client_id"),
            client_secret=parser.get("purview", "client_secret")
        )
    
    def get_asset_description(self, qualified_name: str) -> str:
        """
        Look up an asset by qualified name and return its description.
        
        Args:
            qualified_name: The fully qualified name of the asset
            
        Returns:
            Asset description if found, "N/A" otherwise
        """
        try:
            search_request = {
                "keywords": qualified_name,
                "limit": 1,
                "filter": {
                    "and": [
                        {
                            "attributeName": "qualifiedName",
                            "operator": "eq",
                            "attributeValue": qualified_name
                        }
                    ]
                }
            }
            
            result = self.catalog_client.discovery.query(search_request)
            
            if result.get("value") and len(result["value"]) > 0:
                entity = result["value"][0]
                description = entity.get("description")
                if description:
                    logger.info(f"Found asset: {qualified_name}")
                    return description
                else:
                    logger.info(f"Asset found but no description: {qualified_name}")
                    return "N/A"
            
            logger.info(f"Asset not found: {qualified_name}")
            return "N/A"
            
        except HttpResponseError as e:
            logger.error(f"Error searching for asset: {e}")
            return "N/A"
    
    def get_table_entity_guid(self, qualified_name: str) -> Optional[str]:
        """
        Look up a table asset by qualified name and return its GUID.
        
        Args:
            qualified_name: The fully qualified name of the table
            
        Returns:
            Entity GUID if found, None otherwise
        """
        try:
            search_request = {
                "keywords": qualified_name,
                "limit": 1,
                "filter": {
                    "and": [
                        {
                            "attributeName": "qualifiedName",
                            "operator": "eq",
                            "attributeValue": qualified_name
                        }
                    ]
                }
            }
            
            result = self.catalog_client.discovery.query(search_request)
            
            if result.get("value") and len(result["value"]) > 0:
                entity = result["value"][0]
                return entity.get("id") or entity.get("guid")
            
            return None
            
        except HttpResponseError as e:
            logger.error(f"Error searching for table entity: {e}")
            return None
    
    def get_column_descriptions(self, table_qualified_name: str) -> List[Dict[str, str]]:
        """
        Look up all column assets for a table and return their names and descriptions.
        
        Args:
            table_qualified_name: The fully qualified name of the table
            
        Returns:
            List of dicts with 'name' and 'description' for each column
        """
        columns = []
        
        try:
            # First try to get the table entity and its columns via entity API
            table_guid = self.get_table_entity_guid(table_qualified_name)
            
            if table_guid:
                # Try to get entity with relationships to find columns
                try:
                    entity_response = self.catalog_client.entity.get_by_guid(
                        table_guid,
                        min_ext_info=False,
                        ignore_relationships=False
                    )
                    
                    if entity_response:
                        entity = entity_response.get("entity", {})
                        relationship_attributes = entity.get("relationshipAttributes", {})
                        
                        # Columns are typically in 'columns' relationship
                        column_refs = relationship_attributes.get("columns", [])
                        
                        for col_ref in column_refs:
                            col_guid = col_ref.get("guid")
                            col_name = col_ref.get("displayText") or col_ref.get("uniqueAttributes", {}).get("name")
                            
                            if col_guid:
                                # Get full column entity to get description
                                try:
                                    col_entity = self.catalog_client.entity.get_by_guid(col_guid)
                                    if col_entity:
                                        col_attrs = col_entity.get("entity", {}).get("attributes", {})
                                        col_description = col_attrs.get("description", "")
                                        col_display_name = col_attrs.get("name") or col_name
                                        
                                        if col_description:
                                            columns.append({
                                                "name": col_display_name,
                                                "description": col_description
                                            })
                                except Exception as e:
                                    logger.debug(f"Could not get column entity {col_guid}: {e}")
                                    continue
                        
                        if columns:
                            logger.info(f"Found {len(columns)} columns with descriptions for table")
                            return columns
                            
                except Exception as e:
                    logger.debug(f"Could not get entity relationships: {e}")
            
            # Fallback: Search for columns by qualified name pattern
            # Columns typically have qualified names like: table_qualified_name#column_name
            # or table_qualified_name/column_name
            for separator in ["#", "/"]:
                search_request = {
                    "keywords": f"{table_qualified_name}{separator}*",
                    "limit": 100,
                    "filter": {
                        "and": [
                            {
                                "attributeName": "qualifiedName",
                                "operator": "startswith",
                                "attributeValue": f"{table_qualified_name}{separator}"
                            }
                        ]
                    }
                }
                
                result = self.catalog_client.discovery.query(search_request)
                
                if result.get("value"):
                    for entity in result["value"]:
                        col_name = entity.get("name") or entity.get("displayText")
                        col_description = entity.get("description")
                        
                        if col_name and col_description:
                            columns.append({
                                "name": col_name,
                                "description": col_description
                            })
                    
                    if columns:
                        logger.info(f"Found {len(columns)} columns with descriptions via search")
                        break
            
            return columns
            
        except HttpResponseError as e:
            logger.error(f"Error searching for column assets: {e}")
            return columns
    
    def get_table_and_column_descriptions(self, qualified_name: str) -> str:
        """
        Look up a table asset and its columns, returning an essay-style description.
        
        Args:
            qualified_name: The fully qualified name of the table
            
        Returns:
            Essay-style description of table and columns, or "N/A" if not found
        """
        # Get table description
        table_description = self.get_asset_description(qualified_name)
        
        # Get column descriptions
        column_descriptions = self.get_column_descriptions(qualified_name)
        
        # Build combined description
        if table_description == "N/A" and not column_descriptions:
            return "N/A"
        
        return self._format_as_essay(table_description, column_descriptions)
    
    def _format_as_essay(self, table_description: str, column_descriptions: List[Dict[str, str]]) -> str:
        """
        Format table and column descriptions as an easy-to-read essay.
        
        Args:
            table_description: The table's description or "N/A"
            column_descriptions: List of column dicts with 'name' and 'description'
            
        Returns:
            Essay-style description text
        """
        paragraphs = []
        
        # Opening paragraph with table description
        if table_description != "N/A":
            paragraphs.append(table_description)
        
        # Build column descriptions as flowing prose
        if column_descriptions:
            if len(column_descriptions) == 1:
                col = column_descriptions[0]
                col_text = f"This table contains the {col['name']} column, which {self._lowercase_first(col['description'])}"
                paragraphs.append(col_text)
            else:
                # Group columns into sentences
                col_intro = "The table includes the following data elements: "
                col_parts = []
                
                for i, col in enumerate(column_descriptions):
                    col_name = col['name']
                    col_desc = self._lowercase_first(col['description'])
                    
                    if i == len(column_descriptions) - 1 and len(column_descriptions) > 1:
                        # Last column with "and"
                        col_parts.append(f"and {col_name} ({col_desc})")
                    else:
                        col_parts.append(f"{col_name} ({col_desc})")
                
                # Join with appropriate punctuation
                if len(col_parts) <= 3:
                    col_text = col_intro + ", ".join(col_parts) + "."
                else:
                    # For many columns, create multiple sentences
                    col_text = col_intro + col_parts[0]
                    for part in col_parts[1:]:
                        col_text += ", " + part
                    col_text += "."
                
                paragraphs.append(col_text)
        
        return "\n\n".join(paragraphs) if paragraphs else "N/A"
    
    def _lowercase_first(self, text: str) -> str:
        """
        Lowercase the first character of a string if appropriate.
        
        Preserves capitalization for acronyms, proper nouns, etc.
        
        Args:
            text: Input text
            
        Returns:
            Text with potentially lowercased first character
        """
        if not text:
            return text
        
        # Don't lowercase if it looks like an acronym or proper noun
        # (all caps or second char is also uppercase)
        if len(text) > 1 and text[1].isupper():
            return text
        
        # Don't lowercase if starts with "I " or "I'"
        if text.startswith("I ") or text.startswith("I'"):
            return text
            
        return text[0].lower() + text[1:] if len(text) > 1 else text.lower()
    
    def close(self):
        """Close the client connections."""
        logger.info("Purview client closed")


def lookup_asset_description(
    db_type: str,
    host: str,
    service_name: str,
    schema: str,
    table_name: str,
    port: int,
    config_path: str = "purview_config.ini"
) -> str:
    """
    Look up a table asset and its columns in Purview and return their descriptions.
    
    This is the main entry point for Purview lookups. It retrieves the table
    description and all column descriptions, combining them into a single output.
    
    All parameters are required.
    
    Args:
        db_type: Database type (oracle, mssql, postgres, db2) (required)
        host: Database server hostname (required)
        service_name: Service name (Oracle) or database name (others) (required)
        schema: The database schema name (e.g., 'HR', 'SALES') (required)
        table_name: The table name (e.g., 'EMPLOYEES', 'ORDERS') (required)
        port: Database port (required)
        config_path: Path to Purview configuration file
        
    Returns:
        Essay-style description of table and columns if found, "N/A" otherwise.
        The description is formatted as flowing prose for easy reading.
        
    Example:
        >>> desc = lookup_asset_description(
        ...     db_type="oracle",
        ...     host="db.example.com",
        ...     service_name="ORCL",
        ...     schema="HR",
        ...     table_name="EMPLOYEES",
        ...     port=1521
        ... )
        >>> print(desc)
        This table stores employee master data including personal information
        and employment details.
        
        The table includes the following data elements: EMPLOYEE_ID (unique 
        identifier for each employee), FIRST_NAME (employee's given name), 
        and LAST_NAME (employee's family name).
    """
    if not AZURE_SDK_AVAILABLE:
        logger.warning("Azure SDK not installed")
        return "N/A"
    
    try:
        qualified_name = build_qualified_name(
            database_type=db_type,
            host=host,
            service_name=service_name,
            schema=schema,
            table_name=table_name,
            port=port
        )
        
        client = PurviewClient(config_path)
        description = client.get_table_and_column_descriptions(qualified_name)
        client.close()
        
        return description
        
    except Exception as e:
        logger.error(f"Purview lookup failed: {e}")
        return "N/A"


def main():
    """Command-line interface for Purview lookup."""
    parser = argparse.ArgumentParser(
        description="Look up table description in Microsoft Purview",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python purview_handler.py --db-type oracle --host db.example.com --port 1521 --service-name ORCL --schema HR --table_name EMPLOYEES
    python purview_handler.py --db-type mssql --host sql.example.com --port 1433 --service-name mydb -s SALES -t ORDERS
        """
    )
    
    parser.add_argument(
        "--db-type",
        type=str,
        required=True,
        choices=["oracle", "mssql", "postgres", "db2"],
        help="Database type (required)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Database server hostname (required)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Database port (required)"
    )
    
    parser.add_argument(
        "--service-name",
        type=str,
        required=True,
        help="Service name (Oracle) or database name (others) (required)"
    )
    
    parser.add_argument(
        "--schema", "-s",
        type=str,
        required=True,
        help="The database schema name (required)"
    )
    
    parser.add_argument(
        "--table_name", "-t",
        type=str,
        required=True,
        help="The table name (required)"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="purview_config.ini",
        help="Path to Purview configuration file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    description = lookup_asset_description(
        db_type=args.db_type,
        host=args.host,
        service_name=args.service_name,
        schema=args.schema,
        table_name=args.table_name,
        port=args.port,
        config_path=args.config
    )
    
    print(description)
    
    sys.exit(0 if description != "N/A" else 1)


if __name__ == "__main__":
    main()
