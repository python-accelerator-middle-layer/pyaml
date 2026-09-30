"""
Store and instantiate parameterized configuration templates.

Each registry owns its definitions. Generation substitutes positional arguments
into a copy of the template; the configuration loader expands any remaining
file, environment, or template references.
"""

import copy
import logging
import re

from ..common.exception import PyAMLConfigException

logger = logging.getLogger(__name__)


def substitute(obj, arguments):
    """
    Recursively substitute named placeholders in configuration values.

    Parameters
    ----------
    obj : object
        Configuration value to process. Dictionaries and lists are traversed;
        dictionary keys and non-string scalar values are left unchanged.
    arguments : dict[str, object]
        Parameter names mapped to replacement values, converted to strings.

    Returns
    -------
    object
        Configuration with substitutions applied and new dictionaries and lists.

    Notes
    -----
    Replacements use ``{name}`` placeholders and follow argument insertion order.
    Text inserted by one replacement can be modified by a later replacement.
    """
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
    """
    Store template definitions for one configuration manager or loading session.

    Definitions are isolated between instances and copied on registration and
    generation so callers can modify their configurations independently.

    Methods
    -------
    add(name, parameters, config)
        Register a named template with ordered parameters.
    generate(name, *args)
        Substitute positional arguments into a copy of a template.
    clear()
        Remove all definitions from this registry.
    """

    def __init__(self):
        """Initialize an empty template registry."""
        self.template_parameters: dict[str, list[str]] = {}
        self.template_codes: dict[str, dict] = {}

    def add(self, name: str, parameters: list[str], config: dict):
        """
        Register a template, copying its parameters and configuration.

        Parameters
        ----------
        name : str
            Template name, unique within this registry.
        parameters : list[str]
            Parameter names in the order expected by :meth:`generate`.
        config : dict
            Configuration body containing ``{parameter}`` placeholders.

        Raises
        ------
        PyAMLConfigException
            If the name is already registered.
        """
        if name in self.template_codes:
            raise PyAMLConfigException(f"Template '{name}' has already been registered.")

        self.template_parameters[name] = list(parameters)
        self.template_codes[name] = copy.deepcopy(config)

    def generate(self, name: str, *args):
        """
        Generate a configuration by substituting positional arguments.

        Parameters
        ----------
        name : str
            Name of a registered template.
        *args : object
            Values corresponding to the template's ordered parameters.
            Values are converted to strings during substitution.

        Returns
        -------
        dict
            Independent configuration with placeholders replaced. Resolver
            expressions and file references are left for the loader to expand.

        Raises
        ------
        KeyError
            If the template name is not registered.
        PyAMLConfigException
            If the number of arguments does not match the parameters.

        Notes
        -----
        Arguments containing brace-delimited placeholders produce a logging
        warning because sequential substitution may modify their contents.
        """
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
        """Remove all definitions from this registry without affecting other instances."""
        self.template_parameters.clear()
        self.template_codes.clear()
