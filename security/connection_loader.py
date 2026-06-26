"""
Connection Configuration Loader
================================================================================

A Python module for loading database connection configurations from XML files
in the security directory. Supports credential lookup from Azure Key Vault.

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

USAGE
-----
Basic usage:

    from security.connection_loader import ConnectionLoader

    # Load Oracle connection by hostname
    loader = ConnectionLoader()
    config = loader.get_connection("oracle", "db.example.com")
    
    # Get credentials (resolves Key Vault if configured)
    creds = loader.get_credentials("oracle", "db.example.com")

With explicit XML path:

    loader = ConnectionLoader(security_dir="/path/to/security")
    config = loader.get_connection("mssql", "sql.example.com")

================================================================================
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, List

# Azure Key Vault imports (optional)
_AZURE_KEYVAULT_ERROR = None
try:
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, ClientSecretCredential
    from azure.keyvault.secrets import SecretClient
except ImportError as e:
    DefaultAzureCredential = None
    ManagedIdentityCredential = None
    ClientSecretCredential = None
    SecretClient = None
    _AZURE_KEYVAULT_ERROR = e


# Mapping of database types to XML filenames
DATABASE_XML_FILES = {
    "oracle": "oracle_connections.xml",
    "mssql": "mssql_connections.xml",
    "postgres": "postgres_connections.xml",
    "db2": "ibmdb2_connections.xml",
    "ibmdb2": "ibmdb2_connections.xml",
}


class ConnectionLoader:
    """
    Loads database connection configurations from XML files.
    Supports credential lookup from Azure Key Vault.
    """

    def __init__(self, security_dir: Optional[str] = None):
        """
        Initialize the connection loader.

        Args:
            security_dir: Path to the security directory containing XML files.
                         Defaults to the 'security' directory relative to this file.
        """
        if security_dir:
            self.security_dir = Path(security_dir)
        else:
            # Default to the security directory in the project root
            self.security_dir = Path(__file__).parent
        
        self._cache: Dict[str, ET.Element] = {}
        self._keyvault_clients: Dict[str, "SecretClient"] = {}

    def _get_xml_path(self, db_type: str) -> Path:
        """Get the path to the XML file for a database type."""
        db_type_lower = db_type.lower()
        if db_type_lower not in DATABASE_XML_FILES:
            raise ValueError(f"Unknown database type: {db_type}. Supported: {list(DATABASE_XML_FILES.keys())}")
        
        return self.security_dir / DATABASE_XML_FILES[db_type_lower]

    def _load_xml(self, db_type: str) -> ET.Element:
        """Load and parse the XML file for a database type."""
        if db_type in self._cache:
            return self._cache[db_type]
        
        xml_path = self._get_xml_path(db_type)
        if not xml_path.exists():
            raise FileNotFoundError(f"Connection XML file not found: {xml_path}")
        
        tree = ET.parse(xml_path)
        root = tree.getroot()
        self._cache[db_type] = root
        return root

    def list_connections(self, db_type: str) -> List[Dict[str, str]]:
        """
        List all connections defined for a database type.

        Args:
            db_type: Database type (oracle, mssql, postgres, db2)

        Returns:
            List of connection summaries with id, host, and description
        """
        root = self._load_xml(db_type)
        connections = []
        
        for conn in root.findall("connection"):
            conn_info = {
                "id": conn.get("id", ""),
                "host": self._get_element_text(conn, "host", ""),
                "description": self._get_element_text(conn, "description", ""),
                "auth": conn.get("auth", ""),
                "environment": conn.get("environment", "production"),
            }
            connections.append(conn_info)
        
        return connections

    def get_connection(self, db_type: str, host: str, connection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get connection configuration by hostname.

        Args:
            db_type: Database type (oracle, mssql, postgres, db2)
            host: Hostname to match
            connection_id: Optional specific connection ID to use

        Returns:
            Dictionary with connection configuration

        Raises:
            ValueError: If no matching connection found
        """
        root = self._load_xml(db_type)
        
        # Find matching connection
        conn_element = None
        for conn in root.findall("connection"):
            conn_host = self._get_element_text(conn, "host", "")
            conn_id = conn.get("id", "")
            
            # Match by connection_id if provided
            if connection_id and conn_id == connection_id:
                conn_element = conn
                break
            
            # Match by hostname
            if conn_host.lower() == host.lower():
                conn_element = conn
                break
        
        if conn_element is None:
            raise ValueError(f"No connection found for {db_type} host: {host}")
        
        return self._parse_connection(conn_element)

    def _parse_connection(self, conn: ET.Element) -> Dict[str, Any]:
        """Parse a connection element into a dictionary."""
        config: Dict[str, Any] = {
            "id": conn.get("id", ""),
            "type": conn.get("type", ""),
            "auth": conn.get("auth", ""),
            "environment": conn.get("environment", "production"),
        }
        
        # Basic connection info
        config["host"] = self._get_element_text(conn, "host", "")
        config["port"] = int(self._get_element_text(conn, "port", "0"))
        config["description"] = self._get_element_text(conn, "description", "")
        
        # Database-specific fields
        config["service_name"] = self._get_element_text(conn, "service_name", "")
        config["database"] = self._get_element_text(conn, "database", "")
        config["schema"] = self._get_element_text(conn, "schema", "")
        
        # Parse credentials if present
        creds_elem = conn.find("credentials")
        if creds_elem is not None:
            config["username"] = self._get_element_text(creds_elem, "username", "")
            config["password"] = self._get_element_text(creds_elem, "password", "")
        
        # Parse Key Vault config if present
        keyvault_elem = conn.find("keyvault")
        if keyvault_elem is not None:
            config["keyvault"] = {
                "vault_url": self._get_element_text(keyvault_elem, "vault_url", ""),
                "username_secret": self._get_element_text(keyvault_elem, "username_secret", ""),
                "password_secret": self._get_element_text(keyvault_elem, "password_secret", ""),
                "auth_method": self._get_element_text(keyvault_elem, "auth_method", "managed_identity"),
                "tenant_id": self._get_element_text(keyvault_elem, "tenant_id", ""),
                "client_id": self._get_element_text(keyvault_elem, "client_id", ""),
                "client_secret_name": self._get_element_text(keyvault_elem, "client_secret_name", ""),
            }
        
        # Parse Entra ID config if present
        entra_elem = conn.find("entra_id")
        if entra_elem is not None:
            config["entra_id"] = {
                "auth_method": self._get_element_text(entra_elem, "auth_method", ""),
                "tenant_id": self._get_element_text(entra_elem, "tenant_id", ""),
                "client_id": self._get_element_text(entra_elem, "client_id", ""),
                "client_secret": self._get_element_text(entra_elem, "client_secret", ""),
                "username": self._get_element_text(entra_elem, "username", ""),
                "password": self._get_element_text(entra_elem, "password", ""),
                "pg_user": self._get_element_text(entra_elem, "pg_user", ""),
                "oracle_user": self._get_element_text(entra_elem, "oracle_user", ""),
            }
        
        # Parse wallet config if present (Oracle)
        wallet_elem = conn.find("wallet")
        if wallet_elem is not None:
            config["wallet"] = {
                "wallet_location": self._get_element_text(wallet_elem, "wallet_location", ""),
                "tns_alias": self._get_element_text(wallet_elem, "tns_alias", ""),
            }
        
        # Parse certificate config if present
        cert_elem = conn.find("certificate")
        if cert_elem is not None:
            config["certificate"] = {
                "client_cert": self._get_element_text(cert_elem, "client_cert", ""),
                "client_key": self._get_element_text(cert_elem, "client_key", ""),
                "ca_cert": self._get_element_text(cert_elem, "ca_cert", ""),
                "username": self._get_element_text(cert_elem, "username", ""),
            }
        
        # Parse Kerberos config if present
        kerberos_elem = conn.find("kerberos")
        if kerberos_elem is not None:
            config["kerberos"] = {
                "realm": self._get_element_text(kerberos_elem, "realm", ""),
                "service_principal": self._get_element_text(kerberos_elem, "service_principal", ""),
                "keytab": self._get_element_text(kerberos_elem, "keytab", ""),
                "principal": self._get_element_text(kerberos_elem, "principal", ""),
            }
        
        # Parse Windows auth config if present
        windows_elem = conn.find("windows_auth")
        if windows_elem is not None:
            config["windows_auth"] = {
                "trusted_connection": self._get_element_text(windows_elem, "trusted_connection", "no").lower() in ("yes", "true", "1"),
            }
        
        # Parse options
        options_elem = conn.find("options")
        if options_elem is not None:
            config["options"] = {}
            for child in options_elem:
                tag = child.tag
                text = child.text or ""
                # Convert known integer/boolean options
                if tag in ("min_connections", "max_connections", "port", "connection_timeout", "connect_timeout"):
                    config["options"][tag] = int(text) if text else 0
                elif tag in ("thick_mode", "encrypt", "trust_server_certificate", "ssl"):
                    config["options"][tag] = text.lower() in ("yes", "true", "1")
                else:
                    config["options"][tag] = text
        
        return config

    def _get_element_text(self, parent: ET.Element, tag: str, default: str = "") -> str:
        """Get text content of a child element."""
        elem = parent.find(tag)
        return elem.text.strip() if elem is not None and elem.text else default

    def get_credentials(self, db_type: str, host: str, connection_id: Optional[str] = None) -> Dict[str, str]:
        """
        Get resolved credentials for a connection.
        If Key Vault is configured, retrieves secrets from Azure Key Vault.

        Args:
            db_type: Database type (oracle, mssql, postgres, db2)
            host: Hostname to match
            connection_id: Optional specific connection ID

        Returns:
            Dictionary with 'username' and 'password' keys
        """
        config = self.get_connection(db_type, host, connection_id)
        auth_type = config.get("auth", "")
        
        # Handle Key Vault authentication
        if "azure_keyvault" in auth_type or "keyvault" in config:
            return self._resolve_keyvault_credentials(config)
        
        # Handle direct credentials
        if "username" in config and "password" in config:
            return {
                "username": config["username"],
                "password": config["password"],
            }
        
        # Handle Entra ID / Windows Auth (return empty password, auth handled differently)
        if "entra_id" in auth_type or "windows" in auth_type:
            entra_config = config.get("entra_id", {})
            return {
                "username": entra_config.get("username", "") or entra_config.get("pg_user", "") or entra_config.get("oracle_user", ""),
                "password": entra_config.get("password", ""),
                "auth_type": auth_type,
            }
        
        return {"username": "", "password": ""}

    def _resolve_keyvault_credentials(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Resolve credentials from Azure Key Vault."""
        if _AZURE_KEYVAULT_ERROR is not None:
            raise ImportError(
                "Azure Key Vault packages required. Install with: pip install azure-identity azure-keyvault-secrets"
            ) from _AZURE_KEYVAULT_ERROR
        
        kv_config = config.get("keyvault", {})
        vault_url = kv_config.get("vault_url", "")
        
        if not vault_url:
            raise ValueError("Key Vault URL not configured")
        
        # Get or create Key Vault client
        client = self._get_keyvault_client(vault_url, kv_config)
        
        # Retrieve secrets
        username = ""
        password = ""
        
        username_secret = kv_config.get("username_secret", "")
        if username_secret:
            secret = client.get_secret(username_secret)
            username = secret.value or ""
        
        password_secret = kv_config.get("password_secret", "")
        if password_secret:
            secret = client.get_secret(password_secret)
            password = secret.value or ""
        
        return {"username": username, "password": password}

    def _get_keyvault_client(self, vault_url: str, kv_config: Dict[str, Any]) -> "SecretClient":
        """Get or create a Key Vault secret client."""
        if vault_url in self._keyvault_clients:
            return self._keyvault_clients[vault_url]
        
        auth_method = kv_config.get("auth_method", "managed_identity")
        
        if auth_method == "managed_identity":
            client_id = kv_config.get("client_id", "")
            if client_id:
                credential = ManagedIdentityCredential(client_id=client_id)
            else:
                credential = ManagedIdentityCredential()
        elif auth_method == "service_principal":
            tenant_id = kv_config.get("tenant_id", "")
            client_id = kv_config.get("client_id", "")
            # Client secret should be retrieved from environment or another secure source
            client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            # Default to DefaultAzureCredential which tries multiple auth methods
            credential = DefaultAzureCredential()
        
        client = SecretClient(vault_url=vault_url, credential=credential)
        self._keyvault_clients[vault_url] = client
        return client

    def get_connection_for_ini(self, db_type: str, host: str, connection_id: Optional[str] = None) -> Dict[str, str]:
        """
        Get connection configuration formatted for INI file compatibility.
        Resolves all credentials and returns flat key-value pairs.

        Args:
            db_type: Database type (oracle, mssql, postgres, db2)
            host: Hostname to match
            connection_id: Optional specific connection ID

        Returns:
            Dictionary compatible with existing connector INI format
        """
        config = self.get_connection(db_type, host, connection_id)
        credentials = self.get_credentials(db_type, host, connection_id)
        
        # Build INI-compatible config
        ini_config: Dict[str, str] = {
            "host": config.get("host", ""),
            "port": str(config.get("port", "")),
        }
        
        # Add database-specific fields
        if config.get("service_name"):
            ini_config["service_name"] = config["service_name"]
        if config.get("database"):
            ini_config["database"] = config["database"]
        if config.get("schema"):
            ini_config["schema"] = config["schema"]
        
        # Add credentials
        ini_config["username"] = credentials.get("username", "")
        ini_config["password"] = credentials.get("password", "")
        
        # Add options
        options = config.get("options", {})
        for key, value in options.items():
            if isinstance(value, bool):
                ini_config[key] = "yes" if value else "no"
            else:
                ini_config[key] = str(value)
        
        return ini_config


# Convenience function for quick access
def load_connection(db_type: str, host: str, security_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to load a connection configuration.

    Args:
        db_type: Database type (oracle, mssql, postgres, db2)
        host: Hostname to match
        security_dir: Optional path to security directory

    Returns:
        Dictionary with connection configuration
    """
    loader = ConnectionLoader(security_dir)
    return loader.get_connection(db_type, host)


def load_credentials(db_type: str, host: str, security_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to load resolved credentials.

    Args:
        db_type: Database type (oracle, mssql, postgres, db2)
        host: Hostname to match
        security_dir: Optional path to security directory

    Returns:
        Dictionary with username and password
    """
    loader = ConnectionLoader(security_dir)
    return loader.get_credentials(db_type, host)
