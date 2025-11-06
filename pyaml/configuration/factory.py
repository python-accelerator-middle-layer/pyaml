# PyAML factory (construct AML objects from config files)
import importlib
from threading import Lock
import fnmatch

from ..common.exception import PyAMLConfigException
from ..common.element import Element
from pydantic import ValidationError

class BuildStrategy:
    def can_handle(self, module: object, config_dict: dict) -> bool:
        """Return True if this strategy can handle the module/config."""
        raise NotImplementedError

    def build(self, module: object, config_dict: dict):
        """Build the object according to custom logic."""
        raise NotImplementedError

class PyAMLFactory:
    """Singleton factory to build PyAML elements with future compatibility logic."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        No matter how many times you call PyAMLFactory(), it will be created only once.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._elements = {}
                cls._instance._strategies = []
            return cls._instance

    def register_strategy(self, strategy: BuildStrategy):
        """Register a plugin-based strategy for object creation."""
        self._strategies.append(strategy)

    def remove_strategy(self, strategy: BuildStrategy):
        """Register a plugin-based strategy for object creation."""
        self._strategies.remove(strategy)

    def handle_validation_error(self, e, type_str:str, location_str:str, field_locations:dict):
            # Handle pydantic errors
            globalMessage = ""
            for err in e.errors():
                msg = err['msg']
                field = ""
                if len(err['loc'])==2:
                    field, fieldIdx = err['loc']
                    message = f"'{field}.{fieldIdx}': {msg}"
                else:
                    field = err['loc'][0]
                    message = f"'{field}': {msg}"
                if field in field_locations:
                    file, line, col = field_locations[field]
                    loc = f"{file} at line {line}, colum {col}"
                    message += f" {loc}"
                globalMessage += message
                globalMessage += ", "
            # Discard pydantic stack trace
            raise PyAMLConfigException(f"{globalMessage} for object: '{type_str}' {location_str}") from None

    def build_object(self, d:dict):
        """Build an object from the dict"""
        location = d.pop('__location__', None)
        field_locations = d.pop('__fieldlocations__', None)
        location_str = ""
        if location:
            file, line, col = location
            location_str = f"{file} at line {line}, column {col}."

        if not isinstance(d,dict):
            raise PyAMLConfigException(f"Unexpected object {str(d)} {location_str}")
        if not "type" in d:
            raise PyAMLConfigException(f"No type specified for {str(type(d))}:{str(d)} {location_str}")
        type_str = d.pop("type")

        try:
            module = importlib.import_module(type_str)
        except ModuleNotFoundError as ex:
            # Discard module not found stack trace
            raise PyAMLConfigException(f"Module referenced in type cannot be found: '{type_str}' {location_str}") from None

        # Try plugin strategies first
        for strategy in self._strategies:
            try:
                if strategy.can_handle(module, d):
                    obj = strategy.build(module, d)
                    self.register_element(obj)
                    return obj
            except Exception as e:
                raise PyAMLConfigException(f"Custom strategy failed {location_str}") from e

        # Default loading strategy
        # Get the config object
        config_cls = getattr(module, "ConfigModel", None)
        if config_cls is None:
            raise PyAMLConfigException(f"ConfigModel class '{type_str}.ConfigModel' not found {location_str}")

        # Get the class name
        cls_name = getattr(module, "PYAMLCLASS", None)
        if cls_name is None:
            raise PyAMLConfigException(f"PYAMLCLASS definition not found in '{type_str}' {location_str}")

        try:
            # Validate the model
            cfg = config_cls.model_validate(d)
        except ValidationError as e:
            self.handle_validation_error(e,type_str,location_str,field_locations)

        # Construct and return the object
        elem_cls = getattr(module, cls_name, None)
        if elem_cls is None:
            raise PyAMLConfigException(f"Unknown element class '{type_str}.{cls_name}'")

        try:
            obj = elem_cls(cfg)
            self.register_element(obj)
        except Exception as e:
            raise PyAMLConfigException(f"{str(e)} when creating '{type_str}.{cls_name}' {location_str}")

        return obj


    def depth_first_build(self, d):
      """Main factory function (Depth-first factory)"""

      if isinstance(d,list):
          # list can be a list of objects or a list of native types
          l = []
          for index, e in enumerate(d):
              if isinstance(e,dict) or isinstance(e,list):
                  obj = self.depth_first_build(e)
                  l.append(obj)
              else:
                  l.append(e)
          return l

      elif isinstance(d,dict):
        for key, value in d.items():
            if not key == "__fieldlocations__":
                if isinstance(value,dict) or isinstance(value,list):
                    obj = self.depth_first_build(value)
                    # Replace the inner dict by the object itself
                    d[key]=obj

        # We are now on leaf (no nested object), we can construct
        return self.build_object(d)

      raise PyAMLConfigException(f"Unexpected element found. 'dict' or 'list' expected but got '{d.__class__.__name__}'")

    def register_element(self, elt):
        if isinstance(elt,Element):
            name = elt.get_name()
            if name in self._elements:
                raise PyAMLConfigException(f"element {name} already defined")
            self._elements[name] = elt


    def get_element(self, name:str):
        if name not in self._elements:
            raise PyAMLConfigException(f"element {name} not defined")
        return self._elements[name]
    
    def get_elements_by_name(self,wildcard:str) -> list[Element]:        
        return [e for k,e in self._elements.items() if fnmatch.fnmatch(k, wildcard)]

    def get_elements_by_type(self,type) -> list[Element]:
        return [e for k,e in self._elements.items() if isinstance(e,type)]

    def clear(self):
        self._elements.clear()

Factory = PyAMLFactory()
