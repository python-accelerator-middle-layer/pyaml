"""
catalog.py

Catalog abstractions used by :mod:`pyaml.configuration`.

Catalogs provide a stable public API for resolving configuration keys
into concrete :class:`~pyaml.control.deviceaccess.DeviceAccess`
instances at control-system attachment time.
"""

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess

if TYPE_CHECKING:
    from pyaml.control.controlsystem import ControlSystem


class CatalogConfigModel(BaseModel):
    r"""
    Base configuration model for named catalogs.

    Parameters
    ----------
    name : str
        Unique catalog identifier used in accelerator and control-system
        configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str


class CatalogResolver(metaclass=ABCMeta):
    r"""
    Bound resolver used by a control system to resolve catalog keys.

    A :class:`CatalogResolver` encapsulates the runtime resolution logic
    for one attached control-system context.
    """

    @abstractmethod
    def resolve(self, key: str) -> DeviceAccess:
        r"""
        Resolve a catalog key into a device access object.

        Parameters
        ----------
        key : str
            Catalog key to resolve.

        Returns
        -------
        DeviceAccess
            Resolved device access instance.
        """
        raise NotImplementedError


class Catalog(CatalogResolver, metaclass=ABCMeta):
    r"""
    Base abstraction for resolving catalog keys into devices.

    A :class:`Catalog` is attached to a
    :class:`~pyaml.control.controlsystem.ControlSystem` and is then used
    to resolve string references found in PyAML object configuration
    into concrete :class:`~pyaml.control.deviceaccess.DeviceAccess`
    instances.

    Notes
    -----
    Concrete implementations live in each control-system package
    (e.g. ``tango.pyaml.static_catalog``). External projects may
    derive from :class:`Catalog` to implement different resolution
    strategies while preserving the same public API.
    """

    def __init__(self, cfg: CatalogConfigModel):
        self._cfg = cfg

    def get_name(self) -> str:
        r"""
        Return the catalog name.

        Returns
        -------
        str
            Catalog identifier.
        """
        return self._cfg.name

    def attach_control_system(self, control_system: "ControlSystem"):
        r"""
        Create a resolver bound to one control system.

        Parameters
        ----------
        control_system : ControlSystem
            Control system using this catalog.

        Returns
        -------
        CatalogResolver
            Resolver instance bound to ``control_system``.

        Notes
        -----
        The default implementation returns ``self``. Subclasses may
        override this hook to return a dedicated per-control-system
        resolver while keeping the catalog object itself shared.
        """
        return self
