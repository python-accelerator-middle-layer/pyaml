"""Configuration helpers for backend-provided catalogs."""

from abc import ABCMeta, abstractmethod

from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess


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


class Catalog(metaclass=ABCMeta):
    r"""
    Abstract class for backend catalog configuration objects.

    Notes
    -----
    Concrete catalogs live in each control-system package. They may expose
    backend-specific resolution APIs, but those APIs are not called by the
    PyAML core.
    """

    def __init__(self, cfg: CatalogConfigModel):
        self._cfg = cfg

    @abstractmethod
    def resolve(self, key: str) -> DeviceAccess:
        """
        Return
        """
        pass
