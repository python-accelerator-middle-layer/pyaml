from typing import TYPE_CHECKING

from ..magnet.serialized_magnet import SerializedMagnets

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class SerializedMagnetHolder:
    def __init__(self, peer: "ElementHolder"):
        self._peer = peer

    def all(self) -> list[SerializedMagnets]:
        """
        Returns all serialized magnets as a list
        """
        return [value for key, value in self._peer._SERIALIZED_MAGNETS.items()]

    def get(self, name: str) -> SerializedMagnets:
        """
        Returns the specified magnet

        Parameters
        ----------
        name : str
            Name of the magnet
        """
        return self._peer._get("Serialized magnet", name, self._peer._SERIALIZED_MAGNETS)

    def add(self, m: SerializedMagnets):
        """
        Adds the specified magnet to the holder

        Parameters
        ----------
        m : Magnet
           Magnet to be added
        """
        self._peer._add(self._peer._SERIALIZED_MAGNETS, m)
