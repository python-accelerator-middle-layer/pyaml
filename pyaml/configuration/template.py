import yaml

from ..common.element import Element
from ..common.exception import PyAMLConfigException


class TemplateManager:
    template_names = []
    template_parameters = {}
    template_codes = {}

    @classmethod
    def add(cls, name: str, parameters: list[str], config: dict):
        if name in cls.template_names:
            raise PyAMLConfigException("Template '{name}' has already been registered.")

        cls.template_names.append(name)
        cls.template_parameters[name] = parameters
        cls.template_codes[name] = yaml.safe_dump(config, sort_keys=False)  # serialize into yaml, retain order

    @classmethod
    def generate(cls, name: str, *args):
        number_of_parameters = len(cls.template_parameters[name])
        number_of_arguments = len(args)

        if number_of_parameters != number_of_arguments:
            raise PyAMLConfigException(
                f"Invalid number of arguments ({args}: {number_of_arguments}) passed to template {name}."
                f" Expected {number_of_parameters}."
            )

        # name the arguments by position
        arguments_dict = {}
        for arg_name, arg_value in zip(cls.template_parameters[name], args, strict=True):
            arguments_dict[arg_name] = arg_value

        # use standard str function format to replace.
        new_code = cls.template_codes[name].format(**arguments_dict)
        # code str must already be in yaml format
        config = yaml.safe_load(new_code)
        return config

    @classmethod
    def clear(cls):
        cls.template_names = []
        cls.template_parameters = {}
        cls.template_codes = {}
