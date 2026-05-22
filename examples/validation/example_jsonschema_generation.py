from pyaml.configuration.validation import SchemaRegistry
from pyaml.configuration.validation.generator import SchemaGenerator

# Create schema registry and discover all schemas.
schema_registry = SchemaRegistry()
schema_registry.discover()

SchemaGenerator.save(
    "pyaml.accelerator.Accelerator",
    "pyaml.schema.json",
)

# This schema can then for example be loaded in the MetaConfigurator (https://www.metaconfigurator.org) or used in VS code.
