from typing import TYPE_CHECKING

from ...magnet.cfm_magnet import CombinedFunctionMagnet

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class CombinedFunctionMagnetHolder:
    def __init__(self, peer: "ElementHolder"):
        self._peer = peer

    def all(self) -> list[CombinedFunctionMagnet]:
        """
        Returns all combined function magnets as a list
        """
        return [value for key, value in self._peer._CFM_MAGNETS.items()]

    def get(self, name: str) -> CombinedFunctionMagnet:
        """
        Returns the specified combined function magnet

        Parameters
        ----------
        name : str
            Name of the magnet
        """
        return self._peer._get("Combined function magnet", name, self._peer._CFM_MAGNETS)

    def add(self, m: CombinedFunctionMagnet):
        """
        Adds the specified combined function magnet to the holder

        Parameters
        ----------
        m : Magnet
           Magnet to be added
        """
        self._peer._add(self._peer._CFM_MAGNETS, m)
