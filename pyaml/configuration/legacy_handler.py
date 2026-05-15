"""Functionality to handle transition from legacy configuration to new format."""

from __future__ import annotations

import importlib
import json
import logging
import pkgutil
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "legacy_registry.json"


# ==========================================================
# Build legacy mapping
# ==========================================================


def build_legacy_registry(package_name: str) -> dict[str, str]:
    registry = {}

    package = importlib.import_module(package_name)

    for module_info in pkgutil.walk_packages(
        package.__path__,
        prefix=package.__name__ + ".",
    ):
        module_name = module_info.name
        print("VISITING:", module_name)

        try:
            module = importlib.import_module(module_name)
            print(module)
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
