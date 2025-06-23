from pyaml.control import Element

class Magnet(Element.Element):

  """
  Class providing access to one magnet of a physical or simulated lattice

  Attributes:
  strength (ReadWriteScalar): Magnet strength
  """

  def __init__(self, name=None):
    super().__init__(name)

  def __repr__(self):
    return "%s(name=%s)" % (
      self.__class__.__name__, self.name)