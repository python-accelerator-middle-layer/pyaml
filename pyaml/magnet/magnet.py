from ..common.element import Element,ElementConfigModel
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
    self.__strength:abstract.ReadWriteFloatScalar = None
    self.__hardware:abstract.ReadWriteFloatScalar = None
    self.__modelName = self.get_name()

  @property
  def strength(self) -> abstract.ReadWriteFloatScalar:
    """
    Gives access to the strength of this magnet in physics unit
    """
    self.check_peer()
    if self.__strength is None:
        raise PyAMLException(f"{str(self)} has no model that supports physics units")
    return self.__strength

  @property
  def hardware(self) -> abstract.ReadWriteFloatScalar:
    """
    Gives access to the strength of this magnet in hardware unit when possible
    """
    self.check_peer()
    if self.__hardware is None:
        raise PyAMLException(f"{str(self)} has no model that supports hardware units")
    return self.__hardware

  @property
  def model(self) -> MagnetModel:
     """
     Returns a handle to the underlying magnet model
     """
     return self.__model

  def attach(self, peer, strength: abstract.ReadWriteFloatScalar, hardware: abstract.ReadWriteFloatScalar) -> Self:
    """
    Create a new reference to attach this magnet to a simulator or a control systemand.    
    """
    obj = self.__class__(self._cfg)
    obj.__modelName = self.__modelName
    obj.__strength = strength
    obj.__hardware = hardware
    obj._peer = peer
    return obj

  def set_energy(self, energy:float):
     """
     Set the energy in eV to compute and set the magnet rigidity on the underlying magnet model.
     """
     if self.__model is not None:
        self.__model.set_magnet_rigidity(np.double(energy / speed_of_light))

  def set_model_name(self, name:str):
     """
     Sets the name of this magnet in the model (Used for combined function manget)
     """
     self.__modelName = name

  def get_model_name(self) -> str:
     """
     Returns the model name of this magnet
     """
     return self.__modelName

  def __repr__(self):
      return "%s(peer='%s', name='%s', model_name='%s', magnet_model=%s)" % (
          self.__class__.__name__,
          self.get_peer(),
          self.get_name(),
          self.__modelName,
          repr(self.__model)                    
      )
