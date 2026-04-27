import logging
import time
from typing import Callable, Optional

import numpy as np
from pydantic import ConfigDict

from ..common.constants import Action
from ..common.element import ElementConfigModel
from .measurement_tool import MeasurementTool, MeasurementToolConfigModel
from .response_matrix_data import ConfigModel as ResponseMatrixDataConfigModel

logger = logging.getLogger(__name__)

PYAMLCLASS = "ChromaticityResponseMatrix"


class ConfigModel(MeasurementToolConfigModel):
    """
    Configuration model for Tune response matrix

    Parameters
    ----------
    sextu_array_name : str
        Array name of sextupole used to adjust the chromaticity
    chromaticity_name : str
        Name of the diagnostic chromaticy monitor
    sextu_delta : float
        Delta strength used to get the response matrix
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    sextu_array_name: str
    chromaticity_name: str
    sextu_delta: float


class ChromaticityResponseMatrix(MeasurementTool):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.aborted = False

    def measure(
        self,
        sextu_delta: Optional[float] = None,
        n_step: Optional[int] = None,
        sleep_between_step: Optional[float] = None,
        n_avg_meas: Optional[int] = None,
        sleep_between_meas: Optional[float] = None,
        callback: Optional[Callable] = None,
    ):
        """
        Measure chromaticity response matrix.
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

            sr = Accelerator.load("tests/config/EBSOrbit.yaml")
            acc = sr.design

            if acc.crm.measure(callback=callback):
                acc.crm.save("ideal_crm.json")
                acc.crm.save("ideal_crm.yaml", with_type="yaml")
                acc.crm.save("ideal_crm.npz", with_type="npz")


        Parameters
        ----------
        sextu_delta : float
            Delta strength used to get the response matrix
        n_step: int, optional
            Number of step for fitting the chomaticity slope [-sextu_delta/n_step..sextu_delta/n_step]
            Default from config
        sleep_between_step: float
            Default time sleep after sextu exitation
            Default: from config
        n_avg_meas : int, optional
            Default number of chromaticity measurement per step used for averaging
            Default from config
        sleep_between_meas: float
            Default time sleep between two chomaticity measurment
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
              avg_step:int # The current averaging step
              magnet:str # The magnet being excited
              strength:float # Magnet strength
              chroma:np.array # The measured chroma (on Action.MEASURE)
              dchroma:np.array # The chroma variation (on Action.RESTORE)

        """
        # Get devices
        self.check_peer()
        sextus = self._peer.get_magnets(self._cfg.sextu_array_name)
        cm = self._peer.get_chromaticity_monitor(self._cfg.chromaticity_name)

        self._register_callback(callback)
        self._init_measure("pyaml.tuning_tools.response_matrix_data")

        chromamat = np.zeros((len(sextus), 2))

        initial_chroma = None
        if not cm.measure(callback=callback):
            # Aborted
            return False
        initial_chroma = cm.chromaticity.get()

        delta = sextu_delta if sextu_delta is not None else self._cfg.sextu_delta
        nb_step = n_step if n_step is not None else self._cfg.n_step
        nb_meas = n_avg_meas if n_avg_meas is not None else self._cfg.n_avg_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self._cfg.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self._cfg.sleep_between_meas

        err = None
        aborted = False
        try:
            for qidx, m in enumerate(sextus):
                str = m.strength.get()  # Initial strength
                deltas = np.linspace(-delta, delta, nb_step)
                Qp = np.zeros((nb_step, 2))

                for step, d in enumerate(deltas):
                    # apply strength
                    m.strength.set(str + d)

                    self.send_callback(
                        Action.APPLY, {"idx": qidx, "step": step, "magnet": m.get_name(), "strength": float(str + d)}
                    )

                    time.sleep(sleep_step)

                    # Chroma averaging
                    Qp[step] = np.zeros(2)
                    for avg in range(nb_meas):
                        if not cm.measure(callback=callback):
                            raise KeyboardInterrupt
                        chroma = cm.chromaticity.get()
                        Qp[step] += chroma

                        self.send_callback(
                            Action.MEASURE,
                            {"idx": qidx, "step": step, "avg_step": avg, "magnet": m.get_name(), "chroma": chroma},
                        )

                        if avg < nb_meas - 1:
                            time.sleep(sleep_meas)
                    Qp[step] /= float(nb_meas)

                # Fit and fill matrix with the slopes
                if nb_step == 1:
                    chromamat[qidx] = (Qp - initial_chroma) / deltas[0]
                else:
                    coefs = np.polynomial.polynomial.polyfit(deltas, Qp, 1)
                    chromamat[qidx] = coefs[1]

                # Restore strength
                m.strength.set(str)
                self.send_callback(
                    Action.RESTORE,
                    {"idx": qidx, "magnet": m.get_name(), "strength": float(str), "dchroma": chromamat[qidx]},
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
                {"step": qidx, "magnet": m.get_name(), "strength": float(str), "dchroma": chromamat[qidx]},
                raiseException=False,
            )

        if err is not None:
            raise (err)

        if aborted:
            logger.warning(f"{self.get_name()} : measurement aborted")
            return False

        mat = ResponseMatrixDataConfigModel(
            matrix=chromamat.T.tolist(),
            variable_names=sextus.names(),
            observable_names=[cm.get_name() + ".x", cm.get_name() + ".y"],
        )
        self.latest_measurement.update(mat.model_dump())
        self.latest_measurement["type"] = "pyaml.tuning_tools.response_matrix_data"

        return True
