"""Functionality to handle transition from legacy configuration to new format."""

from __future__ import annotations

import importlib
import json
import logging
import pkgutil
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Type

import yaml
from pydantic import BaseModel

from .configuration_models import ConfigurationSchema

if TYPE_CHECKING:
    from .schema_registry import SchemaRegistry


logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "legacy_registry.json"


# ==========================================================
# Build mapping between module and pyamlclass
# ==========================================================


def build_legacy_registry(package_name: str) -> dict[str, str]:
    registry = {}

    package = importlib.import_module(package_name)

    for module_info in pkgutil.walk_packages(
        package.__path__,
        prefix=package.__name__ + ".",
    ):
        module_name = module_info.name
        logger.debug("VISITING:", module_name)

        try:
            module = importlib.import_module(module_name)
        except Exception as ex:
            print(f"FAILED importing {module_name}: {ex}")
            continue

        if hasattr(module, "PYAMLCLASS"):
            pyamlclass = module.PYAMLCLASS
            pyamlclass = f"{module_name}.{pyamlclass}"
            registry[module_name] = pyamlclass

    return registry


def save_legacy_registry(output_file: str, *package_names: str):
    registry = {}

    for package_name in package_names:
        registry.update(build_legacy_registry(package_name))

    with open(output_file, "w") as f:
        json.dump(registry, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    save_legacy_registry(
        "pyaml/configuration/legacy_registry.json",
        "pyaml",
        "pyaml_cs_oa",
        "tango.pyaml",
    )


# ==========================================================
# Convert yaml file to new format
# ==========================================================


def load_registry(path: str | Path | None = None) -> dict[str, str]:
    if path is None:
        path = DEFAULT_REGISTRY_PATH

    return json.loads(Path(path).read_text())


def convert_node(node: Any, registry: dict[str, str]) -> Any:
    if isinstance(node, list):
        return [convert_node(item, registry) for item in node]

    if not isinstance(node, dict):
        return node

    converted = {k: convert_node(v, registry) for k, v in node.items()}

    legacy_type = converted.get("type")

    if isinstance(legacy_type, str):
        if legacy_type not in registry:
            raise KeyError(f"Legacy type '{legacy_type}' not found in registry")

        new_dict = {"class_path": registry[legacy_type]}

        for k, v in converted.items():
            if k != "type":
                new_dict[k] = v

        return new_dict

    return converted


def convert_yaml_file(
    input_path: str | Path,
    output_path: str | Path,
    registry_path: str | Path | None = None,
) -> None:
    registry = load_registry(registry_path)

    input_path = Path(input_path)
    output_path = Path(output_path)

    with input_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    converted = convert_node(data, registry)

    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(converted, f, sort_keys=False)


# ==========================================================
# Handle schemas
# ==========================================================


def load_legacy_schema_mapping() -> list[str]:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    schema_map = data.get("tool", {}).get("pyaml", {}).get("legacy_schema_mapping", [])

    return schema_map


def adapt_legacy_schema(config_model: Type[BaseModel], baseschema: Type[BaseModel]) -> type[BaseModel]:
    return type(
        f"Adapted_{config_model.__module__.replace('.', '_')}_{config_model.__name__}",
        (config_model, baseschema),
        {
            "__module__": config_model.__module__,
        },
    )


def discover_legacy_schemas(registry: SchemaRegistry):
    schema_map = load_legacy_schema_mapping()

    for module_name, baseschema in schema_map.items():
        # Import the baseschema
        module_path, class_name = baseschema.rsplit(".", 1)
        module = importlib.import_module(module_path)
        basecls = getattr(module, class_name)

        # Import the external package module
        try:
            module = importlib.import_module(module_name)
        except Exception as ex:
            print(f"FAILED importing {module_name}: {ex}")
            continue

        if hasattr(module, "PYAMLCLASS"):
            pyamlclass = module.PYAMLCLASS
            pyamlclass = f"{module_name}.{pyamlclass}"

            config_model = getattr(module, "ConfigModel", None)
            schema = adapt_legacy_schema(config_model, basecls)
            registry.register(pyamlclass, schema)

    # for package_name in external_packages:

    #     package = importlib.import_module(package_name)

    #     for module_info in pkgutil.walk_packages(
    #         package.__path__,
    #         prefix=package.__name__ + ".",
    #     ):
    #         module_name = module_info.name
    #         logger.debug("VISITING:", module_name)

    #         try:
    #             module = importlib.import_module(module_name)
    #         except Exception as ex:
    #             print(f"FAILED importing {module_name}: {ex}")
    #             continue

    #         if hasattr(module, "PYAMLCLASS"):
    #             pyamlclass = module.PYAMLCLASS
    #             pyamlclass = f"{module_name}.{pyamlclass}"

    #             config_model = getattr(module, "ConfigModel", None)
    #             schema = adapt_legacy_schema(config_model)
    #             registry.register(pyamlclass, schema)
