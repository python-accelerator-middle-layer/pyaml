# PyAML factory (construct AML objects from config files)
import importlib
import inspect

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
    p = importlib.import_module(typeStr)
    return p.factory_constructor(d)

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
