from ..common.element_holder import ElementHolder
from ..configuration import register_schema
from .array import Array, ArraySchema


@register_schema(ArraySchema)
class SerializedMagnets(Array):
    """
    Serialized magnets array configuration

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
        Fill the serialized magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with serialized magnet array
        """
        holder.fill_serialized_magnet_array(self._name, self._elements)
