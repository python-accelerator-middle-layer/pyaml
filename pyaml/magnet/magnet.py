from pyaml.lattice.element import Element
from ..control.deviceaccess import DeviceAccess
from ..control import abstract
from .unitconv import UnitConv
from scipy.constants import speed_of_light
from typing import Self

class Magnet(Element):
  """
  Class providing access to one magnet of a physical or simulated lattice

  Attributes:
  strength (ReadWriteFloatScalar): Magnet strength
  current (ReadWriteFloatScalar): Magnet current
  """
  def __init__(self, name:str, hardware:DeviceAccess = None, unitconv:UnitConv = None):
    super().__init__(name)
    self.unitconv = unitconv
    __strength = None
    __current = None
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
  def current(self) -> abstract.ReadWriteFloatScalar:
    if self.__current is None:
        raise Exception(f"{str(self)} has non trivial strenght<->current unitconv model")
    return self.__current

  def attach(self, strength: abstract.ReadWriteFloatScalar, current: abstract.ReadWriteFloatScalar) -> Self:
    # Attach strengh and current attribute and returns a new reference
    obj = self.__class__(self._cfg)
    obj.__strength = strength
    obj.__current = current
    return obj

  def set_energy(self,E:float):
     if(self.unitconv is not None):
        self.unitconv.set_magnet_rigidity(E/speed_of_light)
