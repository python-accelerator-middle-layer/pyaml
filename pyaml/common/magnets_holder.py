from typing import TYPE_CHECKING

from ..arrays.magnet_array import MagnetArray

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class MagnetsHolder:
    def __init__(self, peer: "ElementHolder"):
        self._peer = peer

    def get(self, name: str = None) -> MagnetArray:
        """
        Returns the specified magnet array or all magnets if no name specified

        Parameters
        ----------
        name : str
            Name of the magnet array
        """
        if name is None:
            return MagnetArray("", self._peer.magnet.all())
        else:
            return self._peer._get("Magnet array", name, self._peer._MAGNET_ARRAYS)

    def add(self, arrayName: str, elementNames: list[str]):
        """
        Adds the specified magnet array to the holder

        Parameters
        ----------
        arrayName : str
            Array name
        elementNames : list[str]
            List of magnet names
        """
        self._peer._fill_array(arrayName, elementNames, self._peer.magnet.get, MagnetArray, self._peer._MAGNET_ARRAYS)

    def __getitem__(self, key):
        return self.get().__getitem__(key)
