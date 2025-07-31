# PyAML config file loader
import logging
import json
import pytest
from typing import Union
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from . import get_root_folder
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
        self.tag_node_positions(obj)
        return obj

    def tag_node_positions(self, obj):
        """Recursively tag dicts with their __location__ (line, column)."""
        if isinstance(obj, CommentedMap):
            if hasattr(obj, 'lc'):
                obj['__location__'] = (obj.lc.line + 1, obj.lc.col + 1)
            for v in obj.values():
                self.tag_node_positions(v)
        elif isinstance(obj, dict):
            for v in obj.values():
                self.tag_node_positions(v)
        elif isinstance(obj, CommentedSeq):
            for i in obj:
                self.tag_node_positions(i)
        elif isinstance(obj, list):
            for i in obj:
                self.tag_node_positions(i)

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
        yaml = YAML()
        yaml.preserve_quotes = True
        with open(self.path) as file:
            try:
                return self.expand(yaml.load(file)) # Use fast C loader
            except Exception as e:
                raise PyAMLException(str(self.path) + ": " + str(e)) from e

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
                raise PyAMLException(str(self.path) + ": " + str(e)) from e


def test_error_with_location(tmp_path):
    # YAML avec erreur (champ 'nme' au lieu de 'name')
    content = "- type: mock_module\n  nme: oops\n"

    file_path = tmp_path / "bad.yaml"
    file_path.write_text(content)

    # Chargement YAML avec position
    yaml = YAML()
    data = yaml.load(file_path.open())

    # Injection de __location__ dans chaque dict
    def tag_node_positions(obj):
        if isinstance(obj, dict) and hasattr(obj, 'lc'):
            obj['__location__'] = (obj.lc.line + 1, obj.lc.col + 1)
        if isinstance(obj, dict):
            for v in obj.values():
                tag_node_positions(v)
        elif isinstance(obj, list):
            for i in obj:
                tag_node_positions(i)

    tag_node_positions(data)

    with pytest.raises(PyAMLConfigException) as excinfo:
        depthFirstBuild(data)

    msg = str(excinfo.value)
    assert "line 2" in msg or "line 1" in msg  # selon parser
    assert "column" in msg
    assert "name" in msg or "field" in msg
