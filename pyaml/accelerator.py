"""
Accelerator class
"""

import os

from pydantic import BaseModel, ConfigDict, Field

from .arrays.array import ArrayConfig
from .common.element import Element
from .common.exception import PyAMLConfigException
from .configuration.catalog import Catalog
from .configuration.factory import Factory
from .configuration.fileloader import load, set_root_folder
from .control.controlsystem import ControlSystem
from .lattice.simulator import Simulator

# Define the main class name for this module
PYAMLCLASS = "Accelerator"


class ConfigModel(BaseModel):
    """
    Configuration model for Accelerator

    Parameters
    ----------
    facility : str
        Facility name
    machine : str
        Accelerator name
    energy : float
        Accelerator nominal energy. For ramped machine,
        this value can be dynamically set
    controls : list[ControlSystem], optional
        List of control system used. An accelerator
        can access several control systems
    simulators : list[Simulator], optional
        Simulator list
    data_folder : str
        Data folder
    arrays : list[ArrayConfig], optional
        Element family
    description : str , optional
        Acceleration description
    devices : list[.common.element.Element]
        Element list
    control_system_catalog : Catalog
        catalog of DeviceAccess objects
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    facility: str
    machine: str
    energy: float
    controls: list[ControlSystem] = None
    simulators: list[Simulator] = None
    data_folder: str
    description: str | None = None
    arrays: list[ArrayConfig] = Field(default=None, repr=False)
    devices: list[Element] = Field(repr=False)
    control_system_catalogs: list[Catalog] = None


class Accelerator(object):
    """PyAML top level class"""

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        __design = None
        __live = None

        # TODO Manage mapping between catalogs and control systems
        catalog = (
            cfg.control_system_catalogs[0]
            if cfg.control_system_catalogs is not None
            and len(cfg.control_system_catalogs) > 0
            else None
        )
        if cfg.controls is not None:
            for c in cfg.controls:
                c.set_catalog(catalog)
                if c.name() == "live":
                    self.__live = c
                else:
                    # Add as dynamic attribute
                    setattr(self, c.name(), c)
                c.fill_device(cfg.devices)

        if cfg.simulators is not None:
            for s in cfg.simulators:
                if s.name() == "design":
                    self.__design = s
                else:
                    # Add as dynamic attribute
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
        """
        Set the energy for all simulators and control systems.

        Parameters
        ----------
        E : float
            Energy value to set in eV
        """
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

    def get_description(self) -> str:
        """
        Returns the description of the accelerator
        """
        return self._cfg.description

    @property
    def live(self) -> ControlSystem:
        """
        Get the live control system.

        Returns
        -------
        ControlSystem
            The live control system instance
        """
        return self.__live

    @property
    def design(self) -> Simulator:
        """
        Get the design simulator.

        Returns
        -------
        Simulator
            The design simulator instance
        """
        return self.__design

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)

    @staticmethod
    def from_dict(config_dict: dict, ignore_external=False) -> "Accelerator":
        """
        Construct an accelerator from a dictionary.

        Parameters
        ----------
        config_dict : str
            Dictionary containing accelerator config
        ignore_external: bool
            Ignore external modules and return None for object that
            cannot be created. pydantic schema that support that an
            object is not created should handle None fields.
        """

        if ignore_external:
            # control systems are external, so remove controls field
            config_dict.pop("controls", None)
        # Ensure factory is clean before building a new accelerator
        Factory.clear()
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
        ignore_external : bool
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
