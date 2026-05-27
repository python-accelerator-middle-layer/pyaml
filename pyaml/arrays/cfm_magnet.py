from ..common.element_holder import ElementHolder
from ..validation import register_schema
from .array import Array, ArraySchema


@register_schema(ArraySchema)
class CombinedFunctionMagnet(Array):
    """
    Combined function magnet array confirguration.

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
        Fill the combined function magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with combined function magnet array
        """
        holder.fill_cfm_magnet_array(self._name, self._elements)
