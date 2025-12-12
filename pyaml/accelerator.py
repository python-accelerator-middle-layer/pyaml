"""
Accelerator class
"""

import os

from pydantic import BaseModel, ConfigDict

from .arrays.array import ArrayConfig
from .common.element import Element
from .common.exception import PyAMLConfigException
from .configuration.factory import Factory
from .configuration.fileloader import load, set_root_folder
from .control.controlsystem import ControlSystem
from .lattice.simulator import Simulator

# Define the main class name for this module
PYAMLCLASS = "Accelerator"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    facility: str
    "Facility name"
    machine: str
    """Accelerator name"""
    energy: float
    """Accelerator nominal energy, for ramped machine,
       this value can be dynamically set"""
    controls: list[ControlSystem] = None
    """List of control system used, an accelerator
       can access several control systems"""
    simulators: list[Simulator] = None
    """Simulator list"""
    data_folder: str
    """Data folder"""
    arrays: list[ArrayConfig] = None
    """Element family"""
    devices: list[Element]
    """Element list"""


class Accelerator(object):
    """PyAML top level class"""

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        __design = None
        __live = None

        if cfg.controls is not None:
            for c in cfg.controls:
                if c.name() == "live":
                    self.__live = c
                else:
                    # Add as dynacmic attribute
                    setattr(self, c.name(), c)
                c.fill_device(cfg.devices)

        if cfg.simulators is not None:
            for s in cfg.simulators:
                if s.name() == "design":
                    self.__design = s
                else:
                    # Add as dynacmic attribute
                    setattr(self, s.name(), s)
                s.fill_device(cfg.devices)

        if cfg.arrays is not None:
            for a in cfg.arrays:
                if cfg.simulators is not None:
                    for s in cfg.simulators:
                        a.fill_array(s)
                if cfg.controls is not None:
                    for c in cfg.controls:
                        a.fill_array(c)

        if cfg.energy is not None:
            self.set_energy(cfg.energy)

        self.post_init()

    def set_energy(self, E: float):
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s.set_energy(E)
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
                c.set_energy(E)

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s.post_init()
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
                c.post_init()

    @property
    def live(self) -> ControlSystem:
        return self.__live

    @property
    def design(self) -> Simulator:
        return self.__design

    @staticmethod
    def from_dict(config_dict: dict, ignore_external=False):
        """
        Construct an accelerator from a config file.
        Parameters
        ----------
        config_dict : str
            Dictionnary conatining accelerator config
        ignore_external: bool
            Ignore external modules and return None for object that
            cannot be created. pydantic schema that support that an
            object is not created should handle None fields.

        """
        if ignore_external:
            # control systems are external, so remove controls field
            config_dict.pop("controls", None)
        return Factory.depth_first_build(config_dict, ignore_external)

    @staticmethod
    def load(
        filename: str, use_fast_loader: bool = False, ignore_external=False
    ) -> "Accelerator":
        """
        Load an accelerator from a config file.

        Parameters
        ----------
        filename : str
            Configuration file name, yaml or json.
        use_fast_loader : bool
            Use fast yaml loader. When specified,
            no line number are reported in case of error,
            only the element name that triggered the error
            will be reported in the exception)
        ignore_external: bool
            Ignore external modules and return None for object that
            cannot be created. pydantic schema that support that an
            object is not created should handle None fields.
        """
        # Asume that all files are referenced from
        # folder where main AML file is stored
        if not os.path.exists(filename):
            raise PyAMLConfigException(f"{filename} file not found")
        rootfolder = os.path.abspath(os.path.dirname(filename))
        set_root_folder(rootfolder)
        config_dict = load(os.path.basename(filename), None, use_fast_loader)
        return Accelerator.from_dict(config_dict)
