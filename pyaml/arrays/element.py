from ..common.element_holder import ElementHolder
from ..validation import register_schema
from .array import Array, ArraySchema


@register_schema(ArraySchema)
class Element(Array):
    """
    :py:class:`.ElementArray` configuration.

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

        Fill the :py:class:`.ElementArray` using element holder
        (:py:class:`~pyaml.lattice.simulator.Simulator`
        or :py:class:`~pyaml.control.controlsystem.ControlSystem`)
        and add the array to the holder. This method is called when an
        :py:class:`~pyaml.accelerator.Accelerator` is loaded but can be
        used to create arrays by code as shown bellow:

        .. code-block:: python

            >>> elt_cfg.fill_array(sr.design)
            >>> names = sr.design.get_elements("MyArray").names()
            >>> print(names)
            ['BPM_C04-01', 'SH1A-C04-H']

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with element array
        """
        holder.fill_element_array(self._name, self._elements)
