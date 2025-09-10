#!/bin/bash
# Azure PostgreSQL Setup Automation Script
# This script automates the creation of Azure PostgreSQL for Amplifier

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
ADMIN_USER="${AZURE_ADMIN_USER:-pgadmin}"
SKU="${AZURE_SKU:-B_Standard_B1ms}"

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

# Generate a secure password
generate_password() {
    # Generate a 20-character password with special characters
    local password=$(openssl rand -base64 20 | tr -d "=+/" | cut -c1-16)
    echo "${password}!Aa1"  # Ensure it meets Azure requirements
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

# Deploy PostgreSQL using Bicep
deploy_postgresql() {
    local password="$1"
    local client_ip="$2"
    
    print_info "Deploying PostgreSQL server: $SERVER_NAME"
    print_info "This may take 5-10 minutes..."
    
    # Deploy the Bicep template
    deployment_output=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$(dirname "$0")/postgresql.bicep" \
        --parameters \
            serverName="$SERVER_NAME" \
            administratorLogin="$ADMIN_USER" \
            administratorPassword="$password" \
            databaseName="$DATABASE_NAME" \
            clientIPAddress="$client_ip" \
        --query properties.outputs \
        --output json)
    
    echo "$deployment_output"
}

# Save connection details to .env file
save_connection_details() {
    local connection_string="$1"
    local env_file="${2:-.env}"
    
    print_info "Saving connection details to $env_file"
    
    # Create .env if it doesn't exist
    if [ ! -f "$env_file" ]; then
        touch "$env_file"
    fi
    
    # Check if DATABASE_URL already exists
    if grep -q "^DATABASE_URL=" "$env_file"; then
        # Update existing
        sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$connection_string|" "$env_file"
        rm -f "${env_file}.bak"
    else
        # Add new
        echo "DATABASE_URL=$connection_string" >> "$env_file"
    fi
    
    # Also save to a dedicated Azure config file
    cat > .azure-postgresql.env << EOF
# Azure PostgreSQL Configuration
# Generated on $(date)
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_LOCATION=$LOCATION
AZURE_POSTGRES_SERVER=$SERVER_NAME
AZURE_DATABASE_NAME=$DATABASE_NAME
AZURE_ADMIN_USER=$ADMIN_USER
DATABASE_URL=$connection_string
EOF
}

# Main execution
main() {
    print_info "Starting Azure PostgreSQL setup for Amplifier"
    
    # Check prerequisites
    check_prerequisites
    
    # Get client IP for firewall rule
    CLIENT_IP=$(get_client_ip)
    if [ -z "$CLIENT_IP" ]; then
        print_warning "Could not detect client IP. You may need to add it manually in Azure Portal."
    else
        print_info "Detected client IP: $CLIENT_IP"
    fi
    
    # Generate secure password
    if [ -z "$AZURE_ADMIN_PASSWORD" ]; then
        ADMIN_PASSWORD=$(generate_password)
        print_info "Generated secure password for admin user"
    else
        ADMIN_PASSWORD="$AZURE_ADMIN_PASSWORD"
        print_info "Using provided admin password"
    fi
    
    # Create resource group
    create_resource_group
    
    # Deploy PostgreSQL
    deployment_output=$(deploy_postgresql "$ADMIN_PASSWORD" "$CLIENT_IP")
    
    # Extract connection string from deployment output
    connection_string=$(echo "$deployment_output" | jq -r '.connectionString.value')
    server_fqdn=$(echo "$deployment_output" | jq -r '.serverFQDN.value')
    
    print_info "PostgreSQL server created successfully!"
    print_info "Server FQDN: $server_fqdn"
    print_info "Database: $DATABASE_NAME"
    
    # Save connection details
    save_connection_details "$connection_string"
    
    print_info "Setup complete! Connection details saved to .env and .azure-postgresql.env"
    print_info ""
    print_info "Next steps:"
    print_info "  1. Review the connection details in .env"
    print_info "  2. Run 'make setup-db' to initialize the database schema"
    print_info ""
    print_info "To delete these resources later, run:"
    print_info "  az group delete --name $RESOURCE_GROUP --yes"
}

# Run main function
main "$@"