# 0

# 0.2

### 0.2.0

- feature: completely rebuilt everything
- feature: support for many more OpenAPI constructs
  - nested subclasses
  - remote references
  - allOf
  - additionalParameters
  - enums
- feature: support circular references
- feature: support for importing from other OpenAPI documents
- fix: use alias when serialising
- fix: handle unsafe param names (eg `$filter`)
- internal: use cache for OpenAPI documents (speeds up performance when pulling from Github)

# 0.1

### 0.1.0

- feature: completely rebuild everything
- feature: codegen interface from Azure OpenAPI specs
- feature: batch api

# 0.0

### 0.0.2

- deps: update llamazure.rid

### 0.0.1

- feature: release
