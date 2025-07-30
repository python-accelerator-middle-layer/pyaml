# PyAML factory (construct AML objects from config files)
import importlib
import pprint as pp
import traceback

from .config_exception import PyAMLConfigException
from ..exception import PyAMLException
from ..lattice.element import Element

#TODO:
#Implement trace for error management. Hints: Implement private field __file__ in dictionary to report errors.

_ALL_ELEMENTS: dict = {}

def buildObject(d:dict):
    """Build an object from the dict"""

    if not isinstance(d,dict):
        raise PyAMLException("Unexpected object " + str(d))
    if not "type" in d:
        raise PyAMLException("No type specified for " + str(type(d)) + ":" + str(d))
    type_str = d["type"]
    del d["type"]

    try:
        module = importlib.import_module(type_str)
    except ModuleNotFoundError as ex:
        raise PyAMLException(f"Module referenced in type cannot be founded: '{type_str}'") from ex

    # Get the config object
    config_cls = getattr(module, "ConfigModel", None)
    if config_cls is None:
        raise ValueError(f"ConfigModel class '{type_str}.ConfigModel' not found")

    # Get the class name
    cls_name = getattr(module, "PYAMLCLASS", None)
    if cls_name is None:
        raise ValueError(f"PYAMLCLASS definition not found in '{type_str}'")

    try:

        # Validate the model
        cfg = config_cls.model_validate(d)

        # Construct and return the object
        elem_cls = getattr(module, cls_name, None)
        if elem_cls is None:
            raise ValueError(
                f"Unknown element class '{type_str}.{cls_name}'"
            )
        
        obj = elem_cls(cfg)
        register_element(obj)
        return obj

    except Exception as e:

        print(traceback.format_exc())
        print(e)        
        print(type_str)
        pp.pprint(d)
        #Fatal
        quit()


def depthFirstBuild(d):
  """Main factory function (Depth-first factory)"""

  if isinstance(d,list):
      # list can be a list of objects or a list of native types
      l = []
      for index, e in enumerate(d):
          if isinstance(e,dict) or isinstance(e,list):
              try:
                  obj = depthFirstBuild(e)
                  l.append(obj)
              except PyAMLException as pyaml_ex:
                  raise PyAMLConfigException(f"[{index}]", pyaml_ex) from pyaml_ex
              except Exception as ex:
                  raise PyAMLConfigException(f"[{index}]") from ex
          else:
              l.append(e)
      return l
  
  elif isinstance(d,dict):
    for key, value in d.items():
        if isinstance(value,dict) or isinstance(value,list):
            try:
                obj = depthFirstBuild(value)
                # Replace the inner dict by the object itself
                d[key]=obj
            except PyAMLException as pyaml_ex:
                raise PyAMLConfigException(key, pyaml_ex) from pyaml_ex
            except Exception as ex:
                raise PyAMLConfigException(key) from ex

    # We are now on leaf (no nested object), we can construct
    try:
        obj = buildObject(d)
    except PyAMLException as pyaml_ex:
        raise PyAMLConfigException(None, pyaml_ex) from pyaml_ex
    except Exception as ex:
        raise PyAMLException("An exception occurred while building object") from ex
    return obj

  raise PyAMLException("Unexpected element found.")

def register_element(elt):
    if isinstance(elt,Element):
        name = str(elt)
        if name in _ALL_ELEMENTS:
            raise PyAMLException(f"element {name} already defined")
        _ALL_ELEMENTS[name] = elt


def get_element(name:str):
    if name not in _ALL_ELEMENTS:
        raise PyAMLException(f"element {name} not defined")
    return _ALL_ELEMENTS[name]
