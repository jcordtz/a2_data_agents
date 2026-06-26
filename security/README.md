# Security Configuration

This directory contains XML configuration files for database connections with various authentication methods.

> **⚠️ WARNING**: These files contain sensitive connection information. Never commit actual credentials to version control. Use environment variables, Azure Key Vault, or other secrets management solutions for production deployments.

## Files

| File | Database | Description |
|------|----------|-------------|
| [oracle_connections.xml](oracle_connections.xml) | Oracle | Oracle database connections |
| [mssql_connections.xml](mssql_connections.xml) | SQL Server | Microsoft SQL Server connections |
| [postgres_connections.xml](postgres_connections.xml) | PostgreSQL | PostgreSQL database connections |
| [ibmdb2_connections.xml](ibmdb2_connections.xml) | IBM DB2 | IBM DB2 LUW database connections |

## Supported Authentication Methods

### Oracle

| Method | Description | Use Case |
|--------|-------------|----------|
| `password` | Traditional username/password | On-premises, simple setups |
| `azure_keyvault` | Credentials stored in Azure Key Vault | Azure deployments, centralized secrets |
| `wallet` | Oracle Wallet authentication | Enterprise Oracle, Auto-Login wallets |
| `entra_id` | Azure AD for Oracle Autonomous DB | Oracle ADB with Azure AD integration |

### Microsoft SQL Server

| Method | Description | Use Case |
|--------|-------------|----------|
| `sql_password` | SQL Server authentication | On-premises, simple setups |
| `windows_integrated` | Windows/AD integrated auth | Domain-joined servers |
| `azure_keyvault` | Credentials from Key Vault | Azure deployments |
| `entra_id_interactive` | Azure AD with user sign-in | Development, interactive apps |
| `entra_id_service_principal` | Azure AD service principal | Automated services |
| `entra_id_managed_identity` | Azure Managed Identity | Azure-hosted applications |
| `entra_id_password` | Azure AD with username/password | Non-interactive Azure AD |

### PostgreSQL

| Method | Description | Use Case |
|--------|-------------|----------|
| `password` | Traditional username/password | On-premises, simple setups |
| `azure_keyvault` | Credentials from Key Vault | Azure deployments |
| `certificate` | Client certificate authentication | High-security environments |
| `scram` | SCRAM-SHA-256 enhanced password | Enhanced password security |
| `entra_id_managed_identity` | Azure AD Managed Identity | Azure Database for PostgreSQL |
| `entra_id_service_principal` | Azure AD service principal | Automated services |
| `entra_id_interactive` | Azure AD interactive | Development, interactive apps |

### IBM DB2

| Method | Description | Use Case |
|--------|-------------|----------|
| `password` | Traditional username/password | On-premises, simple setups |
| `azure_keyvault` | Credentials from Key Vault | Azure deployments |
| `kerberos` | Kerberos/AD authentication | Enterprise AD environments |
| `certificate` | Client certificate (GSKit) | High-security environments |
| `ibm_iam` | IBM Cloud IAM | DB2 on IBM Cloud |
| `plugin` | Custom security plugins | Enterprise custom auth |

## Azure Key Vault Integration

All databases support Azure Key Vault for secure credential storage:

```xml
<keyvault>
    <vault_url>https://your-vault.vault.azure.net/</vault_url>
    <username_secret>db-username-secret</username_secret>
    <password_secret>db-password-secret</password_secret>
    
    <!-- Authentication options -->
    <auth_method>managed_identity</auth_method>
    <!-- OR -->
    <auth_method>service_principal</auth_method>
    <tenant_id>your-tenant-id</tenant_id>
    <client_id>your-client-id</client_id>
    <client_secret_name>sp-client-secret</client_secret_name>
</keyvault>
```

### Key Vault Authentication Methods

1. **Managed Identity** (recommended for Azure-hosted apps):
   - System-assigned: No configuration needed
   - User-assigned: Specify `client_id`

2. **Service Principal**:
   - Requires `tenant_id`, `client_id`, and `client_secret`
   - Store the client secret in Key Vault itself for additional security

## Best Practices

1. **Never commit real credentials** - Use placeholders in version control
2. **Use Key Vault** - Store all production credentials in Azure Key Vault
3. **Use Managed Identity** - Preferred for Azure-hosted applications
4. **Enable SSL/TLS** - Always use encrypted connections in production
5. **Least privilege** - Create database users with minimal required permissions
6. **Rotate credentials** - Implement regular credential rotation
7. **Audit access** - Enable database auditing and Key Vault logging

## ConnectionLoader Module

The `connection_loader.py` module provides programmatic access to connection configurations from XML files.

### Usage

```python
from security.connection_loader import ConnectionLoader

# Initialize with default security directory
loader = ConnectionLoader()

# Get full connection details
conn = loader.get_connection("oracle", "db.example.com")
print(conn)  # {'host': 'db.example.com', 'port': 1521, 'service_name': 'ORCL', ...}

# Get just credentials (resolves Key Vault secrets if needed)
creds = loader.get_credentials("oracle", "db.example.com")
print(creds)  # {'username': 'hr_user', 'password': 'actual_password'}

# Get config in INI-compatible format
config = loader.get_connection_for_ini("postgres", "analytics.example.com")
```

### Using with Database Connectors

All database connectors require XML-based configuration via the `from_host()` class method:

```python
from databases.oracle.oracle_connector import OracleConnector
from databases.mssql.mssql_connector import MSSQLConnector
from databases.postgres.postgres_connector import PostgresConnector
from databases.ibmdb2.ibmdb2_connector import IBMDB2Connector

# Create connector by hostname lookup
oracle_conn = OracleConnector.from_host("db.example.com")
mssql_conn = MSSQLConnector.from_host("sql.example.com")
postgres_conn = PostgresConnector.from_host("analytics.example.com")
db2_conn = IBMDB2Connector.from_host("warehouse.example.com")

# Specify a particular connection ID if multiple connections exist for the same host
connector = OracleConnector.from_host(
    "db.example.com", 
    connection_id="oracle_db_example_hr_keyvault"
)

# Use a custom security directory
connector = PostgresConnector.from_host(
    "sales-db.example.com",
    security_dir="/path/to/custom/security"
)
```

### Connection Lookup Logic

When looking up a connection by hostname:

1. The loader searches all `<connection>` elements in the database-specific XML file
2. If multiple connections match the hostname, the first match is returned
3. Optionally specify a `connection_id` to select a specific connection
4. Key Vault credentials are automatically resolved when using `get_credentials()` or `get_connection_for_ini()`

### Key Vault Integration

The ConnectionLoader automatically handles Azure Key Vault credential resolution:

```python
# Credentials are fetched from Key Vault transparently
creds = loader.get_credentials("mssql", "sql.example.com")
# Returns: {'username': 'actual_user', 'password': 'secret_from_keyvault'}
```

Supported Key Vault authentication methods:
- **Managed Identity** (default) - Uses `DefaultAzureCredential`
- **Service Principal** - Specify `tenant_id`, `client_id`, and `client_secret`

## Environment-Specific Configurations

Each connection can specify an `environment` attribute:

```xml
<connection id="db_dev" type="oracle" auth="password" environment="development">
    <!-- Development settings -->
</connection>

<connection id="db_prod" type="oracle" auth="azure_keyvault" environment="production">
    <!-- Production settings with Key Vault -->
</connection>
```

## License

MIT License - Copyright (c) 2026
