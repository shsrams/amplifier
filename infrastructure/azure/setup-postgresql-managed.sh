#!/bin/bash
# Azure PostgreSQL Setup with Managed Identity Support
# This script creates Azure PostgreSQL with Microsoft Entra authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-amplifier-rg}"
LOCATION="${AZURE_LOCATION:-eastus}"
SERVER_NAME="${AZURE_POSTGRES_SERVER:-amplifier-postgres-$(date +%s)}"
DATABASE_NAME="${AZURE_DATABASE_NAME:-knowledge_os}"
SKU="${AZURE_SKU:-B_Standard_B1ms}"
USE_MANAGED_IDENTITY="${AZURE_USE_MANAGED_IDENTITY:-true}"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if Azure CLI is installed
check_prerequisites() {
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it first:"
        echo "  Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
        print_error "Not logged in to Azure. Please run: az login"
        exit 1
    fi

    print_info "Azure CLI is installed and authenticated"
}

# Get current user's Azure AD object ID
get_current_user_id() {
    local user_id=$(az ad signed-in-user show --query id --output tsv 2>/dev/null)
    if [ -z "$user_id" ]; then
        print_warning "Could not get current user ID. You may need to configure admin manually."
        echo ""
    else
        echo "$user_id"
    fi
}

# Get current user's display name
get_current_user_name() {
    local user_name=$(az ad signed-in-user show --query displayName --output tsv 2>/dev/null)
    if [ -z "$user_name" ]; then
        echo "Admin User"
    else
        echo "$user_name"
    fi
}

# Get current client IP
get_client_ip() {
    curl -s https://api.ipify.org 2>/dev/null || echo ""
}

# Create resource group
create_resource_group() {
    print_info "Creating resource group: $RESOURCE_GROUP in $LOCATION"
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output none
}

# Deploy PostgreSQL with managed identity
deploy_postgresql_managed() {
    local client_ip="$1"
    local admin_object_id="$2"
    local admin_name="$3"
    
    print_info "Deploying PostgreSQL server with Microsoft Entra authentication: $SERVER_NAME"
    print_info "This may take 5-10 minutes..."
    
    # Deploy the Bicep template
    deployment_output=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$(dirname "$0")/postgresql-managed-identity.bicep" \
        --parameters \
            serverName="$SERVER_NAME" \
            databaseName="$DATABASE_NAME" \
            clientIPAddress="$client_ip" \
            enableEntraAuth=true \
            entraAdminObjectId="$admin_object_id" \
            entraAdminPrincipalName="$admin_name" \
            entraAdminPrincipalType="User" \
        --query properties.outputs \
        --output json)
    
    echo "$deployment_output"
}

# Save connection details for managed identity
save_managed_identity_config() {
    local server_fqdn="$1"
    local env_file="${2:-.env}"
    
    print_info "Saving managed identity configuration to $env_file"
    
    # Create .env if it doesn't exist
    if [ ! -f "$env_file" ]; then
        touch "$env_file"
    fi
    
    # Save individual connection parameters for managed identity
    cat >> "$env_file" << EOF

# Azure PostgreSQL with Managed Identity
AZURE_AUTH_METHOD=managed_identity
AZURE_POSTGRESQL_HOST=$server_fqdn
AZURE_POSTGRESQL_NAME=$DATABASE_NAME
AZURE_POSTGRESQL_USER=your-managed-identity-name
AZURE_POSTGRESQL_PORT=5432
AZURE_POSTGRESQL_SSLMODE=require
# For user-assigned managed identity (optional):
# AZURE_POSTGRESQL_CLIENTID=your-managed-identity-client-id
EOF
    
    # Save to Azure config file
    cat > .azure-postgresql.env << EOF
# Azure PostgreSQL Configuration with Managed Identity
# Generated on $(date)
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_LOCATION=$LOCATION
AZURE_POSTGRES_SERVER=$SERVER_NAME
AZURE_DATABASE_NAME=$DATABASE_NAME
AZURE_AUTH_METHOD=managed_identity
AZURE_POSTGRESQL_HOST=$server_fqdn
EOF
}

# Create database user for managed identity
setup_managed_identity_user() {
    local server_fqdn="$1"
    local identity_name="${2:-$AZURE_MANAGED_IDENTITY_NAME}"
    
    if [ -z "$identity_name" ]; then
        print_warning "No managed identity name provided. Skipping database user creation."
        print_info "You'll need to create a database user for your managed identity manually:"
        print_info "  CREATE USER \"your-identity-name\" WITH LOGIN IN ROLE azure_ad_user;"
        return
    fi
    
    print_info "Creating database user for managed identity: $identity_name"
    
    # This requires the current user to be the Entra admin
    az postgres flexible-server execute \
        --admin-user "current_user" \
        --admin-password "" \
        --name "$SERVER_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --database-name "$DATABASE_NAME" \
        --query-text "CREATE USER \"$identity_name\" WITH LOGIN IN ROLE azure_ad_user;" \
        2>/dev/null || print_warning "Could not create database user automatically. Create it manually after setup."
}

# Main execution
main() {
    print_info "Starting Azure PostgreSQL setup with Managed Identity for Amplifier"
    
    # Check prerequisites
    check_prerequisites
    
    # Get current user info for Entra admin
    ADMIN_OBJECT_ID=$(get_current_user_id)
    ADMIN_NAME=$(get_current_user_name)
    
    if [ -z "$ADMIN_OBJECT_ID" ]; then
        print_error "Could not determine current user's Azure AD object ID"
        print_info "You can set it manually: export AZURE_ADMIN_OBJECT_ID=<your-object-id>"
        exit 1
    fi
    
    print_info "Setting up Microsoft Entra admin: $ADMIN_NAME"
    
    # Get client IP for firewall rule
    CLIENT_IP=$(get_client_ip)
    if [ -z "$CLIENT_IP" ]; then
        print_warning "Could not detect client IP. You may need to add it manually in Azure Portal."
    else
        print_info "Detected client IP: $CLIENT_IP"
    fi
    
    # Create resource group
    create_resource_group
    
    # Deploy PostgreSQL with managed identity
    deployment_output=$(deploy_postgresql_managed "$CLIENT_IP" "$ADMIN_OBJECT_ID" "$ADMIN_NAME")
    
    # Extract outputs
    server_fqdn=$(echo "$deployment_output" | jq -r '.serverFQDN.value')
    auth_method=$(echo "$deployment_output" | jq -r '.authMethod.value')
    
    print_info "PostgreSQL server created successfully!"
    print_info "Server FQDN: $server_fqdn"
    print_info "Database: $DATABASE_NAME"
    print_info "Authentication: $auth_method"
    
    # Save configuration
    save_managed_identity_config "$server_fqdn"
    
    # Setup database user for managed identity
    if [ -n "$AZURE_MANAGED_IDENTITY_NAME" ]; then
        setup_managed_identity_user "$server_fqdn" "$AZURE_MANAGED_IDENTITY_NAME"
    fi
    
    print_info "Setup complete!"
    print_info ""
    print_info "Next steps:"
    print_info "  1. If using App Service/Container Apps:"
    print_info "     - Enable managed identity on your service"
    print_info "     - Set AZURE_POSTGRESQL_USER to your identity name"
    print_info "  2. Create database user for your managed identity:"
    print_info "     CREATE USER \"your-identity-name\" WITH LOGIN IN ROLE azure_ad_user;"
    print_info "  3. Grant permissions to the user:"
    print_info "     GRANT ALL ON DATABASE $DATABASE_NAME TO \"your-identity-name\";"
    print_info ""
    print_info "To delete these resources later, run:"
    print_info "  az group delete --name $RESOURCE_GROUP --yes"
}

# Run main function
main "$@"