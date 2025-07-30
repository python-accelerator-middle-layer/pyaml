"""
PyAML main class
"""

from pydantic import BaseModel,ConfigDict
from .instrument import Instrument
from .configuration.factory import depthFirstBuild
from pyaml.configuration import load,set_root_folder
import os

# Define the main class name for this module
PYAMLCLASS = "PyAML"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    instruments: list[Instrument]
    """Instrument name"""

class PyAML(object):
    """PyAML top level class"""

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.INSTRUMENTS:dict = {}
        for i in cfg.instruments:
            self.INSTRUMENTS[i._cfg.name]=i

    def get(self,name:str) -> Instrument:
      if name not in self.INSTRUMENTS:
        raise Exception(f"Instrument {name} not defined")
      return self.INSTRUMENTS[name]

def pyaml(fileName:str) -> PyAML:
    """Load an accelerator middle layer"""

    # Asume that all files are referenced from folder where main AML file is stored
    if not os.path.exists(fileName):
       raise Exception(f"{fileName} file nnot found")
    rootfolder = os.path.abspath(os.path.dirname(fileName))
    set_root_folder(rootfolder)
    aml_cfg = load(os.path.basename(fileName))
    aml:PyAML = depthFirstBuild(aml_cfg)
    return aml
