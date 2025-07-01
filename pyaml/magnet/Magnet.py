from pyaml.control.Element import Element

class Magnet(Element):

  """
  Class providing access to one magnet of a physical or simulated lattice

  Attributes:
  strength (ReadWriteFloatScalar): Magnet strength
  """
  def __init__(self, name=None):
    super().__init__(name)

  def __repr__(self):
    return "%s(name=%s)" % (
      self.__class__.__name__, self.name)