from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Callable, Type, TypeVar

from pydantic import BaseModel

from .configuration_models import ConfigurationSchema


class SchemaRegistry:
    """
    Registry for dynamically registered schemas.
    """

    _instance: "SchemaRegistry | None" = None

    # class_str -> schema
    _schemas: dict[str, Type[BaseModel]]

    # # base schema -> subclasses
    # _subclasses: dict[
    #     Type[BaseModel],
    #     list[Type[BaseModel]],
    # ]

    def __new__(cls) -> "SchemaRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schemas = {}
            # cls._instance._subclasses = defaultdict(list)

        return cls._instance

    def register(
        self,
        class_str: str,
        schema: Type[ConfigurationSchema],
    ) -> None:
        if not issubclass(
            schema,
            ConfigurationSchema,
        ):
            raise TypeError(f"{schema.__name__} must inherit from ConfigurationSchema.")

        # # Track inheritance hierarchy
        # for base in schema.__bases__:

        #     if (
        #         issubclass(base, BaseModel)
        #         and base is not BaseModel
        #     ):
        #         self._subclasses[base].append(
        #             schema
        #         )

        # TODO: handle this
        if class_str in self._schemas:
            raise ValueError(f"{class_str} already registered.")

        self._schemas[class_str] = schema

    def discover(self) -> None:
        root_package = __package__.split(".")[0]

        package = importlib.import_module(root_package)

        for _, module_name, _ in pkgutil.walk_packages(
            package.__path__,
            package.__name__ + ".",
        ):
            importlib.import_module(module_name)

    def __getitem__(
        self,
        class_str: str,
    ) -> Type[BaseModel]:
        try:
            return self._schemas[class_str]

        except KeyError:
            raise KeyError(f"No schema registered for '{class_str}'") from None

    def __contains__(
        self,
        class_str: str,
    ) -> bool:
        return class_str in self._schemas

    def _ensure_schema_loaded(
        self,
        class_str: str,
    ) -> None:
        if class_str in self:
            return

        module_name, _, _ = class_str.rpartition(".")

        if not module_name:
            raise ValueError(f"Invalid class_str '{class_str}'")

        try:
            importlib.import_module(module_name)

        except ModuleNotFoundError as e:
            raise KeyError(f"Could not import module '{module_name}' for '{class_str}'") from e

        if class_str not in self:
            raise RuntimeError(f"Module '{module_name}' imported but schema '{class_str}' was not registered.")

    def validate(
        self,
        data: dict[str, Any],
    ) -> BaseModel:
        """
        Recursively validate nested configuration.
        """

        validated = self._recursive_validate(data)

        if not isinstance(validated, BaseModel):
            raise TypeError("Top-level config did not validate to BaseModel.")

        return validated

    def _recursive_validate(
        self,
        obj: Any,
    ) -> Any:
        # List
        if isinstance(obj, list):
            return [self._recursive_validate(item) for item in obj]

        # Dict
        if isinstance(obj, dict):
            # First recurse children
            validated_dict = {key: self._recursive_validate(value) for key, value in obj.items()}

            # Then instantiate schema object
            if "class_str" in validated_dict:
                class_str = validated_dict["class_str"]

                # # Lazy import
                # self._ensure_schema_loaded(
                #     class_str
                # )

                if class_str not in self:
                    raise KeyError(f"Unknown schema '{class_str}'")

                schema = self[class_str]

                return schema.model_validate(validated_dict)

            return validated_dict

        return obj

    # # ==========================================================
    # # POLYMORPHIC SCHEMA GENERATION
    # # ==========================================================

    # def subclasses_of(
    #     self,
    #     base_schema: Type[BaseModel],
    # ) -> list[Type[BaseModel]]:

    #     return self._subclasses.get(
    #         base_schema,
    #         [],
    #     )

    # def make_union(
    #     self,
    #     base_schema: Type[BaseModel],
    # ) -> Any:
    #     """
    #     Create discriminated union dynamically.
    #     """

    #     subclasses = self.subclasses_of(
    #         base_schema
    #     )

    #     if not subclasses:
    #         raise ValueError(
    #             f"No subclasses registered for "
    #             f"{base_schema.__name__}"
    #         )

    #     union = subclasses[0]

    #     for subclass in subclasses[1:]:
    #         union = union | subclass

    #     return Annotated[
    #         union,
    #         Field(discriminator="class_str"),
    #     ]

    # def json_schema_for(
    #     self,
    #     base_schema: Type[BaseModel],
    # ) -> dict[str, Any]:
    #     """
    #     Generate polymorphic JSON schema.
    #     """

    #     union = self.make_union(
    #         base_schema
    #     )

    #     adapter = TypeAdapter(union)

    #     return adapter.json_schema()


ModelT = TypeVar(
    "ModelT",
    bound=BaseModel,
)

ClassT = TypeVar("ClassT")


def register_schema(
    schema: Type[ModelT],
) -> Callable[[Type[ClassT]], Type[ClassT]]:
    """
    Decorator that registers a runtime class
    with a Pydantic schema.

    Usage
    -----
    @register_schema(MySchema)
    class MyClass:
        ...
    """

    registry = SchemaRegistry()

    def decorator(
        cls: Type[ClassT],
    ) -> Type[ClassT]:
        class_str = f"{cls.__module__}.{cls.__name__}"

        registry.register(
            class_str=class_str,
            schema=schema,
        )

        return cls

    return decorator
