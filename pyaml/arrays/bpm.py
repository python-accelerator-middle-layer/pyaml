from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "BPM"


class ConfigModel(ArrayConfigModel):
    """Configuration model for BPM array."""


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

    A BPM array configuration can also be created by code using the following example:

    .. code-block:: python

        >>>  from pyaml.arrays.bpm import BPM,ConfigModel as BPMArrayConfigModel
        >>>  bpm_cfg = BPM(BPMArrayConfigModel(
                        name="BPM",
                        elements=["BPM_C04-01","BPM_C04-02","BPM_C04-03"]
                       ))

    """

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

    def fill_array(self, holder: ElementHolder):
        """
        Fill the :py:class:`.BPMArray` using element holder. This method is called
        when an :py:class:`~pyaml.accelerator.Accelerator` is loaded but can be
        used to create arrays by code as shown bellow:

        .. code-block:: python

            >>> bpm_cfg.fill_array(sr.design) # For arrays created on the fly
            >>> orbit = sr.design.get_bpms("BPM").positions.get()
            >>> print(orbit)
            [[ 6.02736506e-10  0.00000000e+00]
             [-3.06292158e-08  0.00000000e+00]
             [-2.80366116e-08  0.00000000e+00]]

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate the BPM array with
        """
        holder.fill_bpm_array(self._cfg.name, self._cfg.elements)
