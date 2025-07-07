"""
PyAML main class
"""

from .control.controlsystem import ControlSystem
from .control.element import Element
from .lattice.simulator import Simulator
from .lattice.array import Array
from .configuration.factory import depthFirstBuild
from pyaml.configuration import load
from pydantic import BaseModel,ConfigDict

# Define the main class name for this module
PYAMLCLASS = "AML"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    instrument: str
    """Instrument name"""
    control: ControlSystem = None
    """control system"""
    simulators: list[Simulator] = None
    """Simulator list"""
    data_folder: str
    """Data folder"""
    arrays: list[Array] = None
    """Element family"""
    devices: list[Element]
    """Element list"""


class AML(object):    
    """PyAML top level class"""
    
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg


def pyaml(fileName:str) -> AML:
    """Load an accelerator middle layer"""

    # Asume that all files are referenced from folder where main AML file is stored
    aml_cfg = load(fileName)
    aml:AML = depthFirstBuild(aml_cfg)
    return aml
