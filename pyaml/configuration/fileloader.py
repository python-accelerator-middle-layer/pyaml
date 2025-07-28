# PyAML config file loader
import yaml
import json
from typing import Union
from . import get_root_folder
from pathlib import Path

#TODO
#Implement cycle detection in case of wrong yaml/json link that creates a cycle
#Implement filename and line mapping for error reporting

def load(fileName:str) -> Union[dict,list]:
    """Load recursively a configuration setup"""
    if fileName.endswith(".yaml"):
        l = YAMLLoader()
    elif fileName.endswith(".json"):
        l = JSONLoader()
    else:
        raise Exception(f"{fileName} File format not supported (only .yaml or .json)")
    return l.load(fileName)
    
# Loader base class (nested files expansion)
class Loader:

    # Expand condition
    def hasToExpand(self,value):
        return isinstance(value,str) and value.endswith(self.suffix)

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
    def load(self,fileName:str) -> Union[dict,list]:
        raise Exception(fileName + ": load() method not implemented")

# YAML loader
class YAMLLoader(Loader):
    
    def load(self,fileName:str) -> Union[dict,list]:
        self.path:Path = get_root_folder() / fileName
        self.suffix = ".yaml"
        with open(self.path) as file:
            try:
                return self.expand(yaml.load(file,yaml.CLoader)) # Use fast C loader
            except yaml.YAMLError as e:
                raise Exception(self.path + ": " + str(e))

# JSON loader
class JSONLoader(Loader):

    def  load(self,fileName:str) -> Union[dict,list]:
        self.path:Path = get_root_folder() / fileName
        self.suffix = ".json"
        with open(self.path) as file:
            try:
                return self.expand(json.load(file))
            except json.JSONDecodeError as e:
                raise Exception(self.path + ": " + str(e))
