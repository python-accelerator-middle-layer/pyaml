from pydantic import BaseModel, ConfigDict

from pyaml.bpm.bpm_simple_model import BPMSimpleModel

from ..common.element import __pyaml_repr__

# Define the main class name for this module
PYAMLCLASS = "BPMTiltOffsetModel"

# TODO: Implepement indexed offset and tilt


class ConfigModel(BaseModel):
    """
    Configuration model for BPM with tilt and offset

    Parameters
    ----------
    x_pos : str
        Horizontal position catalog key
    y_pos : str
        Vertical position catalog key
    x_offset : str
        Horizontal BPM offset catalog key
    y_offset : str
        Vertical BPM offset catalog key
    tilt : str
        BPM tilt catalog key
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    x_pos: str
    y_pos: str
    x_pos_index: int | None = None
    y_pos_index: int | None = None
    x_offset: str
    y_offset: str
    tilt: str


class BPMTiltOffsetModel(BPMSimpleModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
        self.__x_pos = cfg.x_pos
        self.__y_pos = cfg.y_pos
        self.__x_offset = cfg.x_offset
        self.__y_offset = cfg.y_offset
        self.__tilt = cfg.tilt

    def get_pos_devices(self) -> list[str]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_pos, self.__y_pos]

    def get_tilt_device(self) -> str | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        DeviceAccess
            DeviceAcess
        """
        return self.__tilt

    def get_offset_devices(self) -> list[str | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_offset, self.__y_offset]

    def __repr__(self):
        return __pyaml_repr__(self)
