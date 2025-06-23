# PyAML factory (construct Yaml from config file)
import importlib

#TODO
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

"""Check type"""
def checkType(obj,expectedType:type, msg:str):
   if (obj is not None) and not isinstance(obj,expectedType):
      raise Exception(msg + " " + str(expectedType) + " expected but got " + str(type(obj)))
      
