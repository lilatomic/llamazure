# llamazure.tf

Easily generate azurerm resources.

## Resources

### Network

Network rules are a pain. Generate them easily!

## Contributing

### Providing options for rendering

Some resources might have options for how to render them. For example, NSG rules can either be included on the `azurerm_network_security_group` resource or separately as `azurerm_network_security_rule`. The difference changes the semantics, as including them on the parent does not allow other `azurerm_network_security_rule`.

1. Define a subclass of `TFRenderOpt`
2. add the option as a field of your subclass of `TFResource`. Options MUST begin with `opt_` (ex `opt_total`) and they MUST have a default.