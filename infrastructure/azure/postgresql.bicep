@description('The name of the PostgreSQL server')
param serverName string

@description('The location for all resources')
param location string = resourceGroup().location

@description('Administrator username for PostgreSQL')
param administratorLogin string = 'pgadmin'

@secure()
@description('Administrator password for PostgreSQL')
param administratorPassword string

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

resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: serverName
  location: location
  sku: {
    name: skuName
    tier: 'Burstable'
  }
  properties: {
    version: version
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
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
output connectionString string = 'postgresql://${administratorLogin}:${administratorPassword}@${postgresqlServer.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'