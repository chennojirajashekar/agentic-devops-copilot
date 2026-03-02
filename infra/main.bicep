// ============================================================
// Agentic DevOps Copilot - Azure Infrastructure (Bicep)
// Deploys: AI Foundry Hub + Project, Azure OpenAI, Log Analytics
// ============================================================

@description('Location for all resources')
param location string = resourceGroup().location

@description('Project name prefix')
param projectName string = 'agentic-devops'

@description('Azure OpenAI model deployment name')
param openAIModelName string = 'gpt-4o'

@description('Azure OpenAI model version')
param openAIModelVersion string = '2024-08-06'

var uniqueSuffix = uniqueString(resourceGroup().id)
var openAIName = '${projectName}-oai-${uniqueSuffix}'
var workspaceName = '${projectName}-logs-${uniqueSuffix}'
var appInsightsName = '${projectName}-insights-${uniqueSuffix}'
var storageAccountName = replace('${projectName}sa${uniqueSuffix}', '-', '')
var keyVaultName = '${projectName}-kv-${take(uniqueSuffix, 6)}'

// ============================================================
// Log Analytics Workspace
// ============================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ============================================================
// Application Insights
// ============================================================
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ============================================================
// Azure OpenAI Service
// ============================================================
resource openAI 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: openAIName
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: openAIName
    publicNetworkAccess: 'Enabled'
  }
}

// GPT-4o deployment
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAI
  name: openAIModelName
  sku: { name: 'GlobalStandard', capacity: 10 }
  properties: {
    model: {
      format: 'OpenAI'
      name: openAIModelName
      version: openAIModelVersion
    }
  }
}

// ============================================================
// Storage Account (for Foundry shared storage)
// ============================================================
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: take(storageAccountName, 24)
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: { minimumTlsVersion: 'TLS1_2' }
}

// ============================================================
// Key Vault (for secrets)
// ============================================================
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    softDeleteRetentionInDays: 7
  }
}

// ============================================================
// Outputs
// ============================================================
output openAIEndpoint string = openAI.properties.endpoint
output openAIName string = openAI.name
output logAnalyticsWorkspaceId string = logAnalytics.properties.customerId
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output keyVaultUri string = keyVault.properties.vaultUri
output storageAccountName string = storageAccount.name
