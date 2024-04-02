# llamazure.history

Build a history of an Azure tenancy.

The `llamazure.history` provides an application that can keep track of the history of Azure tenancies.
`llamazure.history` uses Postgres as a backend to store the resources. You can use the HTTP query interface in the app, or you can extend the app to run in-DB queries. You can also expose the DB directly for analytical queries.

`llamazure.history` views changes in 2 phases:
- snapshots : coherent and complete views of a tenancy
- deltas : change events to individual resources

Deltas keep the model up-to-date, and snapshots make up for missed deltas and provide a complete view of a tenancy. Snapshots can also improve performance if exact timing isn't necessary. For example, deltas allow a user to know exactly when a resource changed. But, if the delta message is missed, a snapshot ensures that change is noticed at some point. Since snapshots are complete, a user could request a snapshot to get all resources instantly, rather than the DB having to compute the latest version of every resource.

## Usage

### Writing



### Customisation

The app uses the `DefaultAzureCredential` for its Azure credential. You can implement an alternative `CredentialCache`.

## Examples

## References

### FastAPI

- [Getting started](https://fastapi.tiangolo.com/) : the basics for using fastapi
- [FastAPI Settings](https://fastapi.tiangolo.com/advanced/settings/) : FastAPI using Pydantic settings
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) : doc