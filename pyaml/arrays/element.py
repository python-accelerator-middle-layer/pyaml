from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "Element"


class ConfigModel(ArrayConfigModel):
    """Configuration model for :py:class:`.ElementArray`."""


class Element(ArrayConfig):
    """
    :py:class:`.ElementArray` configuration.

    Example
    -------

    An element array configuration can also be created by code using
    the following example:

    .. code-block:: python

        from pyaml.arrays.element import Element,ConfigModel as ElementArrayConfigModel
        elt_cfg = Element(
           ElementArrayConfigModel(name="MyArray", elements=["BPM_C04-01","SH1A-C04-H"])
        )


    """

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

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
        holder.fill_element_array(self._cfg.name, self._cfg.elements)
