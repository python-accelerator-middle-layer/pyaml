"""
Accelerator class
"""

import warnings

from .arrays.array import ArrayConfig
from .common.element import Element, __pyaml_repr__
from .common.element_holder import ElementHolder
from .common.exception import PyAMLConfigException
from .configuration import ConfigurationManager, UnsupportedConfigurationRootError
from .configuration.factory import Factory
from .control.controlsystem import ControlSystem
from .lattice.simulator import Simulator
from .validation import SchemaValidator
from .yellow_pages import YellowPages

# Define the main class name for this module
PYAMLCLASS = "Accelerator"


class Accelerator:
    """
    Top-level accelerator object.

    An Accelerator represents a complete accelerator model, including its
    machine-wide properties, devices, arrays, control systems, and simulators.
    It serves as the main entry point for loading, constructing, and interacting
    with an accelerator configuration.

    Parameters
    ----------
    facility : str
        Facility name.
    machine : str
        Accelerator name.
    energy : float
        Nominal accelerator energy.
    alphac : float, optional
        Momentum compaction factor.
    harmonic_number : int, optional
        Harmonic number.
    controls : list[ControlSystem], optional
        Control systems associated with the accelerator.
    simulators : list[Simulator], optional
        Simulators associated with the accelerator.
    arrays : list[ArrayConfig], optional
        Array configurations.
    devices : list[Element], optional
        Accelerator devices.
    data_folder : str, optional
        Path to the accelerator data directory.
    description : str, optional
        Human-readable description of the accelerator.

    Notes
    -----
    Control systems and simulators are registered by name and are exposed as
    attributes of the accelerator instance. The control system named ``"live"``
    and the simulator named ``"design"`` are additionally available through the
    :attr:`live` and :attr:`design` properties.
    """

    def __init__(
        self,
        facility: str,
        machine: str,
        energy: float,
        alphac: float | None = None,
        harmonic_number: int | None = None,
        controls: list[ControlSystem] | None = None,
        simulators: list[Simulator] | None = None,
        arrays: list[ArrayConfig] | None = None,
        devices: list[Element] | None = None,
        data_folder: str | None = None,
        description: str | None = None,
    ):
        self.facility = facility
        self.machine = machine
        self._data_folder = data_folder
        self.description = description

        self._energy = float(energy) if energy is not None else None
        self._alphac = float(alphac) if alphac is not None else None
        self._harmonic_number = int(harmonic_number) if harmonic_number is not None else None

        self._arrays = arrays
        self._devices = devices

        self.__design = None
        self.__live = None

        self._controls: dict[str, ElementHolder] = {}
        self._simulators: dict[str, ElementHolder] = {}

        if controls is not None:
            for c in controls:
                if c.name() == "live":
                    self.__live = c
                else:
                    # Add as dynamic attribute
                    setattr(self, c.name(), c)
                c.fill_device(self._devices)
                c._peer = self
                self._controls[c.name()] = c

        if simulators is not None:
            for s in simulators:
                if s.name() == "design":
                    self.__design = s
                else:
                    # Add as dynamic attribute
                    setattr(self, s.name(), s)
                s.fill_device(self._devices)
                s._peer = self
                self._simulators[s.name()] = s

        if arrays is not None:
            for a in self._arrays:
                if self._simulators is not None:
                    for s in self._simulators.values():
                        a.fill_array(s)
                if self._controls is not None:
                    for c in self._controls.values():
                        a.fill_array(c)

        if self._energy is not None:
            self.set_energy(self._energy)

        if self._alphac is not None:
            self.set_mcf(self._alphac)

        if self._harmonic_number is not None:
            self.set_harmonic_number(self._harmonic_number)

        self._yellow_pages = YellowPages(self)

        self.post_init()

    def _set_properties(self, method: str, value):
        # Sets global property
        if self._simulators is not None:
            for s in self._simulators.values():
                m = getattr(s, method)
                m(value)
        if self._controls is not None:
            for c in self._controls.values():
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
        dev = Factory.build(config, ignore_external)
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
            for s in self._simulators.values():
                s.post_init()
        if self._controls is not None:
            for c in self._controls.values():
                c.post_init()

    def get_description(self) -> str:
        """
        Returns the description of the accelerator
        """
        return self.description

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
        return __pyaml_repr__(self)

    @staticmethod
    def from_dict(config_dict: dict, ignore_external: bool = False, validate: bool = False) -> "Accelerator":
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

        if validate:
            config_dict = SchemaValidator.validate_to_dict(config_dict)

        # Ensure factory is clean before building a new accelerator
        Factory.clear()
        return Factory.build(config_dict, ignore_external)

    @staticmethod
    def load(filename: str, include_locations: bool = False, ignore_external=False, validate: bool = False) -> "Accelerator":
        """
        Load an accelerator from a config file.

        Parameters
        ----------
        filename : str
            Configuration file name, yaml or json.
        include_locations : bool
            When False, use faster loader but no line number
            are reported in case of error,
            only the element name that triggered the error
            will be reported in the exception
        ignore_external : bool
            Ignore external modules and return None for object that
            cannot be created. pydantic schema that support that an
            object is not created should handle None fields.
        validate : bool
            Validate the loaded data
        """

        manager = ConfigurationManager()

        if not validate and include_locations:
            warnings.warn(
                "'include_locations=True' is ignored when 'validate=False'. "
                "Source-location metadata is only needed for validation.",
                UserWarning,
                stacklevel=2,
            )
            include_locations = False

        try:
            manager.add(filename, include_locations=include_locations)
        except UnsupportedConfigurationRootError as ex:
            raise PyAMLConfigException(
                "Accelerator.load() expects a 'pyaml.accelerator' root configuration. "
                "Use the factory APIs to build sub-elements directly."
            ) from ex
        return manager.build(ignore_external=ignore_external, validate=validate)
