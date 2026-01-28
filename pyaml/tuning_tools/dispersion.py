import logging
from typing import Callable, Optional, Self

from pydantic import ConfigDict
from pySC.apps import measure_dispersion
from pySC.apps.codes import DispersionCode

from ..common.constants import ACTION_APPLY, ACTION_MEASURE, ACTION_RESTORE
from ..common.element import Element, ElementConfigModel
from ..common.element_holder import ElementHolder
from ..external.pySC_interface import pySCInterface

logger = logging.getLogger(__name__)

PYAMLCLASS = "Dispersion"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for dispersion measurement

    Parameters
    ----------
    bpm_array_name : str
        BPM array name
    rf_plant_name : str
        RF plant name
    frequency_delta : float
        Frequency delta for measurement
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    rf_plant_name: str
    frequency_delta: float


class Dispersion(Element):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

        self.bpm_array_name = cfg.bpm_array_name
        self.rf_plant_name = cfg.rf_plant_name
        self.frequency_delta = cfg.frequency_delta
        self.latest_measurement = None

    def measure(
        self,
        set_waiting_time: float = 0,
        callback: Optional[Callable] = None,
    ):
        element_holder = self._peer
        interface = pySCInterface(
            element_holder=element_holder,
            bpm_array_name=self.bpm_array_name,
            rf_plant_name=self.rf_plant_name,
        )
        interface.set_wait_time = set_waiting_time

        generator = measure_dispersion(
            interface=interface,
            delta=self.frequency_delta,
            skip_save=True,
        )

        aborted = False
        for code, measurement in generator:
            callback_data = measurement.dispersion_data  # to be defined better
            if code is DispersionCode.AFTER_SET:
                if callback and not callback(ACTION_APPLY, callback_data):
                    if aborted:
                        break
            elif code is DispersionCode.AFTER_GET:
                if callback and not callback(ACTION_MEASURE, callback_data):
                    aborted = True
                    break
            elif code is DispersionCode.AFTER_RESTORE:
                if callback and not callback(ACTION_RESTORE, callback_data):
                    aborted = True
                    break

        if aborted:
            logger.warning("Measurement aborted! Settings have not been restored.")
            return

        dispersion_data = measurement.dispersion_data
        # contains also pre-processed data

        # dispersion_data.output_names = self.element_holder.get_bpms(
        #     self.bpm_array_name
        # ).names()
        self.latest_measurement = dispersion_data.model_dump()

    def get(self):
        return self.latest_measurement

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this OrbitResponseMatrix object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
