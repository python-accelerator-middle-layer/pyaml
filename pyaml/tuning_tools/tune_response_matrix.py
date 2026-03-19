import logging
from time import sleep
from typing import Callable, Optional

import numpy as np
from pydantic import ConfigDict

from ..common.constants import Action
from .measurement_tool import MeasurementTool, MeasurementToolConfigModel
from .response_matrix_data import ConfigModel as ResponseMatrixDataConfigModel

logger = logging.getLogger(__name__)

PYAMLCLASS = "TuneResponseMatrix"


class ConfigModel(MeasurementToolConfigModel):
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
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    quad_array_name: str
    betatron_tune_name: str
    quad_delta: float


class TuneResponseMatrix(MeasurementTool):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

    def measure(
        self,
        quad_delta: Optional[float] = None,
        n_step: Optional[int] = None,
        sleep_between_step: Optional[float] = None,
        n_avg_meas: Optional[int] = None,
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
        n_avg_meas : int, optional
            Default number of tune measurement per step used for averaging
            Default from config
        sleep_between_meas: float
            Default time sleep between two tune measurment
            Default: from config
        callback : Callable, optional
            Callback executed after each strength setting.
            See :py:meth:`~.measurement_tool.MeasurementTool.send_callback`.
            If the callback return false, then the scan is aborted and strength restored.
            callback_data dict contains:

            .. code-block::

              source:str Object that triggered the source
              step:int The current step
              avg_step:int The current avg step
              magnet:Magnet The magnet being excited
              strength:float Magnet strength
              tune:np.array The measured tune (on Action.MEASURE)
              dtune:np.array The tune variation (on Action.RESTORE)

        """
        # Get devices
        self.check_peer()
        quads = self._peer.get_magnets(self._cfg.quad_array_name)
        tm = self._peer.get_betatron_tune_monitor(self._cfg.betatron_tune_name)

        tunemat = np.zeros((len(quads), 2))
        initial_tune = tm.tune.get()
        delta = quad_delta if quad_delta is not None else self._cfg.quad_delta
        nb_step = n_step if n_step is not None else self._cfg.n_step
        nb_meas = n_avg_meas if n_avg_meas is not None else self._cfg.n_avg_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self._cfg.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self._cfg.sleep_between_meas

        self.register_callback(callback)
        aborted = False
        err = None
        try:
            for qidx, m in enumerate(quads):
                str = m.strength.get()  # Initial strength
                deltas = np.linspace(-delta, delta, nb_step)
                Q = np.zeros((nb_step, 2))

                for step, d in enumerate(deltas):
                    # apply strength
                    m.strength.set(str + d)

                    self.send_callback(Action.APPLY, {"step": qidx, "magnet": m.get_name(), "strength": float(str + d)})

                    sleep(sleep_step)

                    # Tune averaging
                    Q[step] = np.zeros(2)
                    for avg in range(nb_meas):
                        tune = tm.tune.get()
                        Q[step] += tune
                        self.send_callback(
                            Action.MEASURE, {"step": qidx, "avg_step": avg, "magnet": m.get_name(), "tune": tune}
                        )
                        if avg < nb_meas - 1:
                            sleep(sleep_meas)
                    Q[step] /= float(nb_meas)

                # Fit and fill matrix with the slopes
                if nb_step == 1:
                    tunemat[qidx] = (Q - initial_tune) / deltas[0]
                else:
                    coefs = np.polynomial.polynomial.polyfit(deltas, Q, 1)
                    tunemat[qidx] = coefs[1]

                # Restore strength
                m.strength.set(str)
                self.send_callback(
                    Action.RESTORE,
                    {"step": qidx, "magnet": m.get_name(), "strength": float(str), "dtune": tunemat[qidx]},
                )

        except Exception as ex:
            err = ex
        except KeyboardInterrupt as ex:
            aborted = True
        finally:
            # Restore strength
            m.strength.set(str)
            self.send_callback(
                Action.RESTORE,
                {"step": qidx, "magnet": m.get_name(), "strength": float(str), "dtune": tunemat[qidx]},
                raiseException=False,
            )

        if err is not None:
            raise (err)

        if aborted:
            logger.warning(f"{self.get_name()} : measurement aborted")
            return False

        self.latest_measurement = ResponseMatrixDataConfigModel(
            matrix=tunemat.T.tolist(),
            variable_names=quads.names(),
            observable_names=[tm.get_name() + ".x", tm.get_name() + ".y"],
        ).model_dump()
        self.latest_measurement["type"] = "pyaml.tuning_tools.response_matrix_data"

        return True
