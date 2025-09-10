# Azure PostgreSQL with Managed Identity Authentication

This guide explains how to set up Azure PostgreSQL with **passwordless authentication** using managed identities - the recommended security best practice.

## Why Managed Identity?

✅ **No passwords to manage** - Eliminates password storage, rotation, and exposure risks  
✅ **Automatic credential management** - Azure handles token generation and renewal  
✅ **Superior security** - No credentials in code, config files, or environment variables  
✅ **Audit compliance** - Full Azure AD audit trail of database access  

## Quick Start

### Option 1: Fully Automated Setup (Recommended)

```bash
# Create PostgreSQL with managed identity authentication
make azure-create-managed

# Install azure-identity for Python support (optional)
uv add --group azure azure-identity

# Configure your app (see below)
```

### Option 2: Manual Setup with Azure CLI

```bash
# Set your configuration
export RESOURCE_GROUP=amplifier-rg
export SERVER_NAME=amplifier-postgres
export LOCATION=eastus

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create PostgreSQL with Azure AD auth enabled
az postgres flexible-server create \
  --name $SERVER_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --tier Burstable \
  --sku-name B_Standard_B1ms \
  --storage-size 32 \
  --version 15 \
  --active-directory-auth Enabled \
  --password-auth Enabled

# Set yourself as Azure AD admin
USER_ID=$(az ad signed-in-user show --query id -o tsv)
az postgres flexible-server ad-admin create \
  --server-name $SERVER_NAME \
  --resource-group $RESOURCE_GROUP \
  --object-id $USER_ID \
  --display-name "Admin User"
```

## Application Configuration

### 1. App Service / Container Apps

Enable system-assigned managed identity:
```bash
az webapp identity assign --name your-app --resource-group your-rg
```

Set environment variables:
```bash
az webapp config appsettings set --name your-app --resource-group your-rg --settings \
  AZURE_AUTH_METHOD=managed_identity \
  AZURE_POSTGRESQL_HOST=your-server.postgres.database.azure.com \
  AZURE_POSTGRESQL_NAME=knowledge_os \
  AZURE_POSTGRESQL_USER=your-app
```

### 2. Azure Functions

Enable managed identity in function app:
```bash
az functionapp identity assign --name your-function --resource-group your-rg
```

### 3. Local Development

For local development, use Azure CLI credentials:
```bash
# Login to Azure
az login

# Set environment for local dev
export AZURE_AUTH_METHOD=auto  # Falls back to Azure CLI auth
export AZURE_POSTGRESQL_HOST=your-server.postgres.database.azure.com
export AZURE_POSTGRESQL_NAME=knowledge_os
export AZURE_POSTGRESQL_USER=your-email@domain.com
```

## Database User Setup

After creating your PostgreSQL server, create a database user for your managed identity:

### For System-Assigned Managed Identity

```sql
-- Connect as Azure AD admin
psql "host=your-server.postgres.database.azure.com dbname=postgres user=admin@domain.com"

-- Create user for managed identity (use your app's name)
CREATE USER "your-app-name" WITH LOGIN IN ROLE azure_ad_user;
GRANT ALL PRIVILEGES ON DATABASE knowledge_os TO "your-app-name";

-- Grant schema permissions
\c knowledge_os
GRANT ALL ON SCHEMA public TO "your-app-name";
```

### For User-Assigned Managed Identity

```sql
-- Use the managed identity's name
CREATE USER "your-managed-identity-name" WITH LOGIN IN ROLE azure_ad_user;
GRANT ALL PRIVILEGES ON DATABASE knowledge_os TO "your-managed-identity-name";
```

## Python Code Examples

### Basic Connection

```python
from azure.identity import DefaultAzureCredential
import psycopg2
import os

# Get access token
credential = DefaultAzureCredential()
token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")

# Connect using token as password
conn = psycopg2.connect(
    host=os.getenv("AZURE_POSTGRESQL_HOST"),
    database=os.getenv("AZURE_POSTGRESQL_NAME"),
    user=os.getenv("AZURE_POSTGRESQL_USER"),
    password=token.token,
    sslmode="require"
)
```

### Using the Enhanced Connection Module

```python
# With our enhanced connection module (connection_managed_identity.py)
from db_setup.connection_managed_identity import connect

# Automatically uses managed identity if available
conn = connect()
```

### Django Configuration

```python
# settings.py
from azure.identity import DefaultAzureCredential

def get_db_password():
    if os.getenv("AZURE_AUTH_METHOD") == "managed_identity":
        credential = DefaultAzureCredential()
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token
    return os.getenv("DATABASE_PASSWORD")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('AZURE_POSTGRESQL_HOST'),
        'NAME': os.getenv('AZURE_POSTGRESQL_NAME'),
        'USER': os.getenv('AZURE_POSTGRESQL_USER'),
        'PASSWORD': get_db_password(),
        'OPTIONS': {'sslmode': 'require'},
    }
}
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_AUTH_METHOD` | Authentication method | `managed_identity` or `password` or `auto` |
| `AZURE_POSTGRESQL_HOST` | Server FQDN | `server.postgres.database.azure.com` |
| `AZURE_POSTGRESQL_NAME` | Database name | `knowledge_os` |
| `AZURE_POSTGRESQL_USER` | Identity name or email | `my-app` or `user@domain.com` |
| `AZURE_POSTGRESQL_CLIENTID` | User-assigned identity client ID | `uuid` (optional) |

## Troubleshooting

### "Token authentication failed"
- Ensure managed identity is enabled on your service
- Verify the database user was created correctly
- Check the user name matches exactly (case-sensitive)

### "azure-identity not installed"
```bash
# Install the azure-identity package
uv add --group azure azure-identity
# or
pip install azure-identity
```

### Local Development Issues
- Ensure you're logged in: `az login`
- Check your Azure subscription: `az account show`
- Verify you have database access permissions

### Connection Timeouts
- Add firewall rule for Azure services
- Check network security groups if using VNet

## Security Best Practices

1. **Never use passwords in production** - Always prefer managed identity
2. **Use user-assigned identities** for shared resources across multiple apps
3. **Grant minimal permissions** - Use specific database roles, not admin
4. **Enable audit logging** - Track all database access
5. **Use Private Endpoints** for network isolation (advanced)

## Cost Considerations

Managed identity authentication has **no additional cost** beyond the PostgreSQL server itself. You get superior security without extra charges.

## Migration from Password Authentication

To migrate existing password-based connections:

1. Enable Azure AD auth on your server (keeps password auth as fallback)
2. Create database users for managed identities
3. Update application configuration to use `AZURE_AUTH_METHOD=managed_identity`
4. Test thoroughly
5. Disable password authentication once stable

## Further Reading

- [Microsoft Entra authentication for PostgreSQL](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-azure-ad-authentication)
- [Managed Identities Overview](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)
- [Azure.Identity Python SDK](https://pypi.org/project/azure-identity/)