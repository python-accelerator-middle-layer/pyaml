"""
Accelerator class
"""

import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .arrays.array import ArrayConfig
from .common.element import Element
from .common.exception import PyAMLConfigException
from .configuration.factory import Factory
from .configuration.fileloader import load, set_root_folder
from .configuration.validation import validator
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
    data_folder : str, optional
        Data folder
    arrays : list[ArrayConfig], optional
        Element family
    description : str , optional
        Acceleration description
    devices : list[Element], optional
        Element list
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    facility: str
    machine: str
    energy: float
    controls: Optional[list[ControlSystem]] = None
    simulators: Optional[list[Simulator]] = None
    data_folder: Optional[str] = None
    description: Optional[str | None] = None
    arrays: Optional[list[ArrayConfig]] = Field(default=None, repr=False)
    devices: Optional[list[Element]] = Field(default=None, repr=False)


@validator(ConfigModel)
class Accelerator(object):
    """Accelerator class"""

    def __init__(
        self,
        facility: str,
        machine: str,
        energy: float,
        controls: Optional[list[ControlSystem]] = None,
        simulators: Optional[list[Simulator]] = None,
        data_folder: Optional[str] = None,
        description: Optional[str | None] = None,
        arrays: Optional[list[ArrayConfig]] = None,
        devices: Optional[list[Element]] = None,
    ):
        __design = None
        __live = None

        self._facility = facility
        self._machine = machine
        self._energy = energy
        self._controls = controls
        self._simulators = simulators
        self._data_folder = data_folder
        self._description = description
        self._arrays = arrays
        self._devices = devices

        if self._controls is not None:
            for c in self._controls:
                if c.name() == "live":
                    self.__live = c
                else:
                    # Add as dynacmic attribute
                    setattr(self, c.name(), c)
                c.fill_device(self._devices)

        if self._simulators is not None:
            for s in self._simulators:
                if s.name() == "design":
                    self.__design = s
                else:
                    # Add as dynacmic attribute
                    setattr(self, s.name(), s)
                s.fill_device(self._devices)

        if self._arrays is not None:
            for a in self._arrays:
                if self._simulators is not None:
                    for s in self._simulators:
                        a.fill_array(s)
                if self._controls is not None:
                    for c in self._controls:
                        a.fill_array(c)

        if self._energy is not None:
            self.set_energy(self._energy)

        self.post_init()

    def set_energy(self, E: float):
        """
        Set the energy for all simulators and control systems.

        Parameters
        ----------
        E : float
            Energy value to set in eV
        """
        if self._simulators is not None:
            for s in self._simulators:
                s.set_energy(E)
        if self._controls is not None:
            for c in self._controls:
                c.set_energy(E)

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        if self._simulators is not None:
            for s in self._simulators:
                s.post_init()
        if self._controls is not None:
            for c in self._controls:
                c.post_init()

    def get_description(self) -> str:
        """
        Returns the description of the accelerator
        """
        return self._description

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

    # TODO: make this generic when no config model might exist
    #    def __repr__(self):
    #        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)

    @staticmethod
    def from_dict(
        config_dict: dict, validate=True, ignore_external=False
    ) -> "Accelerator":
        """
        Construct an accelerator from a dictionary.

        Parameters
        ----------
        config_dict : str
            Dictionary containing accelerator config
        validate : bool
            Validate the input
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
        return Factory.depth_first_build(config_dict, validate, ignore_external)

    @staticmethod
    def load(
        filename: str,
        validate: bool = True,
        use_fast_loader: bool = False,
        ignore_external=False,
    ) -> "Accelerator":
        """
        Load an accelerator from a config file.

        Parameters
        ----------
        filename : str
            Configuration file name, yaml or json.
        validate : bool
            Validate the input.
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
        return Accelerator.from_dict(config_dict, validate, ignore_external)
