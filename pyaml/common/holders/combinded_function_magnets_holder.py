from typing import TYPE_CHECKING

from ...arrays.cfm_magnet_array import CombinedFunctionMagnetArray

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class CombinedFunctionMagnetsHolder:
    def __init__(self, peer: "ElementHolder"):
        self._peer = peer

    def get(self, name: str = None) -> CombinedFunctionMagnetArray:
        """
        Returns the specified conbined function magnet array or all combined function magnets if no name specified

        Parameters
        ----------
        name : str
            Name of the combined function magnet array
        """
        if name is None:
            return CombinedFunctionMagnetArray("", self._peer.combined_function_magnet.all())
        else:
            return self._peer._get("Combined function magnet array", name, self._peer._CFM_MAGNET_ARRAYS)

    def add(self, arrayName: str, elementNames: list[str]):
        """
        Adds the specified combined function magnet array to the holder

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
            self._peer.combined_function_magnet.get,
            CombinedFunctionMagnetArray,
            self._peer._CFM_MAGNET_ARRAYS,
        )

    def __getitem__(self, key):
        return self.get().__getitem__(key)
