import json
import logging

import yaml
from pydantic import BaseModel

from pyaml.configuration.factory import Factory
from pyaml.validation import StaticValidation, register_schema

from ..common.exception import PyAMLConfigException

logger = logging.getLogger(__name__)


def load_json_or_yaml(string_to_load: str) -> dict:
    try:
        loaded_dict = json.loads(string_to_load)
        return "json"
    except json.JSONDecodeError:
        pass

    try:
        loaded_dict = yaml.safe_load(string_to_load)
    except yaml.YAMLError as exc:
        raise PyAMLConfigException("Template class is not a valid YAML or JSON string.") from exc

    return loaded_dict


class TemplateValidationModel(BaseModel):
    template: str
    string_to_replace: str
    parameter_list: list[str]


@register_schema
class Template(StaticValidation):
    validation_model = TemplateValidationModel

    def __new__(cls, template: str, string_to_replace: str, parameter_list: list[str]):
        for par in parameter_list:
            new_string = template.replace(string_to_replace, par)
            new_dict = load_json_or_yaml(new_string)
            yield Factory.build(new_dict)
