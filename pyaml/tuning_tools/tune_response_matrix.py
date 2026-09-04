import logging
from dataclasses import asdict
from time import sleep
from typing import Callable, Optional

import numpy as np
from pydantic import ConfigDict

from ..common.constants import Action
from ..validation import DynamicValidation, register_schema
from .measurement_tool import MeasurementTool
from .response_matrix_data import ResponseMatrixData

logger = logging.getLogger(__name__)

PYAMLCLASS = "TuneResponseMatrix"


@register_schema
class TuneResponseMatrix(MeasurementTool, DynamicValidation):
    """Measure the response of the betatron tune to quadrupole-strength changes.

    The tune response matrix describes the change in horizontal and vertical
    betatron tune produced by changes in quadrupole strength. Each quadrupole
    in the configured magnet array is varied over a range of strengths, and
    the resulting tune values are measured and averaged.

    For measurements using more than one strength step, a linear fit is used
    to determine the tune response to each quadrupole. The resulting matrix
    has one row for each tune plane and one column for each quadrupole.

    After a successful measurement, the result is stored in
    :attr:`MeasurementTool.latest_measurement` as a
    :class:`ResponseMatrixData` representation.

    Parameters
    ----------
    name : str
        Name of the measurement tool.
    quad_array_name : str
        Name of the quadrupole array used for the measurement.
    betatron_tune_name : str
        Name of the betatron tune monitor used to measure the horizontal and
        vertical tunes.
    quad_delta : float
        Maximum positive and negative quadrupole-strength change applied during
        the measurement.
    n_step : int, optional
        Number of quadrupole-strength settings used for each quadrupole. The
        settings are distributed linearly from ``-quad_delta`` to
        ``quad_delta``. The default is 1.
    sleep_between_step : float, optional
        Time in seconds to wait after changing a quadrupole strength and before
        measuring the tune. The default is 0.
    n_avg_meas : int, optional
        Number of tune measurements averaged at each strength setting. The
        default is 1.
    sleep_between_meas : float, optional
        Time in seconds to wait between tune measurements used for averaging.
        The default is 0.

    Attributes
    ----------
    quad_array_name : str
        Name of the configured quadrupole array.
    betatron_tune_name : str
        Name of the configured betatron tune monitor.
    quad_delta : float
        Configured quadrupole-strength change.
    n_step : int
        Configured number of strength settings.
    sleep_between_step : float
        Configured delay after each strength change.
    n_avg_meas : int
        Configured number of tune measurements to average.
    sleep_between_meas : float
        Configured delay between averaged tune measurements.

    Notes
    -----
    The generated response matrix has shape ``(2, n_quadrupoles)``. The first
    row contains the horizontal tune response and the second row contains the
    vertical tune response.

    Quadrupole strengths are restored after each individual scan and again when
    the measurement exits because of an error or interruption.
    """

    def __init__(
        self,
        name: str,
        quad_array_name: str,
        betatron_tune_name: str,
        quad_delta: float,
        n_step: Optional[int] = 1,
        sleep_between_step: Optional[float] = 0,
        n_avg_meas: Optional[int] = 1,
        sleep_between_meas: Optional[float] = 0,
    ):
        super().__init__(name)
        self.quad_array_name = quad_array_name
        self.betatron_tune_name = betatron_tune_name
        self.quad_delta = quad_delta
        self.n_step = n_step
        self.sleep_between_step = sleep_between_step
        self.n_avg_meas = n_avg_meas
        self.sleep_between_meas = sleep_between_meas

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
        Measure tune response matrix.
        :py:attr:`~pyaml.tuning_tools.measurement_tool.MeasurementTool.latest_measurement` contains:

        .. code-block:: python

            matrix:list[list[float] # The response matrix
            variable_names:list[str] # Variable names
            observable_names:list[str] # Observables names

        **Example**

        .. code-block:: python

            from pyaml.accelerator import Accelerator
            from pyaml.common.constants import Action

            def callback(action: Action, data:dict):
                print(f"{action}, data:{data}")
                return True

            sr = Accelerator.load("tests/config/EBSTune.yaml")
            acc = sr.design

            if acc.trm.measure(n_avg_meas=3,sleep_between_meas=5,callback=callback):
                acc.trm.save("ideal_trm.json")
                acc.trm.save("ideal_trm.yaml", with_type="yaml")
                acc.trm.save("ideal_trm.npz", with_type="npz")

        Parameters
        ----------
        quad_delta : float
            Delta strength used to get the response matrix
        n_step: int, optional
            Number of step for fitting the tune slope [-quad_delta/n_step..quad_delta/n_step]
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
            Callback executed after each strength setting or measurement.
            See :py:meth:`~.measurement_tool.MeasurementTool.send_callback`.
            If the callback return false, then the scan is aborted and strength restored.
            callback_data dict contains:

            .. code-block:: python

              source:MeasurementTool # Tool that triggered the callback
              idx:int # The index in the element array being processed
              step:int # The current step
              avg_step:int # The current avg step
              magnet:str # The magnet being excited
              strength:float # Magnet strength
              tune:np.array # The measured tune (on Action.MEASURE)
              dtune:np.array # The tune variation (on Action.RESTORE)

        """
        # Get devices
        self.check_peer()
        quads = self._peer.magnets.get(self.quad_array_name)
        tm = self._peer.get_betatron_tune_monitor(self.betatron_tune_name)

        tunemat = np.zeros((len(quads), 2))
        initial_tune = tm.tune.get()
        delta = quad_delta if quad_delta is not None else self.quad_delta
        nb_step = n_step if n_step is not None else self.n_step
        nb_meas = n_avg_meas if n_avg_meas is not None else self.n_avg_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self.sleep_between_meas

        self._register_callback(callback)
        self._init_measure("pyaml.tuning_tools.response_matrix_data")

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

                    self.send_callback(
                        Action.APPLY, {"idx": qidx, "step": step, "magnet": m.get_name(), "strength": float(str + d)}
                    )

                    sleep(sleep_step)

                    # Tune averaging
                    Q[step] = np.zeros(2)
                    for avg in range(nb_meas):
                        tune = tm.tune.get()
                        Q[step] += tune
                        self.send_callback(
                            Action.MEASURE,
                            {"idx": qidx, "step": step, "avg_step": avg, "magnet": m.get_name(), "tune": tune},
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
                    {"idx": qidx, "magnet": m.get_name(), "strength": float(str), "dtune": tunemat[qidx]},
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

        mat = ResponseMatrixData(
            matrix=tunemat.T.tolist(),
            variable_names=quads.names(),
            observable_names=[tm.get_name() + ".x", tm.get_name() + ".y"],
        )
        self.latest_measurement.update(asdict(mat))
        self.latest_measurement["type"] = "pyaml.tuning_tools.response_matrix_data"

        return True
