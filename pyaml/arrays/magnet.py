from ..common.element_holder import ElementHolder
from ..validation import register_schema
from .array import Array, ArraySchema


@register_schema(ArraySchema)
class Magnet(Array):
    """
    Magnet array confirguration.
    """

    def __init__(
        self,
        name: str,
        elements: list[str],
    ):
        self._name = name
        self._elements = elements

    def fill_array(self, holder: ElementHolder):
        """
        Fill the magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with magnet array
        """
        holder.fill_magnet_array(self._name, self._elements)
