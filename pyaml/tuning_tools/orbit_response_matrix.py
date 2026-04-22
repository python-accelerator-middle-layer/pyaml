import logging
from pathlib import Path
from typing import Callable, List, Optional, Self

import pySC
from pydantic import ConfigDict
from pySC.apps import measure_ORM
from pySC.apps.codes import ResponseCode

from ..common.constants import Action
from ..common.element import ElementConfigModel
from ..external.pySC_interface import pySCInterface
from .measurement_tool import MeasurementTool, MeasurementToolConfigModel
from .orbit_response_matrix_data import ConfigModel as OrbitResponseMatrixDataConfigModel

logger = logging.getLogger(__name__)

PYAMLCLASS = "OrbitResponseMatrix"


class ConfigModel(MeasurementToolConfigModel):
    """
    Configuration model for orbit response matrix measurement

    Parameters
    ----------
    bpm_array_name : str
        BPM array name
    hcorr_array_name : str
        Horizontal corrector array name
    vcorr_array_name : str
        Vertical corrector array name
    corrector_delta : float
        Corrector delta for measurement
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    hcorr_array_name: str
    vcorr_array_name: str
    corrector_delta: float


class OrbitResponseMatrix(MeasurementTool):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self.corrector_delta = cfg.corrector_delta

    def measure(
        self,
        corrector_names: Optional[List[str]] = None,
        sleep_between_step: Optional[float] = None,
        n_avg_meas: Optional[int] = None,
        sleep_between_meas: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """
        Measure orbit response matrix.

        **Example**

        .. code-block:: python

            sr = Accelerator.load("MyAccelerator.yaml")
            acc = sr.design

            if acc.orm.measure():
                acc.orm.save("ideal_orm.json")
                acc.orm.save("ideal_orm.yaml", with_type="yaml")
                acc.orm.save("ideal_orm.npz", with_type="npz")

        Parameters
        ----------
        sleep_between_step: float
            Default time sleep after steerer exitation
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
            bpm_array_name=self.bpm_array_name,
        )
        # TODO handle sleep_meas
        interface.set_wait_time = sleep_step

        if corrector_names is None:
            logger.info(
                f"Measuring correctors from the default arrays: {self.hcorr_array_name} and {self.vcorr_array_name}."
            )
            hcorrector_names = element_holder.get_magnets(self.hcorr_array_name).names()
            vcorrector_names = element_holder.get_magnets(self.vcorr_array_name).names()
            corrector_names = hcorrector_names + vcorrector_names

        generator = measure_ORM(
            interface=interface,
            corrector_names=corrector_names,
            delta=self.corrector_delta,
            skip_save=True,
            shots_per_orbit=nb_meas,
        )

        pySC.disable_pySC_rich()
        aborted = False
        err = None
        idx = 0
        try:
            self._register_callback(callback)
            self._init_measure()
            for code, measurement in generator:
                callback_data = measurement.response_data  # to be defined better
                if code is ResponseCode.AFTER_SET:
                    self.send_callback(Action.APPLY, callback_data)
                elif code is ResponseCode.AFTER_GET:
                    self.send_callback(Action.MEASURE, callback_data)
                elif code is ResponseCode.AFTER_RESTORE:
                    logger.info(f"Measured response of {measurement.last_input}.")
                    self.send_callback(Action.RESTORE, callback_data)
                idx += 1
        except Exception as ex:
            err = ex
        except KeyboardInterrupt as ex:
            aborted = True
        finally:
            # Restore steerer strength
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

        orm_data = self._pySC_response_data_to_ORMData(measurement.response_data.model_dump())
        self.latest_measurement.update(orm_data.model_dump())
        self.latest_measurement["type"] = "pyaml.tuning_tools.orbit_response_matrix_data"

    def _pySC_response_data_to_ORMData(self, data: dict) -> OrbitResponseMatrixDataConfigModel:
        # all metadata is discarded here. Should we keep something?

        element_holder = self._peer
        all_hcorrector_names = element_holder.get_magnets(self.hcorr_array_name).names()
        all_vcorrector_names = element_holder.get_magnets(self.vcorr_array_name).names()
        variable_planes = []
        for corr in data["input_names"]:
            if corr in all_hcorrector_names:
                variable_planes.append("H")
            elif corr in all_vcorrector_names:
                variable_planes.append("V")

        bpm_names = element_holder.get_bpms(self.bpm_array_name).names()
        # This is because we assume always dual-plane bpms now.
        len_b = len(bpm_names)
        observable_names = bpm_names * 2
        observable_planes = ["H"] * len_b + ["V"] * len_b

        orm_data_model = {
            "matrix": data["matrix"],
            "variable_names": data["input_names"],
            "observable_names": observable_names,
            "rf_response": None,
            "variable_planes": variable_planes,
            "observable_planes": observable_planes,
        }

        orm_data = OrbitResponseMatrixDataConfigModel(**orm_data_model)
        return orm_data
