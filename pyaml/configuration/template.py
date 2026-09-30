import copy
import logging
import re

from ..common.exception import PyAMLConfigException

logger = logging.getLogger(__name__)


def substitute(obj, arguments):
    if isinstance(obj, dict):
        return {key: substitute(value, arguments) for key, value in obj.items()}
    if isinstance(obj, list):
        return [substitute(value, arguments) for value in obj]
    if isinstance(obj, str):
        for name, value in arguments.items():
            obj = obj.replace("{" + name + "}", str(value))
        return obj
    return obj


class TemplateManager:
    """Store template definitions for one configuration manager or loading session."""

    def __init__(self):
        self.template_parameters: dict[str, list[str]] = {}
        self.template_codes: dict[str, dict] = {}

    def add(self, name: str, parameters: list[str], config: dict):
        if name in self.template_codes:
            raise PyAMLConfigException(f"Template '{name}' has already been registered.")

        self.template_parameters[name] = list(parameters)
        self.template_codes[name] = copy.deepcopy(config)

    def generate(self, name: str, *args):
        number_of_parameters = len(self.template_parameters[name])
        number_of_arguments = len(args)

        if number_of_parameters != number_of_arguments:
            raise PyAMLConfigException(
                f"Invalid number of arguments ({args}: {number_of_arguments}) passed to template {name}."
                f" Expected {number_of_parameters}."
            )

        # name the arguments by position
        arguments_dict = {}
        for arg_name, arg_value in zip(self.template_parameters[name], args, strict=True):
            # check if {...} is included in any of the arguments, and a raise a warning if so.
            if re.search(r"\{[^{}]+\}", str(arg_value)):
                logger.warning(
                    f"Argument {arg_name!r} for template {name!r} contains a placeholder: {arg_value!r}. "
                    "Sequential replacement may substitute placeholders inside this argument.",
                )
            arguments_dict[arg_name] = arg_value

        config = substitute(copy.deepcopy(self.template_codes[name]), arguments_dict)

        return config

    def clear(self):
        self.template_parameters.clear()
        self.template_codes.clear()
