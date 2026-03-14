import logging
import time
from typing import TYPE_CHECKING, Callable, Optional, Self

import numpy as np

from ..common.constants import ACTION_APPLY, ACTION_MEASURE, ACTION_RESTORE
from ..common.element import Element, ElementConfigModel
from ..common.exception import PyAMLException
from .response_matrix import ResponseMatrix
from .response_matrix_data import ConfigModel as ResponseMatrixDataConfigModel
from .response_matrix_data import ResponseMatrixData

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder

logger = logging.getLogger(__name__)

PYAMLCLASS = "TuneResponseMatrix"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for Tune response matrix

    Parameters
    ----------
    quad_array_name : str
        Array name of quad used to adjust the tune
    betatron_tune_name : str
        Name of the diagnostic pyaml device for measuring the tune
    quad_delta : float
        Delta strength used to get the response matrix
    n_step: int, optional
        Number of step for fitting the tune [-quad_delta/n_step..quad_delta/n_step]
        Default 1
    sleep_between_step: float
        Default time sleep after quad exitation
        Default: 0
    n_tune_meas : int, optional
        Default number of tune measurement per step used for averaging
        Default 1
    sleep_between_meas: float
        Default time sleep between two tune measurment
        Default: 0
    """

    quad_array_name: str
    betatron_tune_name: str
    quad_delta: float
    n_step: Optional[int] = 1
    sleep_between_step: Optional[float] = 0
    n_tune_meas: Optional[int] = 1
    sleep_between_meas: Optional[float] = 0


class TuneResponseMatrix(ResponseMatrix):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self._peer: "ElementHolder" = None  # Peer: ControlSystem, Simulator

    def measure(
        self,
        quad_delta: Optional[float] = None,
        n_step: Optional[int] = None,
        sleep_between_step: Optional[float] = None,
        n_tune_meas: Optional[int] = None,
        sleep_between_meas: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """
        Measure tune response matrix

        Parameters
        ----------
        quad_delta : float
            Delta strength used to get the response matrix
        n_step: int, optional
            Number of step for fitting the tune [-quad_delta/n_step..quad_delta/n_step]
            Default from config
        sleep_between_step: float
            Default time sleep after quad exitation
            Default: from config
        n_tune_meas : int, optional
            Default number of tune measurement per step used for averaging
            Default from config
        sleep_between_meas: float
            Default time sleep between two tune measurment
            Default: from config
        callback : Callable, optional
            tune_callback(action:int,callback_data: dict)
            Callback executed after each strength setting.
            action can be :py:data:`~pyaml.common.constant.ACTION_APPLY`,
            :py:data:`~pyaml.common.constant.ACTION_MEASURE` or :py:data:`~pyaml.common.constant.ACTION_RESTORE`.
            calback_data dict contains:
              step:int The current step
              avg_step:tin The current avg step
              m:Magnet The magnet being exited
              tune:np.array The tune (on ACTION_MEASURE)
              dtune:np.array The tune variation (on ACTION_RESTORE)
            If the callback return false, then the process is aborted.
        """
        # Get devices
        self.check_peer()
        quads = self._peer.get_magnets(self._cfg.quad_array_name)
        tm = self._peer.get_betatron_tune_monitor(self._cfg.betatron_tune_name)

        tunemat = np.zeros((len(quads), 2))
        initial_tune = tm.tune.get()
        delta = quad_delta if quad_delta is not None else self._cfg.quad_delta
        nb_step = n_step if n_step is not None else self._cfg.n_step
        nb_meas = n_tune_meas if n_tune_meas is not None else self._cfg.n_tune_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self._cfg.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self._cfg.sleep_between_meas

        aborted = False

        for qidx, m in enumerate(quads):
            str = m.strength.get()  # Initial strength
            deltas = np.linspace(-delta, delta, nb_step)
            Q = np.zeros((nb_step, 2))

            for step, d in enumerate(deltas):
                # apply strength
                m.strength.set(str + d)

                if callback and not callback(ACTION_APPLY, {"step": qidx, "magnet": m}):
                    aborted = True
                    m.strength.set(str)  # restore strength
                    break

                time.sleep(sleep_step)

                # Tune averaging
                Q[step] = np.zeros(2)
                for avg in range(nb_meas):
                    tune = tm.tune.get()
                    Q[step] += tune
                    if callback and not callback(
                        ACTION_MEASURE,
                        {"step": qidx, "avg_step": avg, "magnet": m, "tune": tune},
                    ):
                        aborted = True
                        m.strength.set(str)  # restore strength
                        break
                    time.sleep(sleep_meas)
                Q[step] /= float(nb_meas)

            if aborted:
                break

            # Fit and fill matrix with the slopes
            if nb_step == 1:
                tunemat[qidx] = (Q - initial_tune) / deltas[0]
            else:
                coefs = np.polynomial.polynomial.polyfit(deltas, Q, 1)
                tunemat[qidx] = coefs[1]

            # Restore strength
            m.strength.set(str)
            if callback and not callback(ACTION_RESTORE, {"step": qidx, "magnet": m, "dtune": tunemat[qidx]}):
                aborted = True
                break

        self.latest_measurement = ResponseMatrixDataConfigModel(
            matrix=tunemat.T.tolist(),
            variable_names=quads.names(),
            observable_names=[tm.get_name() + ".x", tm.get_name() + ".y"],
        ).model_dump()
        self.latest_measurement["type"] = "pyaml.tuning_tools.response_matrix_data"
