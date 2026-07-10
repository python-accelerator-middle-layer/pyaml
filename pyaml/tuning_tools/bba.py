import logging
from typing import Callable, Optional

import numpy as np
import pySC
from pydantic import ConfigDict
from pySC.apps import measure_bba
from pySC.apps.bba import BBAAnalysis
from pySC.apps.codes import BBACode

from ..common.constants import Action
from ..external.pySC_interface import pySCInterface
from .measurement_tool import MeasurementTool, MeasurementToolConfigModel

logger = logging.getLogger(__name__)

PYAMLCLASS = "BBA"


class ConfigModel(MeasurementToolConfigModel):
    """
    Configuration model for Beam Based Alignment.
    BBA finds the magnetic center of a quad (zero crossing).

    Parameters
    ----------
    bpm_array_name : str
        BPM array name (orbit)
    bpm_name : str
        BPM to be corrected (close to the quad)
    hcorr_name : str
        Horizontal corrector used to make a deviation in the quad
    vcorr_name : str
        Vertical corrector used to make a deviation in the quad
    quad_name : str
        Quadrupole used to find the center
    hcorr_delta : float
        Horizontal corrector delta strength
    vcorr_delta : float
        Vertical corrector delta strength
    hquad_delta : float
        Quadrupole delta strength (for h search)
    vquad_delta : float
        Quadrupole delta strength (for v search)

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    bpm_name: str
    hcorr_name: str
    vcorr_name: str
    quad_name: str
    hcorr_delta: float
    vcorr_delta: float
    hquad_delta: float
    vquad_delta: float


class BBA(MeasurementTool):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

    def measure(
        self,
        sleep_between_step: Optional[float] = None,
        n_avg_meas: Optional[int] = None,
        sleep_between_meas: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """
        Measure BBA.

        **Example**

        .. code-block:: python

            sr = Accelerator.load("MyAccelerator.yaml")
            TODO

        Parameters
        ----------
        sleep_between_step: float
            Default time sleep after steerer or quad exitation
            Default: from config
        n_avg_meas : int, optional
            Default number of orbit measurement per step used for averaging
            Default from config
        sleep_between_meas: float
            Default time sleep between two orbit measurment
            Default: from config
        callback : Callable, optional
            example: callback(action:int, callback_data: 'Complicated struct')
            callback is executed after each strength setting and after each orbit
            reading.
            If the callback returns false, then the process is aborted.
        """
        nb_meas = n_avg_meas if n_avg_meas is not None else self._cfg.n_avg_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self._cfg.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self._cfg.sleep_between_meas

        element_holder = self._peer
        interface = pySCInterface(
            element_holder=element_holder,
            bpm_array_name=self._cfg.bpm_array_name,
        )
        interface.set_wait_time = sleep_step
        interface.read_wait_time = sleep_meas

        bpms_names = element_holder.get_bpms(self._cfg.bpm_array_name).names()

        bba_pySC_config = {
            "number": bpms_names.index(self._cfg.bpm_name),
            "QUAD": self._cfg.quad_name,
            "HCORR": self._cfg.hcorr_name,
            "VCORR": self._cfg.vcorr_name,
            "HCORR_delta": self._cfg.hcorr_delta,
            "QUAD_dk_H": self._cfg.hquad_delta,
            "VCORR_delta": self._cfg.vcorr_delta,
            "QUAD_dk_V": self._cfg.vquad_delta,
            "QUAD_is_skew": False,
        }

        generator = measure_bba(
            interface=interface,
            bpm_name=self._cfg.bpm_name,
            config=bba_pySC_config,
            shots_per_orbit=nb_meas,
            n_corr_steps=self._cfg.n_step,
            bipolar=False,
            skip_save=True,
        )

        pySC.disable_pySC_rich()
        aborted = False
        err = None
        idx = 0
        self._latest_measurement = {"HOffset": np.nan, "VOffset": np.nan, "HOffsetError": np.nan, "VOffsetError": np.nan}

        try:
            self._register_callback(callback)
            self._init_measure()
            for code, measurement_object in generator:
                # print(f"Got code: {code.name}")
                if code == BBACode.HORIZONTAL_DONE:
                    result = BBAAnalysis.analyze(measurement_object.H_data)
                    self.latest_measurement["HOffset"] = result.offset
                    self.latest_measurement["HOffsetError"] = result.offset_error
                if code == BBACode.VERTICAL_DONE:
                    result = BBAAnalysis.analyze(measurement_object.V_data)
                    self.latest_measurement["VOffset"] = result.offset
                    self.latest_measurement["VOffsetError"] = result.offset_error
                idx += 1
        except Exception as ex:
            err = ex
        except KeyboardInterrupt as ex:
            aborted = True
        finally:
            # Restore steerer/quad strength
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

        return True

    def h_offset(self) -> float:
        return self.latest_measurement["HOffset"]

    def h_offset_error(self) -> float:
        return self.latest_measurement["HOffsetError"]

    def v_offset(self) -> float:
        return self.latest_measurement["VOffset"]

    def v_offset_error(self) -> float:
        return self.latest_measurement["VOffsetError"]
