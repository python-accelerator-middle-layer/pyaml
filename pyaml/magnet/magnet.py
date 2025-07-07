from pyaml.control.element import Element
from ..control.deviceaccess import DeviceAccess
from ..control import abstract
from ..lattice.abstract_impl import RWMapper
from ..lattice.abstract_impl import RCurrentScalar
from ..lattice.abstract_impl import RWStrengthScalar
from .unitconv import UnitConv

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

    if hardware is not None:
      # TODO
      # Direct access to a magnet device that supports strength/current conversion
      raise Exception(
          " %s, hardware access not implemented" % (self.__class__.__name__,name)
      )
    
    # In case of unitconv is none, no control system access possible
    self.strength: abstract.ReadWriteFloatScalar = RWStrengthScalar(
      name, self.unitconv
    )
    self.current: abstract.ReadFloatScalar = RCurrentScalar(self.unitconv)

  def set_source(self, source: abstract.ReadWriteFloatArray, idx: int):
      """Set the peer combined function magnet"""
      # Override strength, map single strength to multipole
      self.strength: abstract.ReadWriteFloatScalar = RWMapper(source, idx)
