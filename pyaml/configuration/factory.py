# PyAML factory (construct AML objects from config files)
import importlib
import inspect
from pydantic import ValidationError
import pprint as pp

#TODO:
#Implement trace for error management. Hints: Implement private field __file__ in dictionary to report errors.

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
        return obj

    except ValidationError as e:
        
        print(e)
        pp.pprint(d)
        return None


def depthFirstBuild(d:dict):
  """Main factory function"""
  
  # Depth-first factory
  for key, value in d.items():
    if isinstance(value,dict):
       obj = depthFirstBuild(value)
       # Replace the inner dict by the object itself
       d[key]=obj

  # We are now on leaf (no nested object), we can construt
  obj = buildObject(d)
  return obj
