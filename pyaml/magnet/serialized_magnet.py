import numpy as np
from numpy import typing as npt
from pydantic import BaseModel,ConfigDict
from scipy.constants import speed_of_light

from .magnet import Magnet, MagnetConfigModel
from .model import MagnetModel
from .. import PyAMLException
from ..common import abstract
from ..common.abstract import RWMapper
from ..common.element import Element, ElementConfigModel, __pyaml_repr__
from ..configuration import Factory
from ..control.deviceaccess import DeviceAccess
from .function_mapping import function_map

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnetsModel"


class ConfigModel(ElementConfigModel):
    function: str
    """List of magnets"""
    elements: list[str]
    """List of magnets"""
    model: MagnetModel | None = None
    """Object in charge of converting magnet strengths to currents"""


class SerializedMagnetsModel(Element):
    """
    Class managing serialized magnets: a set of magnet with the same set point.
    The set point is usually managed by only one power supply but it can be covered by several ones.
    If several power supplies


    Parameters
    ----------
    cfg : ConfigModel
        Configuration object TODO: to describe

    Raises
    ------
    pyaml.PyAMLException
        In case of wrong initialization
    """

    def __init__(self, cfg: ConfigModel, peer = None):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.model = cfg.model
        self.polynom = None
        self.__virtuals:list[Magnet] = []

        if peer is None:

            # Configuration part
            self.polynom = function_map[self._cfg.function].polynom
            if not self._cfg.function in function_map:
                raise PyAMLException(self._cfg.function + " not implemented for serialized magnet")
            for element in self._cfg.elements:
                # Check mapping validity
                # Create the virtual magnet for the corresponding magnet
                vm = self.__create_virtual_magnet(element)
                self.__virtuals.append(vm)
                # Register the virtual element in the factory to have a coherent factory and improve error reporting
                Factory.register_element(vm)
        else:
             # Attach
             self._peer = peer

    def __create_virtual_magnet(self,name:str) -> Magnet:
            args = {"name":name,"model":self.model}
            virtual:Magnet = function_map[self._cfg.function](MagnetConfigModel(**args))
            virtual.set_model_name(self.get_name())
            return virtual

    def get_nb_magnets(self) -> int:
        return len(self._cfg.elements)

    def get_magnets(self) -> list[Magnet]:
        return self.__virtuals

    def attach(self, peer, strengths: list[abstract.ReadWriteFloatScalar], hardwares: list[abstract.ReadWriteFloatScalar]) -> list[Magnet]:
        l = []
        # Construct a single function magnet for each multipole of this combined function magnet
        for idx, magnet in enumerate(self._cfg.elements):
            strength = strengths[idx]
            hardware = hardwares[idx] if self.model.has_hardware() else None
            l.append(self.__virtuals[idx].attach(peer, strength, hardware))
        return l

    @property
    def strengths(self) -> abstract.ReadWriteFloatScalar:
        """
        Gives access to the strengths of this combined function magnet in physics unit
        """
        self.check_peer()
        if self.__strengths is None:
            raise PyAMLException(f"{str(self)} has no model that supports physics units")
        return self.__strengths

    @property
    def hardwares(self) -> abstract.ReadWriteFloatScalar:
        """
        Gives access to the strengths of this combined function magnet in hardware unit when possible
        """
        self.check_peer()
        if self.__hardwares is None:
            raise PyAMLException(f"{str(self)} has no model that supports hardware units")
        return self.__hardwares

    def set_energy(self, energy: float):
        if (self.model is not None):
            self.model.set_magnet_rigidity(energy / speed_of_light)

    def __repr__(self):
        return __pyaml_repr__(self)

    def get_devices(self) -> list[DeviceAccess]:
        if isinstance(self.model.powerconverter, list):
            return self.model.powerconverter
        else:
            return [self._cfg.powerconverter]
