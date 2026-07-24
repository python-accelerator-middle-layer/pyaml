import fnmatch
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..common.element import Element
from ..common.exception import PyAMLConfigException
from .unbound_element import UnboundElement

# ---------------------------------------------------------------------
# Element registry
# ---------------------------------------------------------------------

TElement = TypeVar("TElement", bound=Element)


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

NEW_KEYS = ("class", "class_path")
LEGACY_KEY = "type"
BUILD_KEYS = NEW_KEYS + (LEGACY_KEY,)


@dataclass(frozen=True)
class BuildInfo:
    module: ModuleType
    config_cls: type[BaseModel] | None  # Legacy
    class_cls: type[Any]
    control_modes: list[str] | None
    config: dict[str, Any]


def _import_module(module_path: str, ignore_external: bool) -> ModuleType | None:
    try:
        return import_module(module_path)
    except ModuleNotFoundError as exc:
        if ignore_external:
            return None
        raise PyAMLConfigException(f"Module '{module_path}' cannot be found: {exc}") from None


def _resolve_class_name(module: ModuleType, module_path: str) -> str:
    # Legacy
    class_name = getattr(module, "PYAMLCLASS", None)
    if class_name is None:
        raise PyAMLConfigException(f"Module '{module_path}' does not define PYAMLCLASS.")
    return class_name


def _resolve_build_info(data: dict, ignore_external: bool) -> BuildInfo | None:
    if not isinstance(data, dict):
        raise PyAMLConfigException(f"Unexpected object {data!r}. It needs to be a dict.")

    config = dict(data)

    if LEGACY_KEY in config:
        # Legacy module/class format:
        #   type: some.module
        #   class: MyClass        (optional; otherwise PYAMLCLASS is used)

        module_path = config.pop(LEGACY_KEY, None)

        module = _import_module(module_path, ignore_external)
        if module is None:
            return None

        class_name = config.pop("class", None)
        if class_name is None:
            class_name = _resolve_class_name(module, module_path)

        class_path = f"{module_path}.{class_name}"

    else:
        # New class_path/class alias format:
        #   class_path: some.module.MyClass
        # or
        #   class: some.module.MyClass

        present = [key for key in NEW_KEYS if key in data]
        if len(present) != 1:
            raise PyAMLConfigException(f"Exactly one of {NEW_KEYS} must be specified when '{LEGACY_KEY}' is not used.")

        class_key = present[0]
        class_path = config.pop(class_key, None)
        module_path, class_name = class_path.rsplit(".", 1)

        module = _import_module(module_path, ignore_external)
        if module is None:
            return None

    # Get the class
    class_cls = getattr(module, class_name, None)
    if class_cls is None:
        raise PyAMLConfigException(f"Unknown class '{class_path}'.")

    # Get the config class if it exists
    validation_class_name = config.pop("validation_class", None)

    if validation_class_name is not None:
        config_cls = getattr(module, validation_class_name, None)
        if config_cls is None:
            raise PyAMLConfigException(f"Module '{module_path}' does not define validation class '{validation_class_name}'.")
    else:
        config_cls = getattr(module, "ConfigModel", None)

    control_modes = config.pop("control_modes", None)
    if control_modes is not None and not isinstance(control_modes, list):
        raise PyAMLConfigException(f"'control_modes' must be a list, got '{type(control_modes).__name__}'.")

    return BuildInfo(module=module, config_cls=config_cls, class_cls=class_cls, control_modes=control_modes, config=config)


# ---------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------


class PyAMLFactory:
    def build(self, data: dict | list, ignore_external: bool = False) -> Any:
        if not isinstance(data, (dict, list)):
            raise PyAMLConfigException(f"Unexpected element found. Expected 'dict' or 'list' but got '{type(data).__name__}'")

        return self._build(data, ignore_external)

    def _build(self, value: Any, ignore_external: bool = False):
        if isinstance(value, list):
            return self._build_list(value, ignore_external)

        if isinstance(value, dict):
            return self._build_dict(value, ignore_external)

        return value

    def _build_list(self, items: list[Any], ignore_external: bool = False):
        return [self._build(item, ignore_external) for item in items]

    def _build_dict(self, data: dict, ignore_external: bool = False):
        if any(key in data for key in BUILD_KEYS):
            return self._build_object(data, ignore_external)

        return {key: self._build(value, ignore_external) for key, value in data.items()}

    def _build_object(self, data: dict, ignore_external: bool = False):
        build_info = _resolve_build_info(data, ignore_external)
        if build_info is None:
            return None

        config = {key: self._build(value, ignore_external) for key, value in build_info.config.items()}

        if build_info.config_cls is not None:
            try:
                cfg = build_info.config_cls.model_validate(config)
            except ValidationError as exc:
                raise PyAMLConfigException(str(exc)) from exc
        else:
            cfg = config

        try:
            if build_info.control_modes is None:
                if isinstance(cfg, dict):
                    obj = build_info.class_cls(**cfg)
                else:
                    obj = build_info.class_cls(cfg)

            else:
                obj = UnboundElement(
                    build_info.class_cls,
                    build_info.module.__name__,
                    build_info.control_modes,
                    cfg,
                )
        except Exception as exc:
            mode = " unbounded" if build_info.control_modes is not None else ""
            raise PyAMLConfigException(
                f"{exc} when creating{mode} '{build_info.module.__name__}.{build_info.class_cls.__name__}'"
            ) from exc

        if isinstance(obj, Element):
            ELEMENT_REGISTRY.register(obj)

        return obj

    def clear(self):
        """
        Remove all registered elements from the global registry.
        """
        ELEMENT_REGISTRY.clear()


# Shared factory instance maintained for compatibility with
# existing code using Factory.build(...) and Factory.clear(...).
Factory = PyAMLFactory()
