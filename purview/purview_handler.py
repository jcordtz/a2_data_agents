#!/usr/bin/env python3
"""
Purview Handler
================================================================================

Microsoft Purview Data Governance integration module.
This script handles Purview-related operations for tables including:
- Asset registration in Purview catalog
- Metadata synchronization
- Classification and labeling
- Lineage tracking

================================================================================
DISCLAIMER
================================================================================
This code was generated with AI assistance (AI-generated code).
It is provided "AS-IS" under the MIT License without warranty of any kind.

LICENSE: MIT License - Copyright (c) 2026
See LICENSE file in project root for full license text.
================================================================================

USAGE:
    python purview_handler.py --schema HR --table_name EMPLOYEES
    python purview_handler.py --schema HR --table_name EMPLOYEES --config custom_config.ini
    
    Or programmatically:
    
    from purview.purview_handler import PurviewClient, handle_purview_integration
    
    # Using the high-level function
    result = handle_purview_integration("HR", "EMPLOYEES")
    
    # Using the client directly
    client = PurviewClient("purview_config.ini")
    asset = client.register_table_asset("HR", "EMPLOYEES")
    client.close()

DEPENDENCIES:
    pip install azure-identity azure-purview-catalog azure-purview-scanning

CONFIGURATION:
    See purview_config.ini for connection parameters.
"""

import argparse
import configparser
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Azure SDK imports
try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    from azure.purview.catalog import PurviewCatalogClient
    from azure.purview.scanning import PurviewScanningClient
    from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
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
    auth_method: str = "default_credential"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    collection_name: Optional[str] = None
    database_type: str = "oracle"
    server_host: str = "localhost"
    server_port: int = 1521
    service_name: str = "ORCL"
    create_if_not_exists: bool = True
    update_existing: bool = True
    verbose: bool = False
    default_classifications: List[str] = field(default_factory=list)
    
    @property
    def endpoint(self) -> str:
        """Get the Purview catalog endpoint URL."""
        return f"https://{self.account_name}.purview.azure.com"
    
    @property
    def scan_endpoint(self) -> str:
        """Get the Purview scanning endpoint URL."""
        return f"https://{self.account_name}.purview.azure.com"


@dataclass
class PurviewAsset:
    """Represents a Purview catalog asset."""
    guid: str
    qualified_name: str
    name: str
    type_name: str
    description: Optional[str] = None
    classifications: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualifiedNameParams:
    """
    Parameters for constructing a Purview qualified name.
    
    Attributes:
        database_type: Type of database (oracle, mssql, postgres, mysql, db2)
        schema: Database schema name
        table_name: Table name
        host: Database server hostname (default: localhost)
        port: Database server port (default varies by database type)
        service_name: Service/database name (default: ORCL for Oracle)
    """
    database_type: str
    schema: str
    table_name: str
    host: str = "localhost"
    port: Optional[int] = None
    service_name: str = "ORCL"
    
    def __post_init__(self):
        """Set default port based on database type if not specified."""
        if self.port is None:
            default_ports = {
                "oracle": 1521,
                "mssql": 1433,
                "postgres": 5432,
                "mysql": 3306,
                "db2": 50000
            }
            self.port = default_ports.get(self.database_type.lower(), 1521)


# Database type mappings for Purview asset types and qualified name formats
DATABASE_TYPE_MAPPINGS: Dict[str, Dict[str, str]] = {
    "oracle": {
        "table_type": "oracle_table",
        "schema_type": "oracle_schema",
        "database_type": "oracle_db",
        "column_type": "oracle_column",
        "qualified_name_format": "oracle://{host}:{port}/{service}/{schema}/{table}",
        "default_port": "1521"
    },
    "mssql": {
        "table_type": "azure_sql_table",
        "schema_type": "azure_sql_schema",
        "database_type": "azure_sql_db",
        "column_type": "azure_sql_column",
        "qualified_name_format": "mssql://{host}:{port}/{database}/{schema}/{table}",
        "default_port": "1433"
    },
    "postgres": {
        "table_type": "postgresql_table",
        "schema_type": "postgresql_schema",
        "database_type": "postgresql_db",
        "column_type": "postgresql_column",
        "qualified_name_format": "postgresql://{host}:{port}/{database}/{schema}/{table}",
        "default_port": "5432"
    },
    "mysql": {
        "table_type": "mysql_table",
        "schema_type": "mysql_schema",
        "database_type": "mysql_db",
        "column_type": "mysql_column",
        "qualified_name_format": "mysql://{host}:{port}/{database}/{schema}/{table}",
        "default_port": "3306"
    },
    "db2": {
        "table_type": "db2_table",
        "schema_type": "db2_schema",
        "database_type": "db2_db",
        "column_type": "db2_column",
        "qualified_name_format": "db2://{host}:{port}/{database}/{schema}/{table}",
        "default_port": "50000"
    }
}


def get_supported_database_types() -> List[str]:
    """
    Get list of supported database types.
    
    Returns:
        List of supported database type names
        
    Example:
        >>> types = get_supported_database_types()
        >>> print(types)
        ['oracle', 'mssql', 'postgres', 'mysql', 'db2']
    """
    return list(DATABASE_TYPE_MAPPINGS.keys())


def get_database_type_info(database_type: str) -> Optional[Dict[str, str]]:
    """
    Get Purview type information for a database type.
    
    Args:
        database_type: Type of database (oracle, mssql, postgres, mysql, db2)
        
    Returns:
        Dictionary with type mappings, or None if database type not supported
        
    Example:
        >>> info = get_database_type_info("oracle")
        >>> print(info["table_type"])
        'oracle_table'
    """
    return DATABASE_TYPE_MAPPINGS.get(database_type.lower())


def build_qualified_name(
    database_type: str,
    schema: str,
    table_name: str,
    host: str = "localhost",
    port: Optional[int] = None,
    service_name: str = "ORCL"
) -> str:
    """
    Build a Purview-compatible fully qualified name for a database table.
    
    This function constructs the qualified name format that Purview uses
    to uniquely identify database assets in the catalog.
    
    Args:
        database_type: Type of database (oracle, mssql, postgres, mysql, db2)
        schema: Database schema name (e.g., 'HR', 'SALES', 'dbo')
        table_name: Table name (e.g., 'EMPLOYEES', 'ORDERS')
        host: Database server hostname (default: 'localhost')
        port: Database server port (default: database-specific default)
        service_name: Service name (Oracle) or database name (others)
        
    Returns:
        Fully qualified name string for Purview lookup
        
    Raises:
        ValueError: If database_type is not supported
        
    Examples:
        >>> # Oracle table
        >>> qn = build_qualified_name("oracle", "HR", "EMPLOYEES", 
        ...                           host="db.example.com", port=1521, 
        ...                           service_name="ORCL")
        >>> print(qn)
        'oracle://db.example.com:1521/ORCL/HR/EMPLOYEES'
        
        >>> # SQL Server table
        >>> qn = build_qualified_name("mssql", "dbo", "Customers",
        ...                           host="sql.example.com", port=1433,
        ...                           service_name="AdventureWorks")
        >>> print(qn)
        'mssql://sql.example.com:1433/AdventureWorks/dbo/Customers'
        
        >>> # PostgreSQL table with default port
        >>> qn = build_qualified_name("postgres", "public", "users",
        ...                           host="pg.example.com",
        ...                           service_name="mydb")
        >>> print(qn)
        'postgresql://pg.example.com:5432/mydb/public/users'
    """
    db_type = database_type.lower()
    
    if db_type not in DATABASE_TYPE_MAPPINGS:
        supported = ", ".join(DATABASE_TYPE_MAPPINGS.keys())
        raise ValueError(
            f"Unsupported database type: '{database_type}'. "
            f"Supported types: {supported}"
        )
    
    type_mapping = DATABASE_TYPE_MAPPINGS[db_type]
    
    # Use default port if not specified
    if port is None:
        port = int(type_mapping.get("default_port", 1521))
    
    # Build the qualified name using the format string
    qualified_name = type_mapping["qualified_name_format"].format(
        host=host,
        port=port,
        service=service_name,
        database=service_name,  # For non-Oracle databases
        schema=schema,
        table=table_name
    )
    
    return qualified_name


def build_qualified_name_from_params(params: QualifiedNameParams) -> str:
    """
    Build a Purview qualified name from a QualifiedNameParams object.
    
    Args:
        params: QualifiedNameParams object with all required parameters
        
    Returns:
        Fully qualified name string for Purview lookup
        
    Example:
        >>> params = QualifiedNameParams(
        ...     database_type="oracle",
        ...     schema="HR",
        ...     table_name="EMPLOYEES",
        ...     host="db.example.com"
        ... )
        >>> qn = build_qualified_name_from_params(params)
        >>> print(qn)
        'oracle://db.example.com:1521/ORCL/HR/EMPLOYEES'
    """
    return build_qualified_name(
        database_type=params.database_type,
        schema=params.schema,
        table_name=params.table_name,
        host=params.host,
        port=params.port,
        service_name=params.service_name
    )


def parse_qualified_name(qualified_name: str) -> Optional[Dict[str, str]]:
    """
    Parse a Purview qualified name into its components.
    
    Args:
        qualified_name: Fully qualified name string
        
    Returns:
        Dictionary with parsed components, or None if parsing fails
        Keys: database_type, host, port, service_name, schema, table_name
        
    Example:
        >>> parsed = parse_qualified_name("oracle://db.example.com:1521/ORCL/HR/EMPLOYEES")
        >>> print(parsed)
        {'database_type': 'oracle', 'host': 'db.example.com', 'port': '1521',
         'service_name': 'ORCL', 'schema': 'HR', 'table_name': 'EMPLOYEES'}
    """
    import re
    
    # Pattern to match: protocol://host:port/service/schema/table
    pattern = r'^(\w+)://([^:]+):(\d+)/([^/]+)/([^/]+)/([^/]+)$'
    match = re.match(pattern, qualified_name)
    
    if not match:
        return None
    
    db_type_map = {
        "oracle": "oracle",
        "mssql": "mssql",
        "postgresql": "postgres",
        "mysql": "mysql",
        "db2": "db2"
    }
    
    protocol = match.group(1)
    database_type = db_type_map.get(protocol, protocol)
    
    return {
        "database_type": database_type,
        "host": match.group(2),
        "port": match.group(3),
        "service_name": match.group(4),
        "schema": match.group(5),
        "table_name": match.group(6)
    }


class PurviewClient:
    """
    Client for interacting with Microsoft Purview Data Governance.
    
    This client provides methods for:
    - Registering database table assets in Purview catalog
    - Searching for existing assets
    - Applying classifications
    - Managing metadata
    
    Example:
        >>> client = PurviewClient("purview_config.ini")
        >>> asset = client.register_table_asset("HR", "EMPLOYEES")
        >>> print(f"Registered asset: {asset.guid}")
        >>> client.close()
    """
    
    def __init__(self, config_path: str = "purview_config.ini"):
        """
        Initialize the Purview client.
        
        Args:
            config_path: Path to the configuration file
            
        Raises:
            ImportError: If Azure SDK is not installed
            FileNotFoundError: If config file doesn't exist
            ValueError: If required configuration is missing
        """
        if not AZURE_SDK_AVAILABLE:
            raise ImportError(
                "Azure SDK packages not installed. Install with:\n"
                "pip install azure-identity azure-purview-catalog azure-purview-scanning"
            )
        
        self.config = self._load_config(config_path)
        self.credential = self._create_credential()
        self.catalog_client = self._create_catalog_client()
        self.scanning_client = self._create_scanning_client()
        
        if self.config.verbose:
            logger.setLevel(logging.DEBUG)
        
        logger.info(f"Purview client initialized for account: {self.config.account_name}")
    
    def _load_config(self, config_path: str) -> PurviewConfig:
        """Load configuration from INI file."""
        path = Path(config_path)
        if not path.exists():
            # Try relative to this file's directory
            path = Path(__file__).parent / config_path
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        parser = configparser.ConfigParser()
        parser.read(path)
        
        # Parse classifications list
        classifications_str = parser.get("options", "default_classifications", fallback="")
        classifications = [c.strip() for c in classifications_str.split(",") if c.strip()]
        
        return PurviewConfig(
            account_name=parser.get("purview", "account_name"),
            tenant_id=parser.get("purview", "tenant_id"),
            auth_method=parser.get("purview", "auth_method", fallback="default_credential"),
            client_id=parser.get("purview", "client_id", fallback=None),
            client_secret=parser.get("purview", "client_secret", fallback=None),
            collection_name=parser.get("purview", "collection_name", fallback=None) or None,
            database_type=parser.get("database", "database_type", fallback="oracle"),
            server_host=parser.get("database", "server_host", fallback="localhost"),
            server_port=parser.getint("database", "server_port", fallback=1521),
            service_name=parser.get("database", "service_name", fallback="ORCL"),
            create_if_not_exists=parser.getboolean("options", "create_if_not_exists", fallback=True),
            update_existing=parser.getboolean("options", "update_existing", fallback=True),
            verbose=parser.getboolean("options", "verbose", fallback=False),
            default_classifications=classifications
        )
    
    def _create_credential(self):
        """Create Azure credential based on configuration."""
        if self.config.auth_method == "service_principal":
            if not self.config.client_id or not self.config.client_secret:
                raise ValueError(
                    "Service principal authentication requires client_id and client_secret"
                )
            return ClientSecretCredential(
                tenant_id=self.config.tenant_id,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret
            )
        else:
            # Use DefaultAzureCredential which supports multiple auth methods
            return DefaultAzureCredential()
    
    def _create_catalog_client(self) -> "PurviewCatalogClient":
        """Create Purview Catalog client."""
        return PurviewCatalogClient(
            endpoint=self.config.endpoint,
            credential=self.credential
        )
    
    def _create_scanning_client(self) -> "PurviewScanningClient":
        """Create Purview Scanning client."""
        return PurviewScanningClient(
            endpoint=self.config.scan_endpoint,
            credential=self.credential
        )
    
    def _get_type_mapping(self) -> Dict[str, str]:
        """Get type mapping for the configured database type."""
        db_type = self.config.database_type.lower()
        if db_type not in DATABASE_TYPE_MAPPINGS:
            logger.warning(f"Unknown database type '{db_type}', defaulting to 'oracle'")
            db_type = "oracle"
        return DATABASE_TYPE_MAPPINGS[db_type]
    
    def _build_qualified_name(self, schema: str, table_name: str) -> str:
        """Build the fully qualified name for a table asset."""
        return build_qualified_name(
            database_type=self.config.database_type,
            schema=schema,
            table_name=table_name,
            host=self.config.server_host,
            port=self.config.server_port,
            service_name=self.config.service_name
        )
    
    def search_asset(self, qualified_name: str) -> Optional[PurviewAsset]:
        """
        Search for an asset by qualified name.
        
        Args:
            qualified_name: The fully qualified name of the asset
            
        Returns:
            PurviewAsset if found, None otherwise
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
                return PurviewAsset(
                    guid=entity.get("id", ""),
                    qualified_name=entity.get("qualifiedName", qualified_name),
                    name=entity.get("name", ""),
                    type_name=entity.get("entityType", ""),
                    description=entity.get("description"),
                    classifications=entity.get("classification", []),
                    attributes=entity.get("attributes", {})
                )
            
            return None
            
        except HttpResponseError as e:
            logger.error(f"Error searching for asset: {e}")
            return None
    
    def register_table_asset(
        self,
        schema: str,
        table_name: str,
        description: Optional[str] = None,
        columns: Optional[List[Dict[str, str]]] = None,
        classifications: Optional[List[str]] = None
    ) -> PurviewAsset:
        """
        Register a database table as an asset in Purview catalog.
        
        Args:
            schema: Database schema name
            table_name: Table name
            description: Optional description of the table
            columns: Optional list of column definitions
            classifications: Optional list of classification names to apply
            
        Returns:
            PurviewAsset representing the registered asset
            
        Raises:
            HttpResponseError: If the API call fails
        """
        qualified_name = self._build_qualified_name(schema, table_name)
        type_mapping = self._get_type_mapping()
        
        logger.info(f"Registering table asset: {schema}.{table_name}")
        logger.debug(f"Qualified name: {qualified_name}")
        
        # Check if asset already exists
        existing_asset = self.search_asset(qualified_name)
        if existing_asset:
            if self.config.update_existing:
                logger.info(f"Asset exists, updating: {existing_asset.guid}")
                return self._update_asset(existing_asset, description, classifications)
            else:
                logger.info(f"Asset already exists: {existing_asset.guid}")
                return existing_asset
        
        if not self.config.create_if_not_exists:
            raise ResourceNotFoundError(f"Asset not found and create_if_not_exists is False")
        
        # Build the entity definition
        entity = {
            "typeName": type_mapping["table_type"],
            "attributes": {
                "name": table_name,
                "qualifiedName": qualified_name,
                "description": description or f"Table {schema}.{table_name}",
                "schemaName": schema,
                "createTime": int(datetime.now().timestamp() * 1000),
                "modifiedTime": int(datetime.now().timestamp() * 1000)
            }
        }
        
        # Add classifications
        all_classifications = list(self.config.default_classifications)
        if classifications:
            all_classifications.extend(classifications)
        
        if all_classifications:
            entity["classifications"] = [
                {"typeName": c} for c in all_classifications
            ]
        
        # Add collection reference if specified
        if self.config.collection_name:
            entity["attributes"]["collectionId"] = self.config.collection_name
        
        try:
            # Create or update the entity
            request_body = {
                "entities": [entity]
            }
            
            result = self.catalog_client.entity.create_or_update(request_body)
            
            # Extract the created entity GUID
            guid_assignments = result.get("guidAssignments", {})
            entity_guid = list(guid_assignments.values())[0] if guid_assignments else None
            
            if not entity_guid:
                # Try to get from mutatedEntities
                mutated = result.get("mutatedEntities", {})
                created = mutated.get("CREATE", []) or mutated.get("UPDATE", [])
                if created:
                    entity_guid = created[0].get("guid")
            
            logger.info(f"Asset registered successfully: {entity_guid}")
            
            return PurviewAsset(
                guid=entity_guid or "",
                qualified_name=qualified_name,
                name=table_name,
                type_name=type_mapping["table_type"],
                description=description,
                classifications=all_classifications
            )
            
        except HttpResponseError as e:
            logger.error(f"Failed to register asset: {e}")
            raise
    
    def _update_asset(
        self,
        asset: PurviewAsset,
        description: Optional[str] = None,
        classifications: Optional[List[str]] = None
    ) -> PurviewAsset:
        """Update an existing asset."""
        try:
            # Get current entity
            entity_result = self.catalog_client.entity.get_by_guid(asset.guid)
            entity = entity_result.get("entity", {})
            
            # Update attributes
            if description:
                entity["attributes"]["description"] = description
            
            entity["attributes"]["modifiedTime"] = int(datetime.now().timestamp() * 1000)
            
            # Update classifications
            all_classifications = list(self.config.default_classifications)
            if classifications:
                all_classifications.extend(classifications)
            
            if all_classifications:
                existing_classifications = [c["typeName"] for c in entity.get("classifications", [])]
                new_classifications = [c for c in all_classifications if c not in existing_classifications]
                
                if new_classifications:
                    # Add new classifications
                    classification_body = [{"typeName": c} for c in new_classifications]
                    self.catalog_client.entity.add_classifications(
                        guid=asset.guid,
                        classifications=classification_body
                    )
            
            # Update entity
            request_body = {"entities": [entity]}
            self.catalog_client.entity.create_or_update(request_body)
            
            logger.info(f"Asset updated: {asset.guid}")
            
            return PurviewAsset(
                guid=asset.guid,
                qualified_name=asset.qualified_name,
                name=asset.name,
                type_name=asset.type_name,
                description=description or asset.description,
                classifications=list(set(asset.classifications + all_classifications))
            )
            
        except HttpResponseError as e:
            logger.error(f"Failed to update asset: {e}")
            raise
    
    def get_asset_lineage(self, guid: str, direction: str = "BOTH") -> Dict[str, Any]:
        """
        Get lineage information for an asset.
        
        Args:
            guid: The asset GUID
            direction: Lineage direction ("INPUT", "OUTPUT", or "BOTH")
            
        Returns:
            Dictionary containing lineage information
        """
        try:
            result = self.catalog_client.lineage.get_lineage(
                guid=guid,
                direction=direction
            )
            return result
        except HttpResponseError as e:
            logger.error(f"Failed to get lineage: {e}")
            return {}
    
    def apply_classification(self, guid: str, classification_name: str) -> bool:
        """
        Apply a classification to an asset.
        
        Args:
            guid: The asset GUID
            classification_name: Name of the classification to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            classification_body = [{"typeName": classification_name}]
            self.catalog_client.entity.add_classifications(
                guid=guid,
                classifications=classification_body
            )
            logger.info(f"Applied classification '{classification_name}' to asset {guid}")
            return True
        except HttpResponseError as e:
            logger.error(f"Failed to apply classification: {e}")
            return False
    
    def close(self):
        """Close the client connections."""
        # Azure SDK clients handle cleanup automatically
        logger.info("Purview client closed")


def handle_purview_integration(
    schema: str,
    table_name: str,
    config_path: str = "purview_config.ini",
    host: Optional[str] = None,
    db_type: str = "oracle",
    description: Optional[str] = None,
    classifications: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Handle Purview integration for a specific table.
    
    This is the main entry point for Purview integration, used by the
    agent generator to register tables with Purview.
    
    Args:
        schema: The database schema name (e.g., 'HR', 'SALES')
        table_name: The table name (e.g., 'EMPLOYEES', 'ORDERS')
        config_path: Path to Purview configuration file
        host: Database server hostname (overrides config file if provided)
        db_type: Database type (oracle, mssql, postgres, db2)
        description: Optional description for the table
        classifications: Optional list of classifications to apply
        
    Returns:
        Dict containing the result of the Purview operation:
            - success (bool): Whether the operation succeeded
            - message (str): Description of the result
            - purview_asset_id (str, optional): The Purview asset GUID
            - qualified_name (str): The fully qualified name
            
    Example:
        >>> result = handle_purview_integration("HR", "EMPLOYEES")
        >>> print(result)
        {'success': True, 'message': 'Asset registered', 'purview_asset_id': '...'}
    """
    full_table_name = f"{schema}.{table_name}"
    
    logger.info(f"[PURVIEW] Processing table: {full_table_name}")
    
    # Check if Azure SDK is available
    if not AZURE_SDK_AVAILABLE:
        logger.warning(
            "[PURVIEW] Azure SDK not installed. Install with:\n"
            "pip install azure-identity azure-purview-catalog azure-purview-scanning"
        )
        return {
            "success": False,
            "message": "Azure SDK not installed",
            "schema": schema,
            "table_name": table_name,
            "full_table_name": full_table_name,
            "purview_asset_id": None,
            "qualified_name": None
        }
    
    try:
        # Initialize client
        client = PurviewClient(config_path)
        
        # Override host if provided
        if host:
            client.config.server_host = host
        
        # Override database type if provided
        if db_type:
            client.config.database_type = db_type
        
        # Register the table asset
        asset = client.register_table_asset(
            schema=schema,
            table_name=table_name,
            description=description,
            classifications=classifications
        )
        
        client.close()
        
        result = {
            "success": True,
            "message": f"Asset registered successfully: {asset.guid}",
            "schema": schema,
            "table_name": table_name,
            "full_table_name": full_table_name,
            "purview_asset_id": asset.guid,
            "qualified_name": asset.qualified_name,
            "type_name": asset.type_name,
            "classifications": asset.classifications
        }
        
        logger.info(f"[PURVIEW] Successfully registered {full_table_name}")
        return result
        
    except FileNotFoundError as e:
        error_msg = f"Configuration file not found: {e}"
        logger.error(f"[PURVIEW] {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "schema": schema,
            "table_name": table_name,
            "full_table_name": full_table_name,
            "purview_asset_id": None,
            "qualified_name": None
        }
        
    except Exception as e:
        error_msg = f"Purview integration failed: {str(e)}"
        logger.error(f"[PURVIEW] {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "schema": schema,
            "table_name": table_name,
            "full_table_name": full_table_name,
            "purview_asset_id": None,
            "qualified_name": None,
            "error": str(e)
        }


def main():
    """Command-line interface for Purview handler."""
    parser = argparse.ArgumentParser(
        description="Microsoft Purview Data Governance integration handler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python purview_handler.py --schema HR --table_name EMPLOYEES
    python purview_handler.py -s SALES -t CUSTOMERS --host db.example.com
    python purview_handler.py -s HR -t EMPLOYEES --db-type mssql --host sql.example.com
    python purview_handler.py -s HR -t EMPLOYEES --config custom_config.ini
    python purview_handler.py -s HR -t EMPLOYEES --classifications "PII,Confidential"
        """
    )
    
    parser.add_argument(
        "--schema", "-s",
        type=str,
        required=True,
        help="The database schema name (e.g., HR, SALES)"
    )
    
    parser.add_argument(
        "--table_name", "-t",
        type=str,
        required=True,
        help="The table name (e.g., EMPLOYEES, ORDERS)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Database server hostname (overrides config file)"
    )
    
    parser.add_argument(
        "--db-type",
        type=str,
        default="oracle",
        choices=["oracle", "mssql", "postgres", "db2"],
        help="Database type (oracle, mssql, postgres, db2)"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="purview_config.ini",
        help="Path to Purview configuration file (default: purview_config.ini)"
    )
    
    parser.add_argument(
        "--description", "-d",
        type=str,
        default=None,
        help="Description for the table asset"
    )
    
    parser.add_argument(
        "--classifications",
        type=str,
        default=None,
        help="Comma-separated list of classifications to apply"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Parse classifications
    classifications = None
    if args.classifications:
        classifications = [c.strip() for c in args.classifications.split(",")]
    
    # Execute the Purview integration
    result = handle_purview_integration(
        schema=args.schema,
        table_name=args.table_name,
        config_path=args.config,
        host=args.host,
        db_type=getattr(args, 'db_type', 'oracle'),
        description=args.description,
        classifications=classifications
    )
    
    # Print result
    print("\n" + "=" * 60)
    print("PURVIEW INTEGRATION RESULT")
    print("=" * 60)
    print(f"Success:        {result['success']}")
    print(f"Message:        {result['message']}")
    print(f"Table:          {result['full_table_name']}")
    if result.get('purview_asset_id'):
        print(f"Asset GUID:     {result['purview_asset_id']}")
    if result.get('qualified_name'):
        print(f"Qualified Name: {result['qualified_name']}")
    if result.get('classifications'):
        print(f"Classifications: {', '.join(result['classifications'])}")
    print("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
