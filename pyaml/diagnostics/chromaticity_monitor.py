from ..common.abstract import ReadFloatArray
from ..common.constants import ACTION_APPLY, ACTION_MEASURE, ACTION_RESTORE
from ..common.element import ElementConfigModel
from ..common.exception import PyAMLException
from ..tuning_tools.measurement_tool import MeasurementTool

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
import logging
from time import sleep

import matplotlib.pyplot as plt
import numpy as np
from pydantic import ConfigDict

logger = logging.getLogger(__name__)

PYAMLCLASS = "ChomaticityMonitor"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for Chromaticity Monitor.

    Parameters
    ----------
    betatron_tune_name : str
        Name of the diagnostic pyaml device for measuring the tune
    rf_plant_name : str
        Name of main RF frequency plant
    bpm_array_name : str,optional
        Name of main BPM array used for dispersion fit
    n_step : int, optional
        Default number of RF step during chromaticity
        measurement, by default 5
    alphac : float or None, optional
        Momentum compaction factor, by default None
    e_delta : float, optional
        Default variation of relative energy during chromaticity measurement:
        f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac,
        by default 0.001
    max_e_delta : float, optional
        Maximum authorized variation of relative energy during chromaticity
        measurement, by default 0.004
    n_tune_meas : int, optional
        Default number of tune/orbit measurement per RF frequency, by default 1
    sleep_between_meas : float, optional
        Default sleep time in [s] between two tune measurements, by default 2.0
    sleep_between_step : float, optional
        Default sleep time in [s] after RF frequency variation, by default 5.0
    fit_order : int, optional
        Chomaticity fitting order, by default 1
    fit_disp_order : int, optional
        Dispersion fitting order, by default 1
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    betatron_tune_name: str
    rf_plant_name: str
    bpm_array_name: str | None = None
    n_step: int = 5
    alphac: float | None = None
    e_delta: float = 0.001
    max_e_delta: float = 0.004
    n_tune_meas: int = 1
    sleep_between_meas: float = 2.0
    sleep_between_step: float = 5.0
    fit_order: int = 1
    fit_disp_order: int = 1


class RChromaDispArray(ReadFloatArray):
    """
    Class providing read access to chromaticity or dispersion.
    Returns arrays of shape (fit_order,2) or None
    """

    def __init__(self, parent: "ChomaticityMonitor", name: str, unit: str):
        self._parent = parent
        self._name = name
        self._unit = unit

    def get(self) -> np.array:
        last = self._parent.latest_measurement
        if last is not None and self._name in last:
            return np.array(last[self._name])
        else:
            return None

    def unit(self) -> str:
        return self.unit


class ChomaticityMonitor(MeasurementTool):
    """
    Class providing access to a chromaticity monitor
    of a physical or simulated lattice. The monitor provides
    horizontal and vertical chromaticity measurements.
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a ChomaticityMonitor.

        Parameters
        ----------
        cfg : ConfigModel
            Configuration for the ChromaticityMonitor, including betatron
            tune monitor, RF plant, and defaults parameters.
        """
        super().__init__(cfg.name)
        self._cfg = cfg
        self._chromaticity = RChromaDispArray(self, "chromaticity", "1")
        self._dipsersion = RChromaDispArray(self, "dispersion", "m")

    @property
    def chromaticity(self) -> ReadFloatArray:
        """
        Get the chromaticity values.

        Returns
        -------
        ReadFloatArray
            Array of chromaticity values [[q'x, q'y],[q''x, q''y],...]
        """
        return self._chromaticity

    @property
    def dispersion(self) -> ReadFloatArray:
        """
        Get the dispersion values.

        Returns
        -------
        ReadFloatArray
            Array of dispersion values [[dx, dy],[d'x, d'y],...]
        """
        return self._dipsersion

    def measure(
        self,
        n_step: int = None,
        alphac: float = None,
        e_delta: float = None,
        max_e_delta: float = None,
        n_tune_meas: int = None,
        sleep_between_meas: float = None,
        sleep_between_step: float = None,
        fit_order: int = None,
        fit_disp_order: int = None,
        do_plot: bool = None,
        callback: callable = None,
    ):
        """
        Main function for chromaticity measurment

        Parameters
        ----------
        n_step: int
            Default number of RF step during chromaticity
            measurment [default: from config]
        alphac: float | None
            Moment compaction factor [default: from config]
        w_delta: float
            Default variation of relative energy during chromaticity measurment:
            f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac
            [default: from config]
        max_e_delta: float
            Maximum autorized variation of relative energy during chromaticity
            measurment [default: from config]
        n_tune_meas: int
            Default number of tune/orbit measurment per RF frequency [default: from config]
        sleep_between_meas: float
            Default time sleep between two tune measurment [default: from config]
        sleep_between_step: float
            Default time sleep after RF frequency variation [default: from config]
        fit_order: int
            Fitting order [default: from config]
        fit_disp_order : int, optional
            Dispersion fitting order [default: from config]
        do_plot : bool
            Do you want to plot the fittinf results ?
        callback: Callable, optional
            Callback is executed after each measurement or setting.
            If the callback return false, then the process is aborted.
        """
        n_step = n_step if n_step is not None else self._cfg.n_step
        alphac = alphac if alphac is not None else self._cfg.alphac
        e_delta = e_delta if e_delta is not None else self._cfg.e_delta
        max_e_delta = max_e_delta if max_e_delta is not None else self._cfg.max_e_delta
        n_tune_meas = n_tune_meas if n_tune_meas is not None else self._cfg.n_tune_meas
        sleep_between_meas = sleep_between_meas if sleep_between_meas is not None else self._cfg.sleep_between_meas
        sleep_between_step = sleep_between_step if sleep_between_step is not None else self._cfg.sleep_between_step
        fit_order = fit_order if fit_order is not None else self._cfg.fit_order
        fit_disp_order = fit_disp_order if fit_disp_order is not None else self._cfg.fit_disp_order

        if abs(e_delta) > abs(max_e_delta):
            logger.warning("e_delta={e_delta} is greater than max_e_delta={max_e_delta}")

        if alphac is None:
            raise PyAMLException("Moment compaction factor is not defined")

        # Get devices
        self.check_peer()
        tm = self._peer.get_betatron_tune_monitor(self._cfg.betatron_tune_name)
        rf = self._peer.get_rf_plant(self._cfg.rf_plant_name)
        bpms = None
        n_bpm = 0
        orbit = None
        if fit_disp_order is not None and self._cfg.bpm_array_name is not None:
            # For dispersion fit
            bpms = self._peer.get_bpms(self._cfg.bpm_array_name)
            n_bpm = len(bpms)

        f0 = rf.frequency.get()

        delta = np.linspace(-e_delta, e_delta, n_step)
        delta_frec = -delta * alphac * f0

        Q = np.zeros((n_step, 2))
        if bpms is not None:
            orbit = np.zeros((n_step, n_bpm, 2))

        # ensure that, even if there is an issus, the script will finish by
        # reseting the RF frequency to its original value
        err = None
        try:
            for i, f in enumerate(delta_frec):
                # TODO : Use set_and_wait once it is implemented !

                rf.frequency.set(f0 + f)

                cb_data = {"step": i, "rf": f0 + f}
                if not self.send_callback(ACTION_APPLY, callback, cb_data):
                    # Abort
                    rf.frequency.set(f0)
                    return
                sleep(sleep_between_step)

                # Averaging
                for j in range(n_tune_meas):
                    tune = tm.tune.get()
                    Q[i] += tune
                    cb_data = {"step": i, "avg_step": j, "rf": f0 + f, "tune": tune}
                    if bpms is not None:
                        orb = bpms.positions.get()
                        orbit[i] += orb
                        cb_data["orbit"] = orb
                    if not self.send_callback(ACTION_MEASURE, callback, cb_data):
                        # Abort
                        rf.frequency.set(f0)
                        return

                    if j < n_tune_meas - 1:
                        sleep(sleep_between_meas)

                Q /= float(n_tune_meas)
                if bpms is not None:
                    orbit /= float(n_tune_meas)

        except Exception as ex:
            err = ex
        finally:
            # TODO : Use set_and_wait once it is implemented !
            rf.frequency.set(f0)
            cb_data = {"step": i, "rf": f0 + f}
            self.send_callback(ACTION_RESTORE, callback, cb_data)

        if err:
            raise (err)

        self.fit(delta, Q, fit_order, orbit=orbit, fit_disp_order=fit_disp_order, do_plot=do_plot)

    def fit(self, deltas, Q, order, orbit=None, fit_disp_order=None, do_plot=False):
        """
        Compute chromaticity from measurement data.

        Parameters
        ----------
        deltas : array of float
            Relative energy (delta) variation steps done.
        Q : array of [Qx,Qy]
            Horizontal,Vertical tune measured.
        orbit: array of [[x0,y0],[x1,y1],...]
        fit_order: int
            Chromaticity fitting order
        fit_disp_order : int, optional
            Dispersion fitting order
        plot : bool, optional
            If True, plot the fit.

        Returns
        -------
        dict
            Dict with horizontal and veritical chromaticity and dispersion

        """
        chroma = np.polynomial.polynomial.polyfit(deltas, Q, order).T
        self.latest_measurement = dict()
        self.latest_measurement["chromaticity_fit"] = chroma
        self.latest_measurement["chromaticity"] = chroma[:, 1]  # First order chroma
        if orbit is not None:
            dispx = np.polynomial.polynomial.polyfit(deltas, orbit[:, :, 0], fit_disp_order).T
            self.latest_measurement["dispersionx_fit"] = dispx
            dispy = np.polynomial.polynomial.polyfit(deltas, orbit[:, :, 1], fit_disp_order).T
            self.latest_measurement["dispersiony_fit"] = dispy
            self.latest_measurement["dispersion"] = [dispx[:, 1], dispy[:, 1]]  # First order dispersion

        if do_plot:
            fig = plt.figure("Chromaticity_measurement")
            for i in range(2):
                ax = fig.add_subplot(2, 1, 1 + i)
                ax.scatter(deltas * 100, Q[:, i])
                title = ""
                for o in range(order, -1, -1):
                    dp = ""
                    if o == 1:
                        dp = "dp/p"
                    elif o >= 1:
                        dp = f"(dp/p)$^{o}$"

                    title += f"{chroma[i][o]:.4f} {dp}"
                    if o != 0:
                        title += " + "

                ax.plot(deltas * 100, np.polyval(chroma[i][::-1], deltas))
                ax.set_title(title)
                ax.set_xlabel("Momentum Shift, dp/p [%]")
                ax.set_ylabel("%s Tune" % ["Horizontal", "Vertical"][i])
            # ax.legend()
            fig.tight_layout()
            plt.show()
