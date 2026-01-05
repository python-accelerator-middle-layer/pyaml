from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "BPM"


class ConfigModel(ArrayConfigModel): ...


class BPM(ArrayConfig):
    """
    BPM array confirguration

    Example
    -------

    A BPM array configuration can also be created by code using the following example::

        from pyaml.arrays.bpm import BPM,ConfigModel as BPMArrayConfigModel
        bpmArray = BPM(
                     BPMArrayConfigModel(name="MyBPMs", elements=["bpm1","bpm2"])
                   )
    """

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

    def fill_array(self, holder: ElementHolder):
        holder.fill_bpm_array(self._cfg.name, self._cfg.elements)
