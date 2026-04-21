# PyAML factory (construct AML objects from config files)
import fnmatch
import importlib
from threading import Lock

from pydantic import ValidationError

from ..common.element import Element
from ..common.exception import PyAMLConfigException
from .unbound_element import UnboundElement


class PyAMLFactory:
    """Singleton factory to build PyAML elements with future compatibility logic."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        No matter how many times you call PyAMLFactory(),
        it will be created only once.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._elements = {}
                cls._instance._strategies = []
            return cls._instance

    def handle_validation_error(self, e, type_str: str, location_str: str, field_locations: dict):
        # Handle pydantic errors
        globalMessage = ""
        for err in e.errors():
            msg = err["msg"]
            field = ""
            if len(err["loc"]) == 2:
                field, fieldIdx = err["loc"]
                message = f"'{field}.{fieldIdx}': {msg}"
            else:
                field = err["loc"][0]
                message = f"'{field}': {msg}"
            if field_locations and field in field_locations:
                file, line, col = field_locations[field]
                loc = f"{file} at line {line}, colum {col}"
                message += f" {loc}"
            globalMessage += message
            globalMessage += ", "
        # Discard pydantic stack trace
        raise PyAMLConfigException(f"{globalMessage} for object: '{type_str}' {location_str}") from None

    def build_object(self, d: dict, ignore_external: bool = False):
        """Build an object from the dict"""

        location = d.pop("__location__", None)
        field_locations = d.pop("__fieldlocations__", None)
        location_str = ""
        if location:
            file, line, col = location
            location_str = f"{file} at line {line}, column {col}."

        if not isinstance(d, dict):
            raise PyAMLConfigException(f"Unexpected object {str(d)} {location_str}")
        if "type" not in d:
            raise PyAMLConfigException(f"No type specified for {str(type(d))}:{str(d)} {location_str}")

        module_str = d.pop("type")
        class_str = d.pop("class", None)
        validation_class_str = d.pop("validation_class", "ConfigModel")

        # Import the module
        try:
            module = importlib.import_module(module_str)
        except ModuleNotFoundError as ex:
            if not ignore_external:
                # Discard module not found stack trace
                raise PyAMLConfigException(
                    "Module referenced in type cannot be found:" + f"'{module_str}' {location_str}"
                ) from None
            else:
                return None

        # Get the object class name
        if class_str is None:
            class_str = getattr(module, "PYAMLCLASS", None)
        if class_str is None:
            raise PyAMLConfigException(
                f"PYAMLCLASS definition not found or class not specified in '{module_str}' {location_str}"
            )

        control_modes = d.pop("control_modes", None)

        if control_modes is None:
            # Immediate contruction

            # Get the validation class
            config_cls = getattr(module, validation_class_str, None)
            if config_cls is None:
                raise PyAMLConfigException(f"No validation class for '{module_str}.{class_str}' {location_str}")

            # Validate the model
            try:
                cfg = config_cls.model_validate(d)
            except ValidationError as e:
                self.handle_validation_error(e, module_str, location_str, field_locations)

            elem_cls = getattr(module, class_str, None)
            if elem_cls is None:
                raise PyAMLConfigException(f"Unknown element class '{module_str}.{class_str}' {location_str}")

            # Construct and return the object
            try:
                obj = elem_cls(cfg)
                self.register_element(obj)
            except Exception as e:
                raise PyAMLConfigException(f"{str(e)} when creating '{module_str}.{class_str}' {location_str}") from e

        else:
            # Delayed construction
            element_name = d.pop("name", None)
            if element_name is None:
                raise PyAMLConfigException(
                    f"Name not speficied for element class '{module_str}.{class_str}' {location_str}"
                )
            obj = UnboundElement(element_name, class_str, module_str, control_modes, d)

        return obj

    def build_unbound(self, e: UnboundElement, holder) -> Element:
        # Build unbound element (no validation for unbound element)
        try:
            module = importlib.import_module(e._module_name)
        except ModuleNotFoundError as ex:
            raise PyAMLConfigException("Module referenced in type cannot be found:" + f"'{e._module_name}'") from None

        elem_cls = getattr(module, e._class_name, None)
        if elem_cls is None:
            raise PyAMLConfigException(f"Unknown element class '{e._module_name}.{e._class_name}'")

        try:
            obj = elem_cls(e.get_name(), holder, **e._config)
        except Exception as ex:
            raise PyAMLConfigException(f"{str(ex)} when creating '{e._module_name}.{e._class_name}'") from ex

        if not isinstance(obj, Element):
            raise PyAMLConfigException(f"'{e._module_name}.{e._class_name}' is not a sub class of Element")

        obj._peer = holder

        return obj

    def depth_first_build(self, d, ignore_external: bool):
        """
        Main factory function (Depth-first factory)

        Parameters
        ----------
        ignore_external: bool
            Ignore `module not found` and return None when an object cannot be created
        """

        if isinstance(d, list):
            # list can be a list of objects or a list of native types
            l = []
            for _index, e in enumerate(d):
                if isinstance(e, dict) or isinstance(e, list):
                    obj = self.depth_first_build(e, ignore_external)
                    l.append(obj)
                else:
                    l.append(e)
            return l

        elif isinstance(d, dict):
            # Do not recurse CfgDict
            if "type" in d:
                if d["type"] == "pyaml.configuration.cfg_dict":
                    return self.build_object(d)

            for key, value in d.items():
                if not key == "__fieldlocations__":
                    if isinstance(value, dict) or isinstance(value, list):
                        obj = self.depth_first_build(value, ignore_external)
                        # Replace the inner dict by the object itself
                        d[key] = obj

            # We are now on leaf (no nested object), we can construct
            return self.build_object(d, ignore_external)

        raise PyAMLConfigException(
            "Unexpected element found. 'dict' or 'list' expected but got '{d.__class__.__name__}'"
        )

    def register_element(self, elt):
        if isinstance(elt, Element):
            name = elt.get_name()
            if name in self._elements:
                raise PyAMLConfigException(f"element {name} already defined")
            self._elements[name] = elt

    def get_element(self, name: str):
        if name not in self._elements:
            raise PyAMLConfigException(f"element {name} not defined")
        return self._elements[name]

    def get_elements_by_name(self, wildcard: str) -> list[Element]:
        return [e for k, e in self._elements.items() if fnmatch.fnmatch(k, wildcard)]

    def get_elements_by_type(self, type) -> list[Element]:
        return [e for k, e in self._elements.items() if isinstance(e, type)]

    def clear(self):
        self._elements.clear()


Factory = PyAMLFactory()
