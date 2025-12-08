from ..common.abstract import ReadFloatArray
from ..common.element import Element, ElementConfigModel
from ..control.deviceaccess import DeviceAccess

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
from pydantic import ConfigDict

from time import sleep
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

PYAMLCLASS = "ChomaticityMonitor"


class ConfigModel(ElementConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    betatron_tune: str
    """Name of the diagnostic pyaml device for measuring the tune"""
    RFfreq: str
    """Name of main RF frequency plant"""
    N_step: int = 5
    """Default number of RF step during chromaticity measurment [default: 5]"""
    alphac: float = 4.1819e-04
    """Default Twiss parameter alpha ???"""
    E_delta: float = 0.001
    """Default variation of relative energy during chromaticity measurment : f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac [default: 0.001]"""
    Max_E_delta: float = 0.004
    """Maximum autorized variation of relative energy during chromaticity measurment [default: 0.004]"""
    N_tune_meas: int = 1
    """Default number of tune measurment per RF frequency [default: 1]"""
    Sleep_between_meas: float = 2.0
    """Default time sleep between two tune measurment [default: 2.0]"""
    Sleep_between_RFvar: float = 5.0
    """Default time sleep after RF frequency variation [default: 5.0]"""
    fit_method: str = "lin"
    """Default fitting method used for chromaticity between "lin" for linear or "quad" for quadratique [default: "lin"]"""


class ChomaticityMonitor(Element):
    """
    Class providing access to a betatron tune monitor
    of a physical or simulated lattice.
    The monitor provides horizontal and vertical betatron tune measurements.
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a BetatronTuneMonitor.
        Parameters
        ----------
        cfg : ConfigModel
            Configuration for the ChromaticityMonitor, including betatron tune monitor, RF plant, and defaults parameters.
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

    def chromaticity_measurement(self, 
                                 N_step: int=None, 
                                 alphac: float=None, 
                                 E_delta: float=None, 
                                 Max_E_delta: float=None, 
                                 N_tune_meas: int=None, 
                                 Sleep_between_meas: float=None, 
                                 Sleep_between_RFvar: float=None,
                                 fit_method: str=None,
                                 do_plot: bool=False):
        """
        Main function for chromaticity measurment

        N_step : int 
            Number of RF step during chromaticity measurment. 
            If defined, eraised defalt and configation files values.
        alphac : float
            Default Twiss parameter alpha ??? 
            If defined, eraised defalt and configation files values.
        E_delta : float
            Default variation of relative energy during chromaticity measurment : f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac
            If defined, eraised defalt and configation files values.
        Max_E_delta : float
            Maximum autorized variation of relative energy during chromaticity measurment
            If defined, eraised defalt and configation files values.
        N_tune_meas : int
            Default number of tune measurment per RF frequency.
            If defined, eraised defalt and configation files values.
        Sleep_between_meas : float
            Default time sleep between two tune measurment.
            If defined, eraised defalt and configation files values.
        Sleep_between_RFvar: float
            Default time sleep after RF frequency variation.
            If defined, eraised defalt and configation files values.
        fit_method: str
            Default fitting method used for chromaticity between "lin" for linear or "quad" for quadratique.
            If defined, eraised defalt and configation files values.
        do_plot : bool
            Do you want to plot the fittinf results ?
        """
        if N_step is None :
            N_step = self._cfg.N_step
        if alphac is None :
            alphac = self._cfg.alphac
        if E_delta is None :
            E_delta = self._cfg.E_delta
        if Max_E_delta is None :
            Max_E_delta = self._cfg.Max_E_delta
        if N_tune_meas is None :
            N_tune_meas = self._cfg.N_tune_meas
        if Sleep_between_meas is None :
            Sleep_between_meas = self._cfg.Sleep_between_meas
        if Sleep_between_RFvar is None :
            Sleep_between_RFvar = self._cfg.Sleep_between_RFvar
        if fit_method is None :
            fit_method = self._cfg.fit_method

        if abs(E_delta) > abs(Max_E_delta):
            # TODO : Add logger to warm that E_delta is to large
            return np.array([None, None])

        Delta, NuX, NuY = self.measure_tune_response(N_step=N_step, alphac=alphac, E_delta=E_delta, N_tune_meas=N_tune_meas, Sleep_between_meas=Sleep_between_meas, Sleep_between_RFvar=Sleep_between_RFvar)
        chrom = self.fit_chromaticity(Delta, NuX, NuY, fit_method, do_plot)
        return(chrom)

    def measure_tune_response(self, 
                                N_step: int, 
                                alphac: float, 
                                E_delta: float, 
                                N_tune_meas: int, 
                                Sleep_between_meas: float, 
                                Sleep_between_RFvar: float):
        """
        Main function for chromaticity measurment

        N_step : int 
            Number of RF step during chromaticity measurment. 
        alphac : float
            Default Twiss parameter alpha ??? 
        E_delta : float
            Default variation of relative energy during chromaticity measurment : f0 - f0 * E_delta * alphac  < f_RF < f0 + f0 * E_delta * alphac
        N_tune_meas : int
            Default number of tune measurment per RF frequency.
        Sleep_between_meas : float
            Default time sleep between two tune measurment.
        Sleep_between_RFvar: float
            Default time sleep after RF frequency variation.

        """
        tune = self._peer.get_betatron_tune_monitor(self._cfg.betatron_tune)
        rf = self._peer.get_rf_plant(self._cfg.RFfreq)
        
        f0 = rf.frequency.get()
        delta_f = f0 * E_delta * alphac
        Delta = np.linspace(f0 - delta_f, f0 + delta_f, N_step)

        NuY = np.zeros((N_step, N_tune_meas))
        NuX = np.zeros((N_step, N_tune_meas))

        try: # ensure that, even if there is an issus, the script will finish by reseting the RF frequency
            for i, f in enumerate(Delta):
                rf.frequency.set_and_wait(f)
                sleep(Sleep_between_RFvar)

                for j in range(N_tune_meas):
                    NuX[i,j], NuY[i,j] = tune.tune.get()
                    sleep(Sleep_between_meas)
        except:
            # TODO : add proper exception
            print("NOK")
        finally:
            rf.frequency.set_and_wait(f0)
        return(Delta, NuX, NuY)    


    def fit_chromaticity(self, Delta, NuX, NuY, method, do_plot):
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
        method : {"lin" or "quad"}, optional
            "lin" uses a linear fit and "quad" a 2nd order polynomial.
            The default is "lin".
        plot : bool, optional
            If True, plot the fit.
            The default is False.

        Returns
        -------
        chro : array
            Array with horizontal and veritical chromaticity.

        """
        Delta = -Delta
        chro = []
        N_step_delta = len(Delta)
        for i, Nu in enumerate([NuX, NuY]):
            if N_step_delta%2 == 0:
                tune0 = np.mean(Nu[N_step_delta//2:N_step_delta//2+1,:])
            else:
                tune0 = np.mean(Nu[N_step_delta//2,:])

            dtune = np.mean(Nu[:,:],1) - tune0

            if method=="lin":
                def linear_fit(x, a, b):
                    return a*x + b
                popt_lin, _ = curve_fit(linear_fit, Delta, dtune)
                chro.append(popt_lin[0])
            elif method=="quad":
                def quad_fit(x, a, b, c):
                    return a*x**2 + b*x + c
                popt_quad, _ = curve_fit(quad_fit, Delta, dtune)
                chro.append(popt_quad[1])

            if do_plot:
                plt.figure()
                plt.scatter(Delta, dtune)
                if method=="lin":
                    plt.plot(Delta,
                             linear_fit(Delta, popt_lin[0], popt_lin[1]),
                             '--',
                             label="fit: {:.4f}x+{:.8f}".format(*popt_lin))
                elif method=="quad":
                    plt.plot(Delta, 
                             quad_fit(Delta, popt_quad[0], popt_quad[1], popt_quad[2]),
                             '--',
                             label="fit: {:.4f}x2+{:.4f}x+{:.4f}".format(*popt_quad))
                plt.xlabel('$\\delta$')
                if i == 0:
                    plt.title("Horizontal Chromaticity")
                    plt.ylabel('$\\delta Q_x$')
                else:
                    plt.title("Vertical Chromaticity")
                    plt.ylabel('$\\delta Q_y$')
                plt.legend()

        self._last_measured = np.array(chro)

        return self._last_measured





# exit()
# from ..common.element import Element, ElementConfigModel
# from ..common.abstract import ReadFloatArray
# from ..control.deviceaccess import DeviceAccess
# from .tune_monitor import BetatronTuneMonitor
# try:
#     from typing import Self  # Python 3.11+
# except ImportError:
#     from typing_extensions import Self  # Python 3.10 and earlier
# from pydantic import ConfigDict
# from scipy.optimize import curve_fit
# import matplotlib.pyplot as plt

# PYAMLCLASS = "ChromaticityMonitor"

# class ConfigModel(ElementConfigModel):

#     model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")
#     # tune_monitor: str
#     # """Betatron tune"""

#     tune_h: DeviceAccess
#     """Horizontal betatron tune"""
#     tune_v: DeviceAccess
#     """Vertical betatron tune"""


# class ChromaticityMonitor(Element):
#     """
#     Class providing measurement of chromaticity using betatron tune monitor of a physical or simulated lattice.
#     The monitor provides horizontal and vertical chromaticity (ksi) measurements.
#     """

#     def __init__(self, cfg: ConfigModel):
#         """
#         Construct a ChromaticityMonitor.
#         Parameters
#         ----------
#         cfg : ConfigModel
#             Configuration for the ChromaticityMonitor and BetatronTuneMonitor.
#         """
        
#         super().__init__(cfg.name)
#         self._cfg = cfg
#         self.__RFfreq = None
#         # self.__ksi = None

#     @property
#     def RFfreq(self) -> ReadFloatArray:
#         self.check_peer()
#         return self.__RFfreq

#     # @property
#     # def Ksi(self) -> ReadFloatArray:
#     #     self.check_peer()
#     #     return self.__ksi

#     # @property
#     # def chromaticity(self) -> ReadFloatArray:
#     #     return self.Ksi

#     def attach(self, peer, RFfreq: ReadFloatArray) -> Self:
#         obj = self.__class__(self._cfg)
#         obj.__RFfreq = RFfreq
#         obj._peer = peer
#         return obj

#     # def 