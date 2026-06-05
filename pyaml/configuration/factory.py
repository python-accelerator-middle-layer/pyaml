import fnmatch
import importlib
from dataclasses import dataclass
from threading import Lock
from types import ModuleType
from typing import Any, TypeVar, get_origin, get_type_hints

from pydantic import BaseModel, ValidationError

from ..common.element import Element
from ..common.exception import PyAMLConfigException
from .unbound_element import UnboundElement

TElement = TypeVar("TElement", bound=Element)

# ---------------------------------------------------------------------
# Element registry
# ---------------------------------------------------------------------


class ElementRegistry:
    """
    Singleton registry of all instantiated Elements.

    Elements are registered by name and can later be retrieved
    individually, by wildcard pattern, or by type.
    """

    _instance = None

    def __new__(cls):
        """
        Return the singleton registry instance.
        """

        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._elements = {}
        return cls._instance

    def register(self, element: Element) -> None:
        """
        Register an Element by name.

        Parameters
        ----------
        element : Element
            Element to register.

        Raises
        ------
        PyAMLConfigException
            If the object is not an Element or if another element
            with the same name is already registered.
        """

        if not isinstance(element, Element):
            raise PyAMLConfigException(f"Cannot register object of type '{type(element).__name__}' since expected Element.")

        name = element.get_name()
        if name in self._elements:
            raise PyAMLConfigException(f"Element {name} already defined.")
        self._elements[name] = element

    def get(self, name: str) -> Element:
        """
        Return an Element by name.

        Parameters
        ----------
        name : str
            Element name.

        Returns
        -------
        Element
            Registered element.

        Raises
        ------
        PyAMLConfigException
            If the element is not registered.
        """

        try:
            return self._elements[name]
        except KeyError:
            raise PyAMLConfigException(f"Element {name} not defined.") from None

    def get_by_name(self, wildcard: str) -> list[Element]:
        """
        Return all elements whose name matches a wildcard pattern.

        Parameters
        ----------
        wildcard : str
            Wildcard expression compatible with ``fnmatch``.

        Returns
        -------
        list[Element]
            Matching elements.
        """

        return [e for n, e in self._elements.items() if fnmatch.fnmatch(n, wildcard)]

    def get_by_type(self, element_type: type[TElement]) -> list[TElement]:
        """
        Return all registered elements of the given type.

        Parameters
        ----------
        element_type : type[Element]
            Element type to match.

        Returns
        -------
        list[TElement]
            Matching elements.
        """

        return [e for e in self._elements.values() if isinstance(e, element_type)]

    def clear(self) -> None:
        """
        Remove all registered elements.
        """

        self._elements.clear()

    def __contains__(self, name: str) -> bool:
        """
        Return whether an element with the given name is registered.
        """

        return name in self._elements

    def __len__(self) -> int:
        """
        Return the number of registered elements.
        """

        return len(self._elements)


# Global element registry used during configuration loading.
ELEMENT_REGISTRY = ElementRegistry()

# ---------------------------------------------------------------------
# Handle build information
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class BuildInfo:
    """
    Information required to construct an object from a configuration
    dictionary.

    Attributes
    ----------
    module : ModuleType
        Imported module containing the object class and validation model.
    config_cls : type[BaseModel]
        Pydantic model used to validate the configuration.
    class_str : str
        Name of the class to instantiate.
    field_locations : dict | None
        Mapping between configuration fields and their source locations
        in the configuration file.
    location_str : str
        Human-readable location of the object definition in the
        configuration file.
    """

    module: ModuleType
    config_cls: type[BaseModel]
    class_str: str
    field_locations: dict | None
    location_str: str


def resolve_build_info(data: dict, ignore_external: bool) -> BuildInfo | None:
    """
    Resolve the information required to construct an object.

    The configuration dictionary is inspected to determine the module,
    object class and validation model to use. The referenced module is
    imported and the corresponding validation class is retrieved.

    Parameters
    ----------
    data : dict
        Configuration dictionary describing the object.
    ignore_external : bool
        Ignore missing modules and return ``None`` instead of raising an
        exception.

    Returns
    -------
    BuildInfo | None
        Information required to construct the object, or ``None`` when
        ``ignore_external`` is enabled and the referenced module cannot
        be imported.

    Raises
    ------
    PyAMLConfigException
        If the configuration is invalid, the referenced class cannot be
        resolved, or the validation model cannot be found.
    """

    if not isinstance(data, dict):
        raise PyAMLConfigException(f"Unexpected object {data!r}. It needs to be a dict.")

    location = data.get("__location__")
    field_locations = data.get("__fieldlocations__")

    if location:
        file, line, col = location
        location_str = f"{file} at line {line}, column {col}."
    else:
        location_str = ""

    if "type" not in data:
        raise PyAMLConfigException(f"No type specified for {type(data).__name__}:{data!r} {location_str}")

    module_str = data["type"]
    class_str = data.get("class")
    validation_class_str = data.get("validation_class", "ConfigModel")

    # Import the module
    try:
        module = importlib.import_module(module_str)
    except ModuleNotFoundError:
        if ignore_external:
            return None
        raise PyAMLConfigException(f"Module referenced in type cannot be found: '{module_str}' {location_str}") from None

    # Get the object class name
    if class_str is None:
        class_str = getattr(module, "PYAMLCLASS", None)

    if class_str is None:
        raise PyAMLConfigException(f"PYAMLCLASS definition not found or class not specified in '{module_str}' {location_str}")

    # Get the validation class
    config_cls = getattr(module, validation_class_str, None)
    if config_cls is None:
        raise PyAMLConfigException(f"No validation class for '{module.__name__}.{class_str}' {location_str}")

    return BuildInfo(
        module=module,
        config_cls=config_cls,
        class_str=class_str,
        field_locations=field_locations,
        location_str=location_str,
    )


def get_field_type(config_cls, field_name):
    """
    Return the annotated type of a configuration field.

    Parameters
    ----------
    config_cls : type[BaseModel] | None
        Pydantic configuration model.
    field_name : str
        Name of the field.

    Returns
    -------
    type | None
        Annotated field type, or ``None`` if the field is not defined
        in the model.
    """

    if config_cls is None:
        return None

    return get_type_hints(config_cls).get(field_name)


# ---------------------------------------------------------------------
# Validation error
# ---------------------------------------------------------------------


def handle_validation_error(exc, type_str: str, location_str: str, field_locations: dict | None):
    """
    Convert a Pydantic validation error into a PyAMLConfigException.

    Validation errors are reformatted to include the corresponding
    configuration field and, when available, the source file location
    of the field in the configuration file.

    Parameters
    ----------
    exc : ValidationError
        Pydantic validation error.
    type_str : str
        Name of the object type being validated.
    location_str : str
        Human-readable location of the object definition in the
        configuration file.
    field_locations : dict | None
        Mapping between field names and their source locations in the
        configuration file.

    Raises
    ------
    PyAMLConfigException
        Always raised with a formatted summary of the validation
        errors. The original Pydantic exception traceback is
        suppressed.
    """

    messages = []

    for err in exc.errors():
        loc = err.get("loc", ())
        msg = err["msg"]

        if len(loc) == 2:
            field, field_idx = loc
            message = f"'{field}.{field_idx}': {msg}"
            field_name = field
        elif len(loc) == 1:
            field_name = loc[0]
            message = f"'{field_name}': {msg}"
        else:
            field_name = None
            message = f"{loc}: {msg}"

        if field_locations and field_name in field_locations:
            file, line, col = field_locations[field_name]
            message += f" ({file} at line {line}, column {col})"

        messages.append(message)

    raise PyAMLConfigException(f"{'; '.join(messages)} for object: '{type_str}' {location_str}") from None


# ---------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------


class PyAMLFactory:
    """
    Factory for constructing PyAML objects from configuration data.
    """

    def _build_list(self, items, ignore_external: bool):
        """
        Recursively build all nested objects contained in a list.
        """

        return [self.build(item, ignore_external) if isinstance(item, (dict, list)) else item for item in items]

    def _is_plain_dict_type(self, field_type) -> bool:
        """
        Return whether a field type represents a plain dictionary.

        Plain dictionary fields are not recursively processed by the
        factory and are passed unchanged to the validation model.
        """
        return field_type is dict or get_origin(field_type) is dict

    def _build_dict(self, data: dict, ignore_external: bool):
        """
        Recursively build nested objects referenced by a configuration
        dictionary.

        Fields annotated as plain dictionaries are excluded from the
        recursive build process and are left unchanged.
        """

        build_info = resolve_build_info(data, ignore_external)
        config_cls = build_info.config_cls

        result = dict(data)

        for key, value in data.items():
            if key == "__fieldlocations__":
                continue

            if isinstance(value, (dict, list)):
                field_type = get_field_type(config_cls, key)

                # Do not recurse dict defined in ConfigModel
                # pydantic use TypedDict not usable with isinstance
                if not self._is_plain_dict_type(field_type):
                    result[key] = self.build(value, ignore_external)

        return result

    def _strip_build_metadata(self, data: dict):
        """
        Remove PyAML-specific metadata from a configuration dictionary.

        Returns
        -------
        tuple[dict, list[str] | None]
            Cleaned configuration dictionary and the associated
            control modes, if any.
        """

        cleaned = dict(data)
        cleaned.pop("__location__", None)
        cleaned.pop("__fieldlocations__", None)
        cleaned.pop("type", None)
        cleaned.pop("class", None)
        cleaned.pop("validation_class", None)
        control_modes = cleaned.pop("control_modes", None)
        return cleaned, control_modes

    def _resolve_element_class(self, module, class_str: str, location_str: str):
        """
        Resolve the class to instantiate from a module.

        Raises
        ------
        PyAMLConfigException
            If the requested class cannot be found.
        """

        elem_cls = getattr(module, class_str, None)
        if elem_cls is None:
            raise PyAMLConfigException(f"Unknown element class '{module.__name__}.{class_str}' {location_str}")
        return elem_cls

    def _construct_element(
        self,
        elem_cls,
        module_name: str,
        class_str: str,
        cfg,
        control_modes,
        location_str: str,
    ):
        """
        Construct an object from a validated configuration.

        When control modes are specified, an UnboundElement is created
        instead of immediately instantiating the target class.

        Raises
        ------
        PyAMLConfigException
            If object construction fails.
        """

        try:
            if control_modes is None:
                return elem_cls(cfg)

            return UnboundElement(elem_cls, module_name, control_modes, cfg)

        except Exception as e:
            mode = "unbounded" if control_modes is not None else ""
            suffix = f" {mode}" if mode else ""
            raise PyAMLConfigException(f"{e} when creating{suffix} '{module_name}.{class_str}' {location_str}") from e

    def build_object(self, data: dict, ignore_external: bool = False):
        """
        Build a single object from a configuration dictionary.

        The configuration is validated using the associated Pydantic
        model before the target class is instantiated.

        Parameters
        ----------
        data : dict
            Object configuration.
        ignore_external : bool
            Ignore missing external modules.

        Returns
        -------
        Any
            Instantiated object or UnboundElement.
        """

        # Get the build information
        build_info = resolve_build_info(data, ignore_external)
        module = build_info.module
        config_cls = build_info.config_cls
        class_str = build_info.class_str
        field_locations = build_info.field_locations
        location_str = build_info.location_str

        cleaned_data, control_modes = self._strip_build_metadata(data)

        # Validate the model
        try:
            cfg = config_cls.model_validate(cleaned_data)
        except ValidationError as e:
            handle_validation_error(e, module.__name__, location_str, field_locations)

        # Get the class
        elem_cls = self._resolve_element_class(module, class_str, location_str)

        # Build the object
        obj = self._construct_element(
            elem_cls=elem_cls,
            module_name=module.__name__,
            class_str=class_str,
            cfg=cfg,
            control_modes=control_modes,
            location_str=location_str,
        )

        # Register the element
        if isinstance(obj, Element):
            ELEMENT_REGISTRY.register(obj)
        return obj

    def build(self, data: dict | list, ignore_external: bool) -> Any:
        """
        Recursively build objects from configuration data.

        Lists are traversed recursively and configuration dictionaries
        are converted into instantiated objects.

        Parameters
        ----------
        data : dict | list
            Configuration data to build.
        ignore_external : bool
            Ignore missing external modules and return ``None`` for
            objects that cannot be constructed.

        Returns
        -------
        Any
            Built object, list of objects, or native value.
        """

        if not isinstance(data, (dict, list)):
            raise PyAMLConfigException(f"Unexpected element found. 'dict' or 'list' expected but got '{type(data).__name__}'")

        if isinstance(data, list):
            return self._build_list(data, ignore_external)

        elif isinstance(data, dict):
            data = self._build_dict(data, ignore_external)
            return self.build_object(data, ignore_external)

    def clear(self):
        """
        Remove all registered elements from the global registry.
        """
        ELEMENT_REGISTRY.clear()


# Shared factory instance maintained for compatibility with
# existing code using Factory.build(...) and Factory.clear(...).
Factory = PyAMLFactory()
