from pyaml.lattice.element import Element,ElementConfigModel
from .. import PyAMLException
from ..common import abstract
from .model import MagnetModel
from scipy.constants import speed_of_light
try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
import numpy as np

class MagnetConfigModel(ElementConfigModel):

    model: MagnetModel | None = None
    """Object in charge of converting magnet strenghts to power supply values"""

class Magnet(Element):
  """
  Class providing access to one magnet of a physical or simulated lattice
  """

  def __init__(self, name:str, model:MagnetModel = None):
    """
    Construct a magnet

    Parameters
    ----------
    name : str
        Element name
    model : MagnetModel
        Magnet model in charge of computing coil(s) current
    """
    super().__init__(name)
    self.__model = model
    self.__strength = None
    self.__hardware = None

  @property
  def strength(self) -> abstract.ReadWriteFloatScalar:
    if self.__strength is None:
        raise PyAMLException(f"{str(self)} is unattached or has no model that supports physics units")
    return self.__strength

  @property
  def hardware(self) -> abstract.ReadWriteFloatScalar:
    if self.__hardware is None:
        raise PyAMLException(f"{str(self)} is unattached or has no model that supports hardware units")
    return self.__hardware

  @property
  def model(self) -> MagnetModel:
     return self.__model

  def attach(self, strength: abstract.ReadWriteFloatScalar, hardware: abstract.ReadWriteFloatScalar) -> Self:
    # Attach strength and current attribute and returns a new reference
    obj = self.__class__(self._cfg)
    obj.__strength = strength
    obj.__hardware = hardware
    return obj

  def set_energy(self, energy:float):
     if self.__model is not None:
        self.__model.set_magnet_rigidity(np.double(energy / speed_of_light))
