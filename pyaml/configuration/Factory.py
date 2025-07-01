# PyAML factory (construct AML objects from config files)
import importlib
import inspect
from pydantic import ValidationError
import pprint as pp

#TODO:
#Implement trace for error management. Hints: Implement private field __file__ in dictionary to report errors.

"""Build an object from the dict"""
def buildObject(d:dict):

    if not isinstance(d,dict):
        raise Exception("Unecpted object " + str(d))
    if not "type" in d:
        raise Exception("No type specified for " + str(type(d)) + ":" + str(d))
    typeStr = d["type"]
    del d["type"]

    module = importlib.import_module(typeStr)

    # Get the config object and validate
    config_cls = getattr(module, "Config", None)
    if config_cls is None:
        raise ValueError(f"Unknown config class '{module_path}.Config' in {path}")

    try:

        cfg = config_cls.model_validate(d)

        # Construct and return the object
        elem_class_name = typeStr.split(".")[-1]
        elem_cls = getattr(module, elem_class_name, None)
        if elem_cls is None:
            raise ValueError(
                f"Unknown element class '{typeStr}.{elem_class_name}' in {path}"
            )
        
        obj = elem_cls(cfg)
        return obj

    except ValidationError as e:
        
        print(e)
        pp.pprint(d)
        return None


"""Main factory function"""
def depthFirstBuild(d:dict):
  
  # Depth-first factory
  for key, value in d.items():
    if isinstance(value,dict):
       obj = depthFirstBuild(value)
       # Replace the inner dict by the object itself
       d[key]=obj

  # We are now on leaf (no nested object), we can construt
  obj = buildObject(d)
  return obj

"""Returns the class name of a method, or function name"""
def getName(func):
    if ".__init__" in func.__qualname__:
        class_name = func.__qualname__.split('.')[-2]  # this prints the innermost type in case of nested classes
        return f'{class_name}'
    return func.__name__

"""Type validator of a function"""
def validate(func):
    sig = inspect.signature(func)
    def newFunc(*args, **kwargs):
        arguments = sig.bind(*args, **kwargs).arguments
        for arg, value in arguments.items():
            if arg in func.__annotations__:
                expectedType = func.__annotations__[arg]
                if not isinstance(value, expectedType):
                    raise Exception( getName(func) + ", " + arg + ": " + 
                                     str(expectedType) + " but got " + str(type(value)))
        return func(*args, **kwargs)
    return newFunc
