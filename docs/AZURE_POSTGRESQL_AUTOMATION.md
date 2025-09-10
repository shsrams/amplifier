# Automated Azure PostgreSQL Setup

This guide provides fully automated setup of Azure PostgreSQL for Amplifier.

## Prerequisites

1. **Azure CLI** installed: [Installation Guide](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **Azure Account** with active subscription
3. **Logged in** to Azure CLI: `az login`

## Quick Start (2 minutes!)

### Option 1: Managed Identity (Recommended - No Passwords!)

```bash
# Create with managed identity authentication
make azure-create-managed

# Configure your app's managed identity
# See docs/AZURE_POSTGRESQL_MANAGED_IDENTITY.md for details
```

### Option 2: Password Authentication (Simple Setup)

```bash
# Create with traditional password auth
make azure-create

# Initialize database schema
make setup-db

# Done! Your database is ready
```

### Option 2: Customized Setup

```bash
# Set custom values (optional)
export AZURE_RESOURCE_GROUP=my-rg
export AZURE_LOCATION=westus2
export AZURE_POSTGRES_SERVER=my-postgres-server

# Create infrastructure
make azure-create

# Initialize database
make setup-db
```

## What Gets Created

The automation creates:
- **Resource Group**: Container for all resources
- **PostgreSQL Flexible Server**: Burstable B1ms tier (~$12-15/month)
- **Database**: `knowledge_os` database
- **Firewall Rules**: 
  - Allow Azure services
  - Allow your current IP address
- **SSL**: Enforced for all connections

## Available Commands

```bash
make azure-create    # Create all Azure resources
make azure-status    # Check resource status
make azure-teardown  # Delete all Azure resources

make setup-db        # Initialize database schema
make validate-db     # Validate schema integrity
make reset-db        # Reset database (deletes data!)
make db-status       # Check database connection
```

## Configuration Files

After running `make azure-create`, two files are created:

1. **`.env`** - Contains `DATABASE_URL` for application use
2. **`.azure-postgresql.env`** - Contains Azure resource details for management

## Cost Management

### Development Usage (~$12-15/month)
- Burstable B1ms tier
- 32GB storage
- No high availability

### Stop Server When Not Using
```bash
# Stop server to save costs
az postgres flexible-server stop \
  --resource-group amplifier-rg \
  --name your-server-name

# Restart when needed
az postgres flexible-server start \
  --resource-group amplifier-rg \
  --name your-server-name
```

## Teardown

To completely remove all Azure resources:

```bash
# This will DELETE everything!
make azure-teardown
```

## Troubleshooting

### Connection Issues
```bash
# Check server status
make azure-status

# Add current IP to firewall
az postgres flexible-server firewall-rule create \
  --resource-group amplifier-rg \
  --name your-server-name \
  --rule-name AllowMyIP \
  --start-ip-address $(curl -s https://api.ipify.org) \
  --end-ip-address $(curl -s https://api.ipify.org)
```

### Reset Everything
```bash
# Delete Azure resources
make azure-teardown

# Start fresh
make azure-create
make setup-db
```

## Environment Variables

The automation respects these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_RESOURCE_GROUP` | `amplifier-rg` | Resource group name |
| `AZURE_LOCATION` | `eastus` | Azure region |
| `AZURE_POSTGRES_SERVER` | `amplifier-postgres-{timestamp}` | Server name |
| `AZURE_DATABASE_NAME` | `knowledge_os` | Database name |
| `AZURE_ADMIN_USER` | `pgadmin` | Admin username |
| `AZURE_ADMIN_PASSWORD` | (generated) | Admin password |
| `AZURE_SKU` | `B_Standard_B1ms` | Server tier |

## Manual Azure Portal Steps (If Automation Fails)

If automation fails, see [AZURE_POSTGRESQL_SETUP.md](AZURE_POSTGRESQL_SETUP.md) for manual setup instructions.