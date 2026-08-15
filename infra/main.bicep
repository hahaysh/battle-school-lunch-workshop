targetScope = 'subscription'

@description('The azd environment name.')
param environmentName string

@description('The Azure region for all resources.')
param location string

@secure()
@description('The NEIS API key stored in Key Vault.')
param neisApiKey string

var tags = {
  'azd-env-name': environmentName
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module resources './modules/resources.bicep' = {
  name: 'resources'
  scope: resourceGroup
  params: {
    environmentName: environmentName
    location: location
    neisApiKey: neisApiKey
    tags: tags
  }
}

output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.containerRegistryEndpoint
output AZURE_KEY_VAULT_NAME string = resources.outputs.keyVaultName
output API_URL string = resources.outputs.apiUrl
output WEB_URL string = resources.outputs.webUrl
output MCP_URL string = resources.outputs.mcpUrl
