# PyAML factory (construct AML objects from config files)
import importlib
from threading import Lock

from .config_exception import PyAMLConfigException
from ..exception import PyAMLException
from ..lattice.element import Element
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

    def handle_build_error(self, e, type_str:str, location_str:str, field_locations:dict):
            globalMessage = ""
            if isinstance(e,ValidationError):
                # Handle pydantic errors
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
            if len(globalMessage)==0:
                # TODO: improve location for arrays
                globalMessage = str(e)
            raise PyAMLException(f"{globalMessage} for object: '{type_str}' {location_str}") from e

    def build_object(self, d:dict):
        """Build an object from the dict"""
        location = d.pop('__location__', None)
        field_locations = d.pop('__fieldlocations__', None)
        location_str = ""
        if location:
            file, line, col = location
            location_str = f"{file} at line {line}, column {col}."

        if not isinstance(d,dict):
            raise PyAMLException(f"Unexpected object {str(d)} {location_str}")
        if not "type" in d:
            raise PyAMLException(f"No type specified for {str(type(d))}:{str(d)} {location_str}")
        type_str = d.pop("type")

        try:
            module = importlib.import_module(type_str)
        except ModuleNotFoundError as ex:
            raise PyAMLException(f"Module referenced in type cannot be founded: '{type_str}' {location_str}") from ex

        # Try plugin strategies first
        for strategy in self._strategies:
            try:
                if strategy.can_handle(module, d):
                    obj = strategy.build(module, d)
                    self.register_element(obj)
                    return obj
            except Exception as e:
                raise PyAMLException(f"Custom strategy failed {location_str}") from e

        # Default loading strategy
        # Get the config object
        config_cls = getattr(module, "ConfigModel", None)
        if config_cls is None:
            raise PyAMLException(f"ConfigModel class '{type_str}.ConfigModel' not found {location_str}")

        # Get the class name
        cls_name = getattr(module, "PYAMLCLASS", None)
        if cls_name is None:
            raise PyAMLException(f"PYAMLCLASS definition not found in '{type_str}' {location_str}")

        try:

            # Validate the model
            cfg = config_cls.model_validate(d)

            # Construct and return the object
            elem_cls = getattr(module, cls_name, None)
            if elem_cls is None:
                raise PyAMLException(f"Unknown element class '{type_str}.{cls_name}'")

            obj = elem_cls(cfg)
            self.register_element(obj)
            return obj

        except Exception as e:
            self.handle_build_error(e,type_str,location_str,field_locations)

    def depth_first_build(self, d):
      """Main factory function (Depth-first factory)"""

      if isinstance(d,list):
          # list can be a list of objects or a list of native types
          l = []
          for index, e in enumerate(d):
              if isinstance(e,dict) or isinstance(e,list):
                  try:
                      obj = self.depth_first_build(e)
                      l.append(obj)
                  except PyAMLException as pyaml_ex:
                      raise PyAMLConfigException(f"[{index}]", pyaml_ex) from pyaml_ex
                  except Exception as ex:
                      raise PyAMLConfigException(f"[{index}]", ex) from ex
              else:
                  l.append(e)
          return l

      elif isinstance(d,dict):
        for key, value in d.items():
            if( not key == "__fieldlocations__"):
                if isinstance(value,dict) or isinstance(value,list):
                    try:
                        obj = self.depth_first_build(value)
                        # Replace the inner dict by the object itself
                        d[key]=obj
                    except PyAMLException as pyaml_ex:
                        raise PyAMLConfigException(key, pyaml_ex) from pyaml_ex
                    except Exception as ex:
                        raise PyAMLConfigException(key) from ex

        # We are now on leaf (no nested object), we can construct
        try:
            obj = self.build_object(d)
        except PyAMLException as pyaml_ex:
            raise PyAMLConfigException(None, pyaml_ex) from pyaml_ex
        except Exception as ex:
            raise PyAMLException("An exception occurred while building object") from ex
        return obj

      raise PyAMLException("Unexpected element found.")

    def register_element(self, elt):
        if isinstance(elt,Element):
            name = str(elt)
            if name in self._elements:
                raise PyAMLException(f"element {name} already defined")
            self._elements[name] = elt


    def get_element(self, name:str):
        if name not in self._elements:
            raise PyAMLException(f"element {name} not defined")
        return self._elements[name]

    def clear(self):
        self._elements.clear()

factory = PyAMLFactory()

# For backward compatibility
buildObject = factory.build_object
depthFirstBuild = factory.depth_first_build
register_element = factory.register_element
get_element = factory.get_element
clear = factory.clear
