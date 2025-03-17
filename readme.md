# Llamazure

Llamazure is a megalibrary of little tools to make dealing with Azure less onerous.

## llamazure.azrest : Azure Resource Manager client

The `llamazure.azrest` package provides a client for the Azure Resource Manager. This is all the resources you can create in Azure. It includes a client that forms requests the way Azure wants and a code generator for the Azure OpenAPI specs that generates a more ergonomic interface. It provides automatic retries, pagination, and long-polling. It also provides access to the secret batch-mode API.

## llamazure.azgraph : Azure Resources Graph client

The `llamazure.azgraph` package provides a client for the Azure Resource Graph. This API can make pulling back specific information a breeze. For example, you can get the count of all virtual machines by their size with a single query. The client included here allows you to make that query in only a few lines

## llamazure.msgraph : Microsoft Graph client

The `llamazure.msgraph` package provides a client for the Microsoft Graph. This contains resources in Entra (Azure Active Directory), M365, and similar services. This client makes it easy to adapt the query from Microsoft's documentation without having to figure out the ODATA API.

## llamazure.rbac : Azure RBAC helpers

The `llamazure.rbac` package provides helpers to manager Azure RBAC. Azure has idiosyncracies with its implementation of RBAC, and this package smooths over many of them. For example, a RoleDefinition must have the target defined in its assignableScopes for it to be assigned; this package checks for that and automatically expands it. 

## llamazure.rid : Resource IDs you can use

The `llamazure.rid` package provides a usable resource ID parser. 

## llamazure.tf : Utilities to synthesise Terraform for some Azure resources

The `llamazure.tf` package provides helpers and models for generating Terraform objects for some of the more tedious resources. For example, NSGs require defining all fields, manually managing priorities, and insist on the correct pluralisation of some attributes (they will reject a single-item list being set as the "sourcePrefixes", requiring "sourcePrefix"). This package computes all that automatically.

## llamazure.tools : A toolbox with odds and ends

The `llamazure.tools` package provides several tools that leverage other components of the `llamazure` ecosystem. They are useful in themselves, and they serve as examples for developers.

## llamazure.tresource : Tree structure for Azure resources

The `llamazure.tresource` package provides a way to group resources into their hierarchy.
