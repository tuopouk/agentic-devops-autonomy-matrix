@description('Azure region for resource deployment')
param location string = resourceGroup().location

@description('Log Analytics retention in days (governed by semi-autonomous PR gate)')
@minValue(30)
@maxValue(730)
param retentionInDays int = 90

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'law-contoso-agentic-ops-prod'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

output workspaceId string = logAnalyticsWorkspace.id
