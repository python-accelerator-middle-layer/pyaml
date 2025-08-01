# PyAML config file loader
import logging
import json
from typing import Union
from pathlib import Path
import io

import yaml
from yaml.loader import SafeLoader
from yaml.constructor import ConstructorError
import collections.abc

from . import get_root_folder
from .. import PyAMLException

logger = logging.getLogger(__name__)

#TODO
#Implement cycle detection in case of wrong yaml/json link that creates a cycle

def load(filename:str) -> Union[dict,list]:
    """Load recursively a configuration setup"""
    if filename.endswith(".yaml") or filename.endswith(".yml"):
        l = YAMLLoader(filename)
    elif filename.endswith(".json"):
        l = JSONLoader(filename)
    else:
        raise PyAMLException(f"{filename} File format not supported (only .yaml .yml or .json)")
    return l.load(filename)

# Loader base class (nested files expansion)
class Loader:

    def __init__(self, filename:str):
        self.suffixes = []
        self.path:Path = get_root_folder() / filename

    # Expand condition
    def hasToExpand(self,value):
        return isinstance(value,str) and any(value.endswith(suffix) for suffix in self.suffixes)

    # Recursively expand a dict
    def expand_dict(self,d:dict):
        for key, value in d.items():
            if self.hasToExpand(value):
                d[key] = load(value)
            else:
                self.expand(value)

    # Recursively expand a list
    def expand_list(self,l:list):
        for idx,value in enumerate(l):
            if self.hasToExpand(value):
                l[idx] = load(value)
            else:
                self.expand(value)

    # Recursively expand an object
    def expand(self,obj: Union[dict,list]):
        if isinstance(obj,dict):
            self.expand_dict(obj)
        elif isinstance(obj,list):
            self.expand_list(obj)
        return obj 

    # Load a file
    def load(self) -> Union[dict,list]:
        raise Exception(str(self.path) + ": load() method not implemented")

class SafeLineLoader(SafeLoader):

    def __init__(self, stream):
        super().__init__(stream)
        self.filename = stream.name if isinstance(stream,io.TextIOWrapper) else ""

    def construct_mapping(self, node, deep=False):
        mapping = {}
        field_mapping = {}

        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, collections.abc.Hashable):
                raise ConstructorError("while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
            field_mapping[key] = (self.filename, value_node.start_mark.line + 1 , value_node.start_mark.column + 1)

        # Add location information inside the dict
        mapping['__location__'] = (self.filename, node.start_mark.line + 1 , node.start_mark.column + 1) 
        mapping['__fieldlocations__'] = field_mapping
        return mapping

# YAML loader
class YAMLLoader(Loader):
    
    def load(self,fileName:str) -> Union[dict,list]:
        self.path:Path = get_root_folder() / fileName
        self.suffixes = [".yaml",".yml"]
        with open(self.path) as file:
            try:
                return self.expand(yaml.load(file,Loader=SafeLineLoader))
            except yaml.YAMLError as e:
                raise Exception(self.path + ": " + str(e))

# JSON loader
class JSONLoader(Loader):

    def  load(self,fileName:str) -> Union[dict,list]:
        logger.log(logging.DEBUG, f"Loading JSON file '{self.path}'")
        self.suffixes = [".json"]
        with open(self.path) as file:
            try:
                return self.expand(json.load(file))
            except json.JSONDecodeError as e:
                raise PyAMLException(str(self.path) + ": " + str(e)) from e
