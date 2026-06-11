import inspect
from typing import Any, get_type_hints

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


def add_schema(cls):
    # Get the attributes
    sig = inspect.signature(cls.__init__)

    # Filter out self, *args and **kwargs
    params = [
        p
        for p in sig.parameters.values()
        if p.name != "self"
        and p.kind
        not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    ]

    # Get the type annotations
    hints = get_type_hints(cls.__init__, include_extras=True)

    for p in params:
        if p.name not in hints:
            raise TypeError(f"{cls.__name__}.__init__ parameter '{p.name}' must be annotated.")

    @classmethod
    def __get_pydantic_core_schema__(target_cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        fields: dict[str, core_schema.TypedDictField] = {}

        for p in params:
            annotation = hints.get(p.name)
            field_schema = handler.generate_schema(annotation)

            fields[p.name] = core_schema.typed_dict_field(
                field_schema,
                required=(p.default is inspect._empty),
            )

        typed_dict = core_schema.typed_dict_schema(fields)

        # Validate and create an object of the class
        # This is required to handle nested objects
        def validate(value, inner_validator):
            # Allow already-created instances to pass through unchanged
            if isinstance(value, target_cls):
                return value

            # Validate the data
            data = inner_validator(value)

            # Create an object of the class
            return target_cls(**data)

        return core_schema.no_info_wrap_validator_function(validate, typed_dict)

    # Add the method on the class
    cls.__get_pydantic_core_schema__ = __get_pydantic_core_schema__
    return cls
