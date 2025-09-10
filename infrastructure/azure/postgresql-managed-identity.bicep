@description('The name of the PostgreSQL server')
param serverName string

@description('The location for all resources')
param location string = resourceGroup().location

@description('The name of the database to create')
param databaseName string = 'knowledge_os'

@description('PostgreSQL version')
param version string = '15'

@description('SKU for the PostgreSQL server')
param skuName string = 'B_Standard_B1ms'

@description('Storage size in GB')
param storageSizeGB int = 32

@description('Backup retention days')
param backupRetentionDays int = 7

@description('Client IP address to allow')
param clientIPAddress string = ''

@description('Enable Microsoft Entra authentication')
param enableEntraAuth bool = true

@description('Microsoft Entra admin object ID (user or service principal)')
param entraAdminObjectId string = ''

@description('Microsoft Entra admin principal name')
param entraAdminPrincipalName string = ''

@description('Microsoft Entra admin principal type (User, Group, or ServicePrincipal)')
@allowed([
  'User'
  'Group'
  'ServicePrincipal'
])
param entraAdminPrincipalType string = 'User'

resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: serverName
  location: location
  sku: {
    name: skuName
    tier: 'Burstable'
  }
  properties: {
    version: version
    authConfig: {
      activeDirectoryAuth: enableEntraAuth ? 'Enabled' : 'Disabled'
      passwordAuth: 'Enabled' // Keep enabled as fallback
      tenantId: subscription().tenantId
    }
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

// Configure Microsoft Entra administrator if enabled
resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2023-06-01-preview' = if (enableEntraAuth && entraAdminObjectId != '') {
  parent: postgresqlServer
  name: entraAdminObjectId
  properties: {
    principalType: entraAdminPrincipalType
    principalName: entraAdminPrincipalName
    tenantId: subscription().tenantId
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgresqlServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.UTF8'
  }
}

// Allow Azure services
resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgresqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Allow client IP if provided
resource allowClientIP 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = if (clientIPAddress != '') {
  parent: postgresqlServer
  name: 'AllowClientIP'
  properties: {
    startIpAddress: clientIPAddress
    endIpAddress: clientIPAddress
  }
}

output serverName string = postgresqlServer.name
output serverFQDN string = postgresqlServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
output authMethod string = enableEntraAuth ? 'ManagedIdentity' : 'Password'
output entraEnabled bool = enableEntraAuth