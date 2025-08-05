from pyaml.lattice.element import Element,ElementConfigModel
from ..control.deviceaccess import DeviceAccess
from ..control import abstract
from .model import MagnetModel
from scipy.constants import speed_of_light
from typing import Self

class MagnetConfigModel(ElementConfigModel):

    hardware: DeviceAccess | None = None
    """Direct access to a magnet device that provides strength/current conversion"""
    model: MagnetModel | None = None
    """Object in charge of converting magnet strenghts to power supply values"""

class Magnet(Element):
  """
  Class providing access to one magnet of a physical or simulated lattice
  """

  def __init__(self, name:str, linked_elements:list[str], hardware:DeviceAccess = None, model:MagnetModel = None):
    """
    Construct a magnet

    Parameters
    ----------
    name : str
        Element name
    hardware : DeviceAccess
        Direct access to a hardware (bypass the magnet model)
    model : MagnetModel
        Magnet model in charge of comutping coil(s) current
    """
    super().__init__(name, linked_elements)
    self.__model = model
    self.__strength = None
    self.__hardware = None
    if hardware is not None:
      # TODO
      # Direct access to a magnet device that supports strength/current conversion
      raise Exception(
          " %s, hardware access not implemented" % (self.__class__.__name__,name)
      )
    
  @property
  def strength(self) -> abstract.ReadWriteFloatScalar:
    return self.__strength

  @property
  def hardware(self) -> abstract.ReadWriteFloatScalar:
    if self.__hardware is None:
        raise Exception(f"{str(self)} has no model that supports hardware units")
    return self.__hardware

  @property
  def model(self) -> MagnetModel:
     return self.__model

  def attach(self, strength: abstract.ReadWriteFloatScalar, hardware: abstract.ReadWriteFloatScalar) -> Self:
    # Attach strengh and current attribute and returns a new reference
    obj = self.__class__(self._cfg)
    obj.__strength = strength
    obj.__hardware = hardware
    return obj

  def set_energy(self,E:float):
     if(self.__model is not None):
        self.__model.set_magnet_rigidity(E/speed_of_light)
