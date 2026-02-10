from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "BPM"


class ConfigModel(ArrayConfigModel):
    """Configuration model for BPM array."""

    ...


class BPM(ArrayConfig):
    """
    BPM array configuration

    Example
    -------
    Here is an example using a yaml configuration file:

    .. code-block:: yaml

        arrays:                    # Global array section
        - type: pyaml.arrays.bpm   # Type of array
            name: BPM              # Name of the array
            elements:              # Element names
            - BPM_C04-01
            - BPM_C04-02
            - BPM_C04-03
            - BPM_C04-04
            - BPM_C04-05

    A BPM array configuration can also be created by code using the following example:

    .. code-block:: python

        >>>  from pyaml.arrays.bpm import BPM,ConfigModel as BPMArrayConfigModel
        >>>  bpmArray = BPM(BPMArrayConfigModel(name="MyBPMs", elements=["bpm1","bpm2"])


    """

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

    def fill_array(self, holder: ElementHolder):
        """
        Fill the :py:class:`.BPMArray` using element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate the BPM array with
        """
        holder.fill_bpm_array(self._cfg.name, self._cfg.elements)
