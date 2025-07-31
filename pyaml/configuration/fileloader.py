# PyAML config file loader
import logging

import yaml
import json
from typing import Union
from . import get_root_folder
from pathlib import Path

from .. import PyAMLException

logger = logging.getLogger(__name__)

#TODO
#Implement cycle detection in case of wrong yaml/json link that creates a cycle
#Implement filename and line mapping for error reporting

def load(filename:str) -> Union[dict,list]:
    """Load recursively a configuration setup"""
    if filename.endswith(".yaml") or filename.endswith(".yml"):
        l = YAMLLoader(filename)
    elif filename.endswith(".json"):
        l = JSONLoader(filename)
    else:
        raise PyAMLException(f"{filename} File format not supported (only .yaml .yml or .json)")
    return l.load()
    
# Loader base class (nested files expansion)
class Loader:

    def __init__(self, filename:str):
        self.suffixes = []
        self.path:Path = get_root_folder() / filename

    # Expand condition
    def hasToExpand(self,value):
        return isinstance(value,str) and any(value.endswith(suffix) for suffix in self.suffixes)

    # Recursively expand a dict
    def expandDict(self,d:dict):            
        for key, value in d.items():
            if self.hasToExpand(value):
                d[key] = load(value)
            else:
                self.expand(value)

    # Recursively expand a list
    def expandList(self,l:list):            
        for idx,value in enumerate(l):
            if self.hasToExpand(value):
                l[idx] = load(value)
            else:
                self.expand(value)

    # Recursively expand an object
    def expand(self,obj: Union[dict,list]):
        if isinstance(obj,dict):
            self.expandDict(obj)
        elif isinstance(obj,list):
            self.expandList(obj)
        return obj

    # Load a file
    def load(self) -> Union[dict,list]:
        raise Exception(str(self.path) + ": load() method not implemented")

# YAML loader
class YAMLLoader(Loader):

    def __init__(self, filename:str):
        super().__init__(filename)
    
    def load(self) -> Union[dict,list]:
        logger.log(logging.DEBUG, f"Loading YAML file '{self.path}'")
        self.suffixes = [".yaml", ".yml"]
        with open(self.path) as file:
            try:
                return self.expand(yaml.load(file,yaml.CLoader)) # Use fast C loader
            except yaml.YAMLError as e:
                raise Exception(str(self.path) + ": " + str(e))

# JSON loader
class JSONLoader(Loader):

    def __init__(self, filename: str):
        super().__init__(filename)

    def  load(self) -> Union[dict,list]:
        logger.log(logging.DEBUG, f"Loading JSON file '{self.path}'")
        self.suffixes = [".json"]
        with open(self.path) as file:
            try:
                return self.expand(json.load(file))
            except json.JSONDecodeError as e:
                raise Exception(str(self.path) + ": " + str(e))
