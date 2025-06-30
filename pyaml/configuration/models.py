from pathlib import Path
from typing import Dict, List, Tuple
import json
import importlib
import types

import yaml
from pydantic import BaseModel, Field, model_validator

from . import get_config_file_path


class PyAmlBaseModel(BaseModel):
    module_path: str = Field(validation_alias="type", default="")

    model_config = {
        "populate_by_name": True,  # allows setting "module_path" instead of `type` directly
    }


class ConfigBase(PyAmlBaseModel):

    @staticmethod
    def load_config_from_file(path: str | Path):

        path = Path(path).resolve()

        match path.suffix:
            case ".yaml" | ".yml":
                with path.open() as f:
                    data = yaml.safe_load(f)
            case ".json":
                data = json.loads(path.read_text())
            case _:
                raise ValueError(
                    f"Unsupported file type: {path.suffix}. Expected .yaml, .yml, or .json."
                )

        if isinstance(data, list):
            data = data[0]  # Assume the first item is the relevant model

        *_, cfg = construct_config_from_dict(path, data)
        return cfg

    @model_validator(mode="before")
    @classmethod
    def set_default_module_path(cls, values):
        if isinstance(values, ConfigBase):
            return values

        if values.get("type", "") == "":
            values["type"] = cls.__module__
        return values

    @classmethod
    def validate_sub_config(
        cls, v, values, field_name: str, expected_class: PyAmlBaseModel
    ):
        if isinstance(v, ConfigBase):
            return v
        elif isinstance(v, (str, Path)):
            full_path = get_config_file_path(v)
            cfg = cls.load_config_from_file(full_path)
            if not isinstance(cfg, expected_class):
                raise ValueError(
                    f"Invalid type for '{field_name}': {type(cfg)}. Expected {expected_class}."
                )
            return cfg
        else:
            raise ValueError(
                f"Invalid type for '{field_name}': {type(v)}. Expected str or a type inherited from {expected_class}."
            )


def _parse_yaml_file(path: str | Path) -> Tuple[Path, Dict | List]:

    path = get_config_file_path(path)
    with path.open() as f:
        data = yaml.safe_load(f)

    return path, data


def _parse_json_file(path: str | Path) -> Tuple[Path, Dict | List]:

    path = get_config_file_path(path)
    data = json.loads(Path(path).read_text())

    return path, data


def construct_config_from_dict(
    path: Path, data: Dict
) -> Tuple[str, types.ModuleType, ConfigBase]:

    module_path = data.get("type")
    if not module_path:
        raise ValueError(f"No 'type' field found in {path}")

    module = importlib.import_module(module_path)
    config_cls = getattr(module, "Config", None)
    if config_cls is None:
        raise ValueError(f"Unknown config class '{module_path}.Config' in {path}")

    cfg = config_cls.model_validate(data)

    return module_path, module, cfg


def construct_element(
    path: Path, module_path: str, module: types.ModuleType, cfg: ConfigBase
):

    elem_class_name = module_path.split(".")[-1]
    elem_cls = getattr(module, elem_class_name, None)
    if elem_cls is None:
        raise ValueError(
            f"Unknown element class '{module_path}.{elem_class_name}' in {path}"
        )

    return elem_cls(cfg)


def recursively_construct_element_from_cfg(cfg: ConfigBase):
    elem_class_name = cfg.module_path.split(".")[-1]
    module = importlib.import_module(cfg.module_path)
    elem_cls = getattr(module, elem_class_name, None)
    return elem_cls(cfg)


def construct_element_from_dict(path: Path, data: Dict) -> BaseModel:

    module_path, module, cfg = construct_config_from_dict(path, data)

    elem = construct_element(path, module_path, module, cfg)
    return elem


def load_from_yaml(path: str | Path) -> BaseModel:
    path, data = _parse_yaml_file(path)
    if isinstance(data, list):
        data = data[0]  # Assume the first item is the relevant model
    return construct_element_from_dict(path, data)


def load_from_json(path: str | Path) -> BaseModel:
    path, data = _parse_json_file(path)
    if isinstance(data, list):
        data = data[0]  # Assume the first item is the relevant model
    return construct_element_from_dict(path, data)
