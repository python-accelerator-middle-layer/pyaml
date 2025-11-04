from .instrument import Instrument
from .configuration.factory import Factory
from .configuration import load,set_root_folder
from .common.exception import PyAMLException

from pydantic import BaseModel,ConfigDict
import logging
import os

# Define the main class name for this module
PYAMLCLASS = "PyAML"

logger = logging.getLogger(__name__)

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

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
        raise PyAMLException(f"Instrument {name} not defined")
      return self.INSTRUMENTS[name]

def pyaml(filename:str) -> PyAML:
    """Load an accelerator middle layer"""
    logger.log(logging.INFO, f"Loading PyAML from file '{filename}'")

    # Asume that all files are referenced from folder where main AML file is stored
    if not os.path.exists(filename):
       raise PyAMLException(f"{filename} file not found")
    rootfolder = os.path.abspath(os.path.dirname(filename))
    set_root_folder(rootfolder)
    aml_cfg = load(os.path.basename(filename))
    aml:PyAML = Factory.depth_first_build(aml_cfg)
    return aml
