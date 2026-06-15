targetScope = 'resourceGroup'

@description('Name of the Azure Cost Management budget.')
param name string

@description('Monthly budget amount in USD for the workshop resource group.')
@minValue(1)
param amount int

@description('Budget start date. Azure requires the first day of a month in ISO 8601 format.')
param startDate string

@description('Email recipients for budget alerts. Required by Azure Consumption budgets at resource-group scope.')
param contactEmails array

@description('Budget time grain.')
@allowed([
  'Monthly'
  'Quarterly'
  'Annually'
])
param timeGrain string = 'Monthly'

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: name
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: timeGrain
    timePeriod: {
      startDate: startDate
    }
    notifications: {
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: contactEmails
        contactGroups: []
        contactRoles: []
        locale: 'en-us'
      }
      Forecasted_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: contactEmails
        contactGroups: []
        contactRoles: []
        locale: 'en-us'
      }
    }
  }
}

output budgetId string = budget.id
