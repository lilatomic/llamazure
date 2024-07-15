# llamazure.tools

A bundle of helpful tools for dealing with Azure

## llamazure.tools.migrate

Migrate some azure objects

### Usage

#### Migrate the Workspace of a Dashboard

```bash
pants run llamazure/tools/migrate/__main__.py -- dashboard --resource-id '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-dashboards/providers/Microsoft.Portal/dashboards/00000000-0000-0000-0000-000000000001' --replacements '{"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-dashboards/providers/Microsoft.OperationalInsights/workspaces/test-0":"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-dashboards/providers/Microsoft.OperationalInsights/workspaces/test-1"}' --backup-directory '/tmp/o'
```

#### Migrate the Workspace of a Workbook

```bash
pants run llamazure/tools/migrate/__main__.py -- workbook --resource-id '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-dashboards/providers/microsoft.insights/workbooks/00000000-0000-0000-0000-000000000001' --replacements '{"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-dashboards/providers/Microsoft.OperationalInsights/workspaces/test-0":"/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-dashboards/providers/Microsoft.OperationalInsights/workspaces/test-1"}' --backup-directory '/tmp/o'
```