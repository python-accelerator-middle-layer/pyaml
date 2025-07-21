# PyAML factory (construct AML objects from config files)
import importlib
import pprint as pp
import traceback
from ..control.element import Element

#TODO:
#Implement trace for error management. Hints: Implement private field __file__ in dictionary to report errors.

_ALL_ELEMENTS: dict = {}

def buildObject(d:dict):
    """Build an object from the dict"""

    if not isinstance(d,dict):
        raise Exception("Unecpted object " + str(d))
    if not "type" in d:
        raise Exception("No type specified for " + str(type(d)) + ":" + str(d))
    typeStr = d["type"]
    del d["type"]

    module = importlib.import_module(typeStr)

    # Get the config object
    config_cls = getattr(module, "ConfigModel", None)
    if config_cls is None:
        raise ValueError(f"ConfigModel class '{typeStr}.ConfigModel' not found")

    # Get the class name
    cls_name = getattr(module, "PYAMLCLASS", None)
    if cls_name is None:
        raise ValueError(f"PYAMLCLASS definition not found in '{typeStr}'")

    try:

        # Validate the model
        cfg = config_cls.model_validate(d)

        # Construct and return the object
        elem_cls = getattr(module, cls_name, None)
        if elem_cls is None:
            raise ValueError(
                f"Unknown element class '{typeStr}.{cls_name}'"
            )
        
        obj = elem_cls(cfg)
        register_element(obj)
        return obj

    except Exception as e:

        print(traceback.format_exc())
        print(e)        
        print(typeStr)
        pp.pprint(d)
        #Fatal
        quit()


def depthFirstBuild(d):
  """Main factory function (Depth-first factory)"""

  if isinstance(d,list):

      # list can be a list of objects or a list of native types
      l = []
      for e in d:
          if isinstance(e,dict) or isinstance(e,list):
              obj = depthFirstBuild(e)
              l.append(obj)
          else:
              l.append(e)
      return l
  
  elif isinstance(d,dict):
        
    for key, value in d.items():
        if isinstance(value,dict) or isinstance(value,list):
            obj = depthFirstBuild(value)
            # Replace the inner dict by the object itself
            d[key]=obj        

    # We are now on leaf (no nested object), we can construt
    obj = buildObject(d)
    return obj

def register_element(elt):
    if isinstance(elt,Element):
        name = str(elt)
        if name in _ALL_ELEMENTS:
            raise Exception(f"element {name} already defined")
        _ALL_ELEMENTS[name] = elt


def get_element(name:str):
    if name not in _ALL_ELEMENTS:
        raise Exception(f"element {name} not defined")
    return _ALL_ELEMENTS[name]
