# config/schema_registry.py
from enum import Enum
from typing import Any, Type

# from typing import Literal
from pydantic import BaseModel

from ..accelerator import AcceleratorSchema
from ..arrays.array import ArraySchema
from ..common.element import ElementSchema
from ..control.controlsystem import ControlSystemSchema
from ..lattice.simulator import SimulatorSchema


class BaseSchema(Enum):
    ACCELERATOR = AcceleratorSchema
    CONTROLSYSTEM = ControlSystemSchema
    SIMULATOR = SimulatorSchema
    ARRAY = ArraySchema
    DEVICE = ElementSchema


class SchemaRegistry:
    """
    Singleton registry for schemas.
    The registry maps the class type to which
    schema that should be used for validation.

    The registry is divided into namespaces
    based on the base schemas.
    """

    _instance: "SchemaRegistry | None" = None

    # Schemas follow the convention:
    # namespace -> class_str -> validation model class
    _schemas: dict[BaseSchema, dict[type[Any], Type[BaseModel]]]

    def __new__(cls) -> "SchemaRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schemas = {baseschema: {} for baseschema in BaseSchema}
        return cls._instance

    def register(self, class_: type[Any], schema: Type[BaseModel], baseschema: BaseSchema | None = None) -> None:
        if baseschema is None:
            baseschema = get_baseschema(schema)

            if baseschema is None:
                raise TypeError(
                    f"Could not infer a BaseSchema from {schema.__name__}. A baseschema must be explicitly given."
                )

        elif not isinstance(baseschema, BaseSchema):
            raise TypeError(f"{baseschema!r} is not a valid BaseSchema.")

        # Check if already registered
        if self.contains(class_, baseschema):
            raise ValueError(f"{class_.__name__} is already registered under {baseschema.name}.")

        self._schemas[baseschema][class_] = schema

    def contents(
        self,
    ) -> dict[BaseSchema, dict[type[Any], Type[BaseModel]]]:
        return {baseschema: dict(schemas) for baseschema, schemas in self._schemas.items()}

    def get(
        self,
        class_: type[Any],
        baseschema: BaseSchema,
    ) -> Type[BaseModel]:
        _validate_baseschema(baseschema)

        try:
            return self._schemas[baseschema][class_]

        except KeyError:
            raise KeyError(f"{class_.__name__} is not registered under {baseschema.name}.") from None

    def __getitem__(
        self,
        item: tuple[type[Any], BaseSchema],
    ) -> Type[BaseModel]:
        class_, baseschema = item

        return self.get(class_, baseschema)

    def contains(
        self,
        class_: type[Any],
        baseschema: BaseSchema,
    ) -> bool:
        _validate_baseschema(baseschema)

        return class_ in self._schemas[baseschema]

    def __contains__(
        self,
        item: tuple[type[Any], BaseSchema],
    ) -> bool:
        class_, baseschema = item

        return self.contains(class_, baseschema)


def get_baseschema(schema: Type[BaseModel]) -> BaseSchema | None:
    matches = [baseschema for baseschema in BaseSchema if issubclass(schema, baseschema.value)]

    if len(matches) > 1:
        raise TypeError(f"{schema.__name__} matches multiple base schemas: {[m.name for m in matches]}")

    if not matches:
        return None

    return matches[0]


def _validate_baseschema(
    baseschema: BaseSchema,
) -> None:
    if not isinstance(baseschema, BaseSchema):
        raise TypeError(f"{baseschema!r} is not a valid BaseSchema.")
