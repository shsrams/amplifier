#!/bin/bash
# Azure PostgreSQL Teardown Script
# This script removes the Azure PostgreSQL resources created by setup-postgresql.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Load configuration from .azure-postgresql.env if it exists
load_config() {
    if [ -f .azure-postgresql.env ]; then
        print_info "Loading configuration from .azure-postgresql.env"
        source .azure-postgresql.env
    elif [ -f ../.azure-postgresql.env ]; then
        print_info "Loading configuration from ../.azure-postgresql.env"
        source ../.azure-postgresql.env
    else
        print_error "No .azure-postgresql.env file found"
        print_error "Please specify resource group manually: $0 <resource-group-name>"
        exit 1
    fi
}

# Main function
main() {
    # Check if resource group was provided as argument
    if [ $# -eq 1 ]; then
        RESOURCE_GROUP="$1"
    else
        load_config
    fi
    
    if [ -z "$AZURE_RESOURCE_GROUP" ]; then
        AZURE_RESOURCE_GROUP="$RESOURCE_GROUP"
    fi
    
    if [ -z "$AZURE_RESOURCE_GROUP" ]; then
        print_error "Resource group not specified"
        echo "Usage: $0 [resource-group-name]"
        echo "Or ensure .azure-postgresql.env exists with AZURE_RESOURCE_GROUP set"
        exit 1
    fi
    
    print_warning "This will DELETE the following Azure resources:"
    print_warning "  Resource Group: $AZURE_RESOURCE_GROUP"
    print_warning "  And ALL resources within it"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        print_info "Teardown cancelled"
        exit 0
    fi
    
    print_info "Deleting resource group: $AZURE_RESOURCE_GROUP"
    print_info "This may take a few minutes..."
    
    if az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait; then
        print_info "Resource group deletion initiated"
        print_info "Resources are being deleted in the background"
        
        # Clean up local configuration files
        if [ -f .azure-postgresql.env ]; then
            rm .azure-postgresql.env
            print_info "Removed .azure-postgresql.env"
        fi
        
        # Remove DATABASE_URL from .env if it exists
        if [ -f .env ]; then
            sed -i.bak '/^DATABASE_URL=/d' .env
            rm -f .env.bak
            print_info "Removed DATABASE_URL from .env"
        fi
        
        print_info "Teardown complete!"
    else
        print_error "Failed to delete resource group"
        exit 1
    fi
}

# Run main function
main "$@"