"""
Orbit response-matrix measurement tools.

This module measures BPM orbit changes caused by horizontal and vertical
corrector perturbations and stores the fitted response in a structured data
model.
"""

import logging
from dataclasses import asdict
from typing import Callable, List, Optional

import pySC
from pySC.apps import measure_ORM
from pySC.apps.codes import ResponseCode

from ..common.constants import Action
from ..external.pySC_interface import pySCInterface
from ..validation import DynamicValidation, register_schema
from .measurement_tool import MeasurementTool
from .orbit_response_matrix_data import OrbitResponseMatrixData

logger = logging.getLogger(__name__)

PYAMLCLASS = "OrbitResponseMatrix"


@register_schema
class OrbitResponseMatrix(MeasurementTool, DynamicValidation):
    """
    Measure an orbit response matrix using BPMs and orbit correctors.

    The orbit response matrix describes the change in measured beam position
    produced by a change in corrector strength. This measurement tool uses
    horizontal and vertical corrector arrays together with a BPM array to
    perform the measurement through the pySC interface.

    After a successful measurement, the result is converted to
    :class:`OrbitResponseMatrixData` and stored in ``latest_measurement``.
    The stored data includes the response matrix, corrector and BPM names,
    and the plane associated with each variable and observable.

    Parameters
    ----------
    name : str
        Name of the measurement tool.
    bpm_array_name : str
        Name of the BPM array used to measure the orbit.
    hcorr_array_name : str
        Name of the horizontal corrector array.
    vcorr_array_name : str
        Name of the vertical corrector array.
    corrector_delta : float
        Change in corrector strength applied during the measurement.
    n_step : int, optional
        Number of strength steps used for each corrector. The default is 1.
    sleep_between_step : float, optional
        Time in seconds to wait after changing a corrector strength. The
        default is 0.
    n_avg_meas : int, optional
        Number of orbit measurements averaged at each corrector setting. The
        default is 1.
    sleep_between_meas : float, optional
        Time in seconds to wait between orbit measurements used for averaging.
        The default is 0.

    Attributes
    ----------
    bpm_array_name : str
        Name of the configured BPM array.
    hcorr_array_name : str
        Name of the configured horizontal corrector array.
    vcorr_array_name : str
        Name of the configured vertical corrector array.
    corrector_delta : float
        Corrector-strength change used for the measurement.
    n_step : int
        Configured number of corrector-strength steps.
    sleep_between_step : float
        Configured delay between corrector-strength changes.
    n_avg_meas : int
        Configured number of orbit measurements to average.
    sleep_between_meas : float
        Configured delay between averaged orbit measurements.
    """

    def __init__(
        self,
        name: str,
        bpm_array_name: str,
        hcorr_array_name: str,
        vcorr_array_name: str,
        corrector_delta: float,
        n_step: Optional[int] = 1,
        sleep_between_step: Optional[float] = 0,
        n_avg_meas: Optional[int] = 1,
        sleep_between_meas: Optional[float] = 0,
    ):
        """
        Initialize an orbit response-matrix measurement tool.

        Parameters
        ----------
        name : str
            Name of the measurement tool.
        bpm_array_name : str
            Name of the BPM array used for orbit readback.
        hcorr_array_name : str
            Name of the horizontal corrector array.
        vcorr_array_name : str
            Name of the vertical corrector array.
        corrector_delta : float
            Corrector-strength perturbation used for the scan.
        n_step : Optional[int]
            Number of strength steps used to fit each response slope.
        sleep_between_step : Optional[float]
            Delay in seconds after changing a corrector.
        n_avg_meas : Optional[int]
            Number of orbit measurements averaged at each step.
        sleep_between_meas : Optional[float]
            Delay in seconds between averaged orbit measurements.
        """
        super().__init__(name)

        self.bpm_array_name = bpm_array_name
        self.hcorr_array_name = hcorr_array_name
        self.vcorr_array_name = vcorr_array_name
        self.corrector_delta = corrector_delta
        self.n_step = n_step
        self.sleep_between_step = sleep_between_step
        self.n_avg_meas = n_avg_meas
        self.sleep_between_meas = sleep_between_meas

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
        sleep_between_step : float
            Default time sleep after steerer exitation
            Default: from config
        n_avg_meas : int, optional
            Default number of orbit measurement per step used for averaging
            Default from config
        sleep_between_meas : float
            Default time sleep between two orbit measurment
            Default: from config
        callback : Callable, optional
            example: callback(action:int, callback_data: 'Complicated struct')
            callback is executed after each strength setting and after each orbit
            reading.
            If the callback returns false, then the process is aborted.
        """
        nb_meas = n_avg_meas if n_avg_meas is not None else self.n_avg_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self.sleep_between_meas

        element_holder = self._peer
        interface = pySCInterface(
            element_holder=element_holder,
            bpm_array_name=self.bpm_array_name,
        )
        # TODO handle sleep_meas
        interface.set_wait_time = sleep_step

        if corrector_names is None:
            logger.info(f"Measuring correctors from the default arrays: {self.hcorr_array_name} and {self.vcorr_array_name}.")
            hcorrector_names = element_holder.magnets.get(self.hcorr_array_name).names()
            vcorrector_names = element_holder.magnets.get(self.vcorr_array_name).names()
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
            self._init_measure("pyaml.tuning_tools.orbit_response_matrix_data")
            for code, measurement in generator:
                callback_data = {"idx": idx, "response_data": measurement.response_data}
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
        self.latest_measurement.update(asdict(orm_data))

        return True

    def _pySC_response_data_to_ORMData(self, data: dict) -> OrbitResponseMatrixData:
        # all metadata is discarded here. Should we keep something?

        """
        Convert pySC response data to an orbit response-matrix model.

        pySC uses ``input_names`` and ``output_names`` fields, whereas PyAML
        stores actuator and observable names separately. This method performs
        that conversion, infers the horizontal or vertical plane for each
        actuator, and represents every BPM as one horizontal and one vertical
        observable.

        Parameters
        ----------
        data : dict
            pySC response data containing ``matrix`` and ``input_names``.

        Returns
        -------
        OrbitResponseMatrixData
            PyAML response-matrix data with actuator names, BPM names, and
            their associated planes.
        """
        element_holder = self._peer
        all_hcorrector_names = element_holder.magnets.get(self.hcorr_array_name).names()
        all_vcorrector_names = element_holder.magnets.get(self.vcorr_array_name).names()
        variable_planes = []
        for corr in data["input_names"]:
            if corr in all_hcorrector_names:
                variable_planes.append("H")
            elif corr in all_vcorrector_names:
                variable_planes.append("V")

        bpm_names = element_holder.bpms.get(self.bpm_array_name).names()
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

        orm_data = OrbitResponseMatrixData(**orm_data_model)
        return orm_data
