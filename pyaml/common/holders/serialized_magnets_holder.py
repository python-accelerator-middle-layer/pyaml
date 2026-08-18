from typing import TYPE_CHECKING

from ...arrays.serialized_magnet_array import SerializedMagnetsArray

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class SerializedMagnetsHolder:
    def __init__(self, peer: "ElementHolder"):
        self._peer = peer

    def get(self, name: str = None) -> SerializedMagnetsArray:
        """
        Returns the specified serialized magnet array or all serialized magnets if no name specified

        Parameters
        ----------
        name : str
            Name of the serialized magnet array
        """
        if name is None:
            return SerializedMagnetsArray("", self._peer.serialized_magnet.all())
        else:
            return self._peer._get("serialized Magnet array", name, self._peer._SERIALIZED_MAGNETS_ARRAYS)

    def add(self, arrayName: str, elementNames: list[str]):
        """
        Adds the specified serialied magnet array to the holder

        Parameters
        ----------
        arrayName : str
            Array name
        elementNames : list[str]
            List of magnet names
        """
        self._peer._fill_array(
            arrayName,
            elementNames,
            self._peer.serialized_magnet.get,
            SerializedMagnetsArray,
            self._peer._SERIALIZED_MAGNETS_ARRAYS,
        )

    def __getitem__(self, key):
        return self.get().__getitem__(key)
