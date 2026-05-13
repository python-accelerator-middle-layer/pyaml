"""
Accelerator class
"""

from pydantic import BaseModel, ConfigDict, Field

from .arrays.array import Array, ArraySchema
from .common.element import Element, ElementSchema
from .common.element_holder import ElementHolder
from .common.exception import PyAMLConfigException
from .configuration import ConfigurationManager, UnsupportedConfigurationRootError
from .configuration.configuration_models import ConfigurationSchema
from .configuration.factory import Factory
from .control.controlsystem import ControlSystem, ControlSystemSchema
from .lattice.simulator import Simulator, SimulatorSchema
from .yellow_pages import YellowPages


class AcceleratorSchema(ConfigurationSchema):
    """
    Schema for Accelerator

    Parameters
    ----------
    facility : str
        Facility name
    machine : str
        Accelerator name
    energy : float
        Accelerator nominal energy. For ramped machine,
        this value can be dynamically set
    alphac : float, optional
        Moment compaction factor.
    harmonic_number: int, optional
        Number of bucket
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
    """

    model_config = ConfigDict(extra="forbid")

    facility: str
    machine: str
    energy: float
    alphac: float | None = None
    harmonic_number: int | None = None
    controls: list[ControlSystemSchema] = None
    simulators: list[SimulatorSchema] = None
    data_folder: str
    description: str | None = None
    arrays: list[ArraySchema] = Field(default=None, repr=False)
    devices: list[ElementSchema] = Field(default=None, repr=False)


class Accelerator(object):
    """PyAML top level class"""

    def __init__(
        self,
        facility: str,
        machine: str,
        energy: float,
        data_folder: str,
        alphac: float | None = None,
        harmonic_number: int | None = None,
        controls: list[ControlSystem] = None,
        simulators: list[Simulator] = None,
        description: str | None = None,
        arrays: list[Array] | None = None,
        devices: list[Element] | None = None,
    ):
        self.facility = facility
        self.machine = machine

        __design = None
        __live = None

        self._controls: dict[str, ElementHolder] = {}
        self._simulators: dict[str, ElementHolder] = {}

        if controls is not None:
            for c in controls:
                if c.name() == "live":
                    self.__live = c
                else:
                    # Add as dynamic attribute
                    setattr(self, c.name(), c)
                c.fill_device(devices)
                c._peer = self
                self._controls[c.name()] = c

        if simulators is not None:
            for s in simulators:
                if s.name() == "design":
                    self.__design = s
                else:
                    # Add as dynamic attribute
                    setattr(self, s.name(), s)
                s.fill_device(devices)
                s._peer = self
                self._simulators[s.name()] = s

        if arrays is not None:
            for a in arrays:
                if simulators is not None:
                    for s in simulators:
                        a.fill_array(s)
                if controls is not None:
                    for c in controls:
                        a.fill_array(c)

        if energy is not None:
            self.set_energy(energy)

        if alphac is not None:
            self.set_mcf(alphac)

        if harmonic_number is not None:
            self.set_harmonic_number(harmonic_number)

        self._yellow_pages = YellowPages(self)

        self.post_init()

    def _set_properties(self, method: str, value):
        # Sets global property
        if self._simulators is not None:
            for s in self._simulators:
                m = getattr(s, method)
                m(value)
        if self._controls is not None:
            for c in self._controls:
                m = getattr(c, method)
                m(value)

    def set_energy(self, E: float):
        """
        Set the energy for all simulators and control systems.

        Parameters
        ----------
        E : float
            Energy value to set in eV
        """
        self._set_properties("_set_energy", E)

    def set_mcf(self, alphac: float):
        """
        Set the moment compaction factor for all simulators and control systems.

        Parameters
        ----------
        alphac : float
            Moment compaction factor
        """
        self._set_properties("_set_mcf", alphac)

    def set_harmonic_number(self, h: int):
        """
        Set the number of bucket.

        Parameters
        ----------
        h : int
            Number of bucket
        """
        self._set_properties("_set_harmonic", h)

    def add_device(self, config: dict, ignore_external=False):
        """
        Dynamically add a device to this accelerator

        config_dict : str
            Dictionary containing accelerator config
        ignore_external: bool
            Ignore external modules and return None for object that
            cannot be created. pydantic schema that support that an
            object is not created should handle None fields.
        """
        dev = Factory.depth_first_build(config, ignore_external)
        if not isinstance(dev, Element):
            raise PyAMLConfigException(
                "Invalid device type, Element or sub classes of Element expected " + f"but got {dev.__class__.__name__}"
            )

        self._devices.append(dev)
        if self._controls is not None:
            for c in self._controls:
                c.fill_device([dev])

        if self._simulators is not None:
            for s in self._simulators:
                s.fill_device([dev])

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

    @property
    def yellow_pages(self) -> YellowPages:
        return self._yellow_pages

    def simulators(self) -> dict[str, "ElementHolder"]:
        """Return all registered simulator modes."""
        return self._simulators

    def controls(self) -> dict[str, "ElementHolder"]:
        """Return all registered control modes."""
        return self._controls

    def modes(self) -> dict[str, "ElementHolder"]:
        """Return all registered control and simulator modes."""
        modes: dict[str, "ElementHolder"] = {}
        modes.update(self._simulators)
        modes.update(self._controls)
        return modes

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
    def load(filename: str, use_fast_loader: bool = False, ignore_external=False) -> "Accelerator":
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
        manager = ConfigurationManager()
        try:
            manager.add(filename, use_fast_loader=use_fast_loader)
        except UnsupportedConfigurationRootError as ex:
            raise PyAMLConfigException(
                "Accelerator.load() expects a 'pyaml.accelerator' root configuration. "
                "Use the factory APIs to build sub-elements directly."
            ) from ex
        return manager.build(ignore_external=ignore_external)
