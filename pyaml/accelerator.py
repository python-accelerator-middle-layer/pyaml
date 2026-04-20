"""
Accelerator class
"""

from pydantic import BaseModel, ConfigDict, Field

from .arrays.array import ArrayConfig
from .common.element import Element
from .common.element_holder import ElementHolder
from .common.exception import PyAMLConfigException
from .configuration import ConfigurationManager, UnsupportedConfigurationRootError
from .configuration.catalog import Catalog
from .configuration.factory import Factory
from .control.controlsystem import ControlSystem
from .lattice.simulator import Simulator
from .yellow_pages import YellowPages

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

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    facility: str
    machine: str
    energy: float
    alphac: float | None = None
    harmonic_number: int | None = None
    controls: list[ControlSystem] = None
    catalogs: list[Catalog] = None
    simulators: list[Simulator] = None
    data_folder: str
    description: str | None = None
    arrays: list[ArrayConfig] = Field(default=None, repr=False)
    devices: list[Element] = Field(repr=False)


class Accelerator(object):
    """PyAML top level class"""

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        __design = None
        __live = None
        self._controls: dict[str, ElementHolder] = {}
        self._simulators: dict[str, ElementHolder] = {}
        self._catalogs: dict[str, Catalog] = {}

        if cfg.catalogs is not None:
            for catalog in cfg.catalogs:
                name = catalog.get_name()
                if name in self._catalogs:
                    raise PyAMLConfigException(f"catalog {name} already defined")
                self._catalogs[name] = catalog

        if cfg.controls is not None:
            for c in cfg.controls:
                if c.name() == "live":
                    self.__live = c
                else:
                    # Add as dynamic attribute
                    setattr(self, c.name(), c)
                c.set_catalog(self._resolve_control_system_catalog(c))
                c.fill_device(cfg.devices)
                c._peer = self
                self._controls[c.name()] = c

        if cfg.simulators is not None:
            for s in cfg.simulators:
                if s.name() == "design":
                    self.__design = s
                else:
                    # Add as dynamic attribute
                    setattr(self, s.name(), s)
                s.fill_device(cfg.devices)
                s._peer = self
                self._simulators[s.name()] = s

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

        if cfg.alphac is not None:
            self.set_mcf(cfg.alphac)

        if cfg.harmonic_number is not None:
            self.set_harmonic_number(cfg.harmonic_number)

        self._yellow_pages = YellowPages(self)

        self.post_init()

    def _set_properties(self, method: str, value):
        # Sets global property
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                m = getattr(s, method)
                m(value)
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
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

        self._cfg.devices.append(dev)
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
                c.fill_device([dev])

        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s.fill_device([dev])

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

    def get_catalog(self, name: str) -> Catalog:
        if name not in self._catalogs:
            raise PyAMLConfigException(f"catalog {name} not defined")
        return self._catalogs[name]

    def catalogs(self) -> dict[str, Catalog]:
        return self._catalogs

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
            config_dict.pop("catalogs", None)
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

    def _resolve_control_system_catalog(self, control_system: ControlSystem) -> Catalog | None:
        catalog = control_system.get_catalog_config()
        if catalog is None:
            return None
        if isinstance(catalog, str):
            return self.get_catalog(catalog)
        if isinstance(catalog, Catalog):
            return catalog
        raise PyAMLConfigException(f"Invalid catalog configuration for control system {control_system.name()}")
