from collections.abc import Callable

from ..common.abstract import ReadFloatArray
from ..common.constants import ACTION_APPLY, ACTION_MEASURE, ACTION_RESTORE
from ..common.element import Element, ElementConfigModel
from ..common.exception import PyAMLException

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
from time import sleep

import matplotlib.pyplot as plt
import numpy as np
from pydantic import ConfigDict

PYAMLCLASS = "ChomaticityMonitor"


class ConfigModel(ElementConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    """
    Chomaticity measurement

    Parameters
    ----------
    betatron_tune: str
        Name of the diagnostic pyaml device for measuring the tune
    RFfreq: str
        Name of main RF frequency plant
    N_step: int = 5
        Default number of RF step during chromaticity
        measurment [default: 5]
    alphac: float | None = None
        Moment compaction factor
    E_delta: float
        Default variation of relative energy during chromaticity measurment:
        f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac
        [default: 0.001]
    Max_E_delta: float
        Maximum autorized variation of relative energy during chromaticity
        measurment [default: 0.004]
    N_tune_meas: int
        Default number of tune measurment per RF frequency [default: 1]
    Sleep_between_meas: float
        Default time sleep between two tune measurment [default: 2.0]
    Sleep_between_RFvar: float
        Default time sleep after RF frequency variation [default: 5.0]
    fit_order: int
        Fitting order [default: 1]
    """

    betatron_tune: str
    RFfreq: str
    N_step: int = 5
    alphac: float | None = None
    E_delta: float = 0.001
    Max_E_delta: float = 0.004
    N_tune_meas: int = 1
    Sleep_between_meas: float = 2.0
    Sleep_between_RFvar: float = 5.0
    fit_order: int = 1


class ChomaticityMonitor(Element):
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
        self.__chromaticity = None
        self._last_measured = np.array([np.nan, np.nan])
        self._peer = None

    @property
    def chromaticity(self) -> ReadFloatArray:
        self.check_peer()
        return self.__chromaticity

    def attach(self, peer, chromaticity: ReadFloatArray) -> Self:
        obj = self.__class__(self._cfg)
        chromaticity._update_chromaticity_monitor(obj)
        obj.__chromaticity = chromaticity
        obj._peer = peer
        return obj

    def measure(
        self,
        N_step: int = None,
        alphac: float = None,
        E_delta: float = None,
        Max_E_delta: float = None,
        N_tune_meas: int = None,
        Sleep_between_meas: float = None,
        Sleep_between_RFvar: float = None,
        fit_order: int = None,
        do_plot: bool = None,
        callback: callable = None,
    ):
        """
        Main function for chromaticity measurment

        Parameters
        ----------
        N_step: int
            Default number of RF step during chromaticity
            measurment [default: from config]
        alphac: float | None
            Moment compaction factor [default: from config]
        E_delta: float
            Default variation of relative energy during chromaticity measurment:
            f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac
            [default: from config]
        Max_E_delta: float
            Maximum autorized variation of relative energy during chromaticity
            measurment [default: from config]
        N_tune_meas: int
            Default number of tune measurment per RF frequency [default: from config]
        Sleep_between_meas: float
            Default time sleep between two tune measurment [default: from config]
        Sleep_between_RFvar: float
            Default time sleep after RF frequency variation [default: from config]
        fit_order: int
            Fitting order [default: 1]
        do_plot : bool
            Do you want to plot the fittinf results ?
        callback: Callable, optional
            User chroma_callback(step:int,action:int,rf:float,tune:np.array)
            Callback is executed after each measurement or setting.
            If the callback return false, then the process is aborted.
        """
        if N_step is None:
            N_step = self._cfg.N_step
        if alphac is None:
            alphac = self._cfg.alphac
        if E_delta is None:
            E_delta = self._cfg.E_delta
        if Max_E_delta is None:
            Max_E_delta = self._cfg.Max_E_delta
        if N_tune_meas is None:
            N_tune_meas = self._cfg.N_tune_meas
        if Sleep_between_meas is None:
            Sleep_between_meas = self._cfg.Sleep_between_meas
        if Sleep_between_RFvar is None:
            Sleep_between_RFvar = self._cfg.Sleep_between_RFvar
        if fit_order is None:
            fit_order = self._cfg.fit_order
        if abs(E_delta) > abs(Max_E_delta):
            # TODO : Add logger to warm that E_delta is to large
            return np.array([None, None])

        if alphac is None:
            raise PyAMLException("Moment compaction factor is not defined")

        delta, NuX, NuY = self.measure_tune_response(
            N_step=N_step,
            alphac=alphac,
            E_delta=E_delta,
            N_tune_meas=N_tune_meas,
            Sleep_between_meas=Sleep_between_meas,
            Sleep_between_RFvar=Sleep_between_RFvar,
            callback=callback,
        )

        if delta is None:
            return [np.nan, np.nan]

        chrom = self.fit(
            delta=delta, NuX=NuX, NuY=NuY, order=fit_order, do_plot=do_plot
        )
        return chrom

    def measure_tune_response(
        self,
        N_step: int,
        alphac: float,
        E_delta: float,
        N_tune_meas: int,
        Sleep_between_meas: float,
        Sleep_between_RFvar: float,
        callback: Callable,
    ):
        """
        Main function for chromaticity measurment

        N_step: int
            Default number of RF step during chromaticity
            measurment [default: from config]
        alphac: float | None
            Moment compaction factor [default: from config]
        E_delta: float
            Default variation of relative energy during chromaticity measurment:
            f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac
            [default: from config]
        N_tune_meas: int
            Default number of tune measurment per RF frequency [default: from config]
        Sleep_between_meas: float
            Default time sleep between two tune measurment [default: from config]
        Sleep_between_RFvar: float
            Default time sleep after RF frequency variation [default: from config]
        callback: Callable, optional
            User chroma_callback(step:int,action:int,rf:float,tune:np.array)
            Callback is executed after each measurement or setting.
            If the callback return false, then the process is aborted.
        """
        tune = self._peer.get_betatron_tune_monitor(self._cfg.betatron_tune)
        rf = self._peer.get_rf_plant(self._cfg.RFfreq)

        f0 = rf.frequency.get()

        delta = np.linspace(-E_delta, E_delta, N_step)
        delta_frec = delta * alphac * f0

        NuY = np.zeros((N_step, N_tune_meas))
        NuX = np.zeros((N_step, N_tune_meas))

        # ensure that, even if there is an issus, the script will finish by
        # reseting the RF frequency to its original value
        err = None
        try:
            for i, f in enumerate(delta_frec):
                # TODO : Use set_and_wait once it is implemented !
                # (and remove Sleep_between_RFvar ?)
                rf.frequency.set(f0 + f)
                if callback and not callback(i, ACTION_APPLY, f0 + f, [np.nan, np.nan]):
                    # Abort
                    rf.frequency.set(f0)
                    return (None, None, None)
                sleep(Sleep_between_RFvar)

                for j in range(N_tune_meas):
                    NuX[i, j], NuY[i, j] = tune.tune.get()
                    if callback and not callback(
                        i, ACTION_MEASURE, f0 + f, [NuX[i, j], NuY[i, j]]
                    ):
                        # Abort
                        rf.frequency.set(f0)
                        return (None, None, None)
                    sleep(Sleep_between_meas)

        except Exception as ex:
            err = ex
        finally:
            # TODO : Use set_and_wait once it is implemented !
            rf.frequency.set(f0)
            if callback:
                callback(i, ACTION_RESTORE, f0 + f, [np.nan, np.nan])

        if err:
            raise (err)

        return (delta, NuX, NuY)

    def fit(self, delta, NuX, NuY, order, do_plot):
        """
        Compute chromaticity from measurement data.

        Parameters
        ----------
        delta : array of float
            Relative energy (delta) variation steps done.
        NuX : array of float
            Horizontal tune measured.
        NuZ : array of float
            Vertical tune measured.
        order : int
            order of polynomial used for fit
        plot : bool, optional
            If True, plot the fit.
            Plots are made but not shown. Use plt.show() to show it.

        Returns
        -------
        chro : array
            Array with horizontal and veritical chromaticity.

        """
        if len(NuX) == 0:
            raise PyAMLException(
                "No measurement data available for fit, pleas call measure() first"
            )

        delta = -delta
        chro = []
        N_step_delta = len(delta)
        for i, Nu in enumerate([NuX, NuY]):
            # if N_step_delta%2 == 0:
            #     tune0 = np.mean((Nu[N_step_delta//2-1,:] + Nu[N_step_delta//2,:])/2.)
            # else:
            #     tune0 = np.mean(Nu[N_step_delta//2,:])

            dtune = np.mean(Nu[:, :], 1)
            coefs = np.polynomial.polynomial.polyfit(delta, dtune, order)
            chro.append(coefs[1])

            if do_plot:
                fig = plt.figure("Chromaticity_measurement")
                ax = fig.add_subplot(2, 1, 1 + i)
                ax.scatter(delta, dtune)
                title = ""
                for o in range(order, -1, -1):
                    dp = ""
                    if o == 1:
                        dp = "dp/p"
                    elif o >= 1:
                        dp = f"(dp/p)$^{o}$"

                    title += f"{coefs[o]:.4f} {dp}"
                    if o != 0:
                        title += " + "

                ax.plot(delta, np.polyval(coefs[::-1], delta))
                ax.set_title(title)
                ax.set_xlabel("Momentum Shift, dp/p [%]")
                ax.set_ylabel("%s Tune" % ["Horizontal", "Vertical"][i])
                # ax.legend()

        if do_plot:
            fig.tight_layout()
            plt.show()

        self._last_measured = np.array(chro)

        return self._last_measured
