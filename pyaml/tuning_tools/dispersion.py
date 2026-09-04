import logging
from typing import Callable, Optional

from pySC.apps import measure_dispersion
from pySC.apps.codes import DispersionCode

from ..common.constants import Action
from ..external.pySC_interface import pySCInterface
from ..validation import DynamicValidation, register_schema
from .measurement_tool import MeasurementTool

logger = logging.getLogger(__name__)

PYAMLCLASS = "Dispersion"


@register_schema
class Dispersion(MeasurementTool, DynamicValidation):
    """Measure beam dispersion by changing the RF frequency.

    The measurement uses a :class:`pySCInterface` to change the frequency of
    an RF plant and acquire orbit data from a BPM array. Progress is reported
    through the callback mechanism provided by :class:`MeasurementTool`.

    Parameters
    ----------
    name : str
        Name of the dispersion measurement tool.
    bpm_array_name : str
        Name of the BPM array used to measure the orbit.
    rf_plant_name : str
        Name of the RF plant whose frequency is varied.
    frequency_delta : float
        RF-frequency change applied during the measurement.

    Attributes
    ----------
    bpm_array_name : str
        Name of the BPM array used for the measurement.
    rf_plant_name : str
        Name of the RF plant used for the measurement.
    frequency_delta : float
        RF-frequency change applied during the measurement.
    """

    def __init__(self, name: str, bpm_array_name: str, rf_plant_name: str, frequency_delta: float):
        super().__init__(name)

        self.bpm_array_name = bpm_array_name
        self.rf_plant_name = rf_plant_name
        self.frequency_delta = frequency_delta

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
        idx = 0
        err = None
        try:
            self._register_callback(callback)
            self._init_measure()
            for code, measurement in generator:
                callback_data = {"idx": idx, "dispersion_data": measurement.dispersion_data}
                if code is DispersionCode.AFTER_SET:
                    if not self.send_callback(Action.APPLY, callback_data):
                        if aborted:
                            break
                elif code is DispersionCode.AFTER_GET:
                    if not self.send_callback(Action.MEASURE, callback_data):
                        aborted = True
                        break
                elif code is DispersionCode.AFTER_RESTORE:
                    if not self.send_callback(Action.RESTORE, callback_data):
                        aborted = True
                        break
                idx += 1
        except Exception as ex:
            err = ex
        except KeyboardInterrupt as ex:
            aborted = True
        finally:
            # Restore RF
            # TODO
            self.send_callback(
                Action.RESTORE,
                {"idx": idx},
                raiseException=False,
            )

        if err is not None:
            raise (err)

        if aborted:
            logger.warning(f"{self.get_name()} : measurement aborted (settings not restored)")
            return False

        dispersion_data = measurement.dispersion_data
        # contains also pre-processed data

        # dispersion_data.output_names = self.element_holder.get_bpms(
        #     self.bpm_array_name
        # ).names()
        self.latest_measurement.update(dispersion_data.model_dump())

        return True

    def get(self):
        return self.latest_measurement
