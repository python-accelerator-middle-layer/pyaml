from typing import TYPE_CHECKING

from ..magnet.magnet import Magnet

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class MagnetHolder:
    def __init__(self, peer: "ElementHolder"):
        self._peer = peer

    def all(self) -> list[Magnet]:
        """
        Returns all magnets as a list
        """
        return [value for key, value in self._peer._MAGNETS.items()]

    def get(self, name: str) -> Magnet:
        """
        Returns the specified magnet

        Parameters
        ----------
        name : str
            Name of the magnet
        """
        return self._peer._get("Magnet", name, self._peer._MAGNETS)

    def add(self, m: Magnet):
        """
        Adds the specified magnet to the holder

        Parameters
        ----------
        m : Magnet
           Magnet to be added
        """
        self._peer._add(self._peer._MAGNETS, m)
