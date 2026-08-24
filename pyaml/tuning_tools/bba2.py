import logging
import time
from enum import Enum
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np
from pydantic import ConfigDict

from ..common.constants import Action
from ..common.exception import PyAMLException
from .measurement_tool import MeasurementTool, MeasurementToolConfigModel

logger = logging.getLogger(__name__)

PYAMLCLASS = "BBA2"


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
    optimum_check: bool
        Make an extra step to check the optimun
    tune_correction_name: str
        Tune tuning tool
    hcorr_delta : float
        Horizontal corrector delta strength
    vcorr_delta : float
        Vertical corrector delta strength
    quad_delta : float
        Quadrupole delta strength
    bipolar_delta : bool
        Perform scan at initial_quad_strength +/- quad delta
    minicyle_sleep_time : float
        Time to wait for quad mini cycle
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    bpm_name: str
    hcorr_name: str
    vcorr_name: str
    quad_name: str
    optimum_check: bool = True
    tune_correction_name: str
    hcorr_delta: float
    vcorr_delta: float
    quad_delta: float
    bipolar_delta: bool = False
    minicyle_sleep_time: float = 5


class BBAData:
    class OPT_TYPE(Enum):
        NONE = 0
        INTERPOLATED = 1
        MEASURED = 2

    def __init__(self):
        self.k = []  # Fitted kick
        self.bpm_pos = []  # BPM#i position
        self.allbpm_pos = []  # IOS (Induced Orbit Shift)
        self.steps = []  # steerer step

        self.opt_type = BBAData.OPT_TYPE.NONE

    def append(self, st, dk, bpm, allbpm):
        # Append new dataset
        self.steps.append(st)
        self.k.append(dk)
        self.bpm_pos.append(bpm)
        self.allbpm_pos.append(allbpm)

    def set_optimum(
        self,
        type: OPT_TYPE,
        s: float = np.nan,
        x: float = np.nan,
        k: float = np.nan,
        error: float = np.nan,
        fit: np.array = None,
    ):
        # Update optimum values
        self.opt_type = type
        self.opt_step = s
        self.opt_k = k
        self.opt_offset = x
        self.opt_error = error
        self.opt_fit = fit

    def to_dict(self) -> dict:
        def _arr(v):
            return v.tolist() if isinstance(v, np.ndarray) else v

        return {
            "k": _arr(self.k),
            "bpm_pos": _arr(self.bpm_pos),
            "allbpm_pos": [_arr(a) for a in self.allbpm_pos],
            "steps": _arr(self.steps),
            "opt_type": self.opt_type.name,
            "opt_step": getattr(self, "opt_step", np.nan),
            "opt_k": getattr(self, "opt_k", np.nan),
            "opt_offset": getattr(self, "opt_offset", np.nan),
            "opt_error": getattr(self, "opt_error", np.nan),
            "opt_fit": _arr(getattr(self, "opt_fit", None)),
        }


class BBA2(MeasurementTool):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

    @staticmethod
    def _x_intercept(x, k):
        # x is not necessary ordered
        xx = np.polynomial.polynomial.polyfit(x, k, 1)
        err = 0
        if len(x) > 2:
            # Compute error of the ratio r = -xx[0] / xx[1]
            X = np.polynomial.polynomial.polyvander(x, 1)
            R = k - X @ xx
            S2 = np.sum(R**2) / float(len(x) - 2)
            COV = S2 * np.linalg.inv(X.T @ X)
            J = [-1 / xx[1], xx[0] / xx[1] ** 2]  # Jacobian [dr/d(xx[0]) , dr/d(xx[1])]
            err = np.sqrt(J @ COV @ J)

        # return x @y=0
        return (-xx[0] / xx[1], xx, err)

    def _init_responses(
        self, tunename: str, bpmname: str, quadname: str, steererhname: str, steerervname: str, bpmi: int, dk0=1e-5
    ):
        # Return:
        #   normalized response of a dipolar kick in a quad from the model (all bpms)
        #   normalized response of horizontal steerer from the model at bpm #i
        #   normalized response of vertical steerer from the model at bpm #i

        # Retrieve model handle
        design = self.peer.peer.design

        # handles
        quad = design.magnet.get(quadname)
        sth = design.magnet.get(steererhname)
        stv = design.magnet.get(steerervname)
        orbit = design.bpms.get(bpmname).positions
        tune_design = design.get_tune_tuning(tunename)
        tune_live = self._peer.get_tune_tuning(tunename)

        # Get tune from live and adjust the model to improve quad response phase
        tune0 = tune_design.readback()
        tune = tune_live.readback()
        logger.debug(f"Live tune: {tune}")
        logger.debug(f"Model tune: {tune0}")
        tune_design.set(tune)
        logger.debug(f"Model tune: {tune_design.readback()}")

        # quadrupole
        a0 = quad.strength.get("PolynomA", 0)
        b0 = quad.strength.get("PolynomB", 0)
        step = [-dk0, 0, dk0]

        orb0 = orbit.get()
        quad.strength.set(b0 - dk0, "PolynomB", 0)
        orbm = orbit.get()
        quad.strength.set(b0 + dk0, "PolynomB", 0)
        orbp = orbit.get()
        quad.strength.set(b0, "PolynomB", 0)

        orbx = [orbm[:, 0], orb0[:, 0], orbp[:, 0]]
        fit = np.polynomial.polynomial.polyfit(step, orbx, 1)
        ref_ios_x = fit[1]

        quad.strength.set(a0 - dk0, "PolynomA", 0)
        orbm = orbit.get()
        quad.strength.set(a0 + dk0, "PolynomA", 0)
        orbp = orbit.get()
        quad.strength.set(a0, "PolynomA", 0)

        orby = [orbm[:, 1], orb0[:, 1], orbp[:, 1]]
        fit = np.polynomial.polynomial.polyfit(step, orby, 1)
        ref_ios_y = fit[1]

        # steerers
        a0 = sth.strength.get()
        b0 = stv.strength.get()
        step = [-dk0, 0, dk0]

        orb0 = orbit.get()
        sth.strength.set(b0 - dk0)
        orbm = orbit.get()
        sth.strength.set(b0 + dk0)
        orbp = orbit.get()
        sth.strength.set(b0)

        orbx = [orbm[bpmi, 0], orb0[bpmi, 0], orbp[bpmi, 0]]
        fit = np.polynomial.polynomial.polyfit(step, orbx, 1)
        bpm_fact_x = fit[1]

        stv.strength.set(a0 - dk0)
        orbm = orbit.get()
        stv.strength.set(a0 + dk0)
        orbp = orbit.get()
        stv.strength.set(a0)

        orby = [orbm[bpmi, 1], orb0[bpmi, 1], orbp[bpmi, 1]]
        fit = np.polynomial.polynomial.polyfit(step, orby, 1)
        bpm_fact_y = fit[1]

        # Restore tune
        tune_design.set(tune0)

        ref = np.array([ref_ios_x, ref_ios_y]).T
        return ref, bpm_fact_x, bpm_fact_y

    def _fit_kick(self, meas, ref, mask):
        # Correlate measured ios and theoretical one

        xy = np.multiply(meas[mask], ref[mask])
        xx = np.multiply(ref[mask], ref[mask])
        if sum(xx) == 0:
            return 0
        else:
            return sum(xy) / sum(xx)

    def _get_averaged_orbit(self):
        # Get averaged orbit

        avgorb = np.zeros((len(self._bpms), 2))
        for avg in range(self._nb_meas):
            o = self._bpms.positions.get()
            avgorb += o
            if avg < self._nb_meas - 1:
                time.sleep(self._sleep_meas)

        avgorb /= float(self._nb_meas)
        return avgorb

    def _one_step_dk(self, dk0: list[float], dk1: float, doH: bool, doV: bool, bipolar_delta: bool):
        # Measure IOS

        if any(abs(dk) > 200e-6 for dk in dk0):
            raise PyAMLException("Requested dk too high (>200urad), consider using bump")

        # Set steerer
        if doH:
            _str = dk0[0] + self._initial_k0[0]
            self._h_steer.strength.set(_str)
            self.send_callback(Action.APPLY, {"step": self._step, "magnet": self._h_steer.name, "strength": _str})
        if doV:
            _str = dk0[1] + self._initial_k0[1]
            self._v_steer.strength.set(_str)
            self.send_callback(Action.APPLY, {"step": self._step, "magnet": self._v_steer.name, "strength": _str})

        time.sleep(self._sleep_step)
        orb0 = self._get_averaged_orbit()

        # Set quad
        _str = self._initial_k1 + dk1 * self._quad_polarity
        self._quad.strength.set(_str)
        self.send_callback(Action.APPLY, {"step": self._step, "magnet": self._quad.name, "strength": _str})
        time.sleep(self._sleep_step)
        orbp = self._get_averaged_orbit()

        ios_x = []
        ios_y = []

        if bipolar_delta:
            # one more point at k1 - dk1
            _str = self._initial_k1 - dk1 * self._quad_polarity
            self._quad.strength.set(_str)
            self.send_callback(Action.APPLY, {"step": self._step, "magnet": self._quad.name, "strength": _str})
            time.sleep(self._sleep_step)
            orbm = self._get_averaged_orbit()
            # take slopes and compute corresponding delta orbit
            stepx = [-dk1 * self._quad_polarity, 0, dk1 * self._quad_polarity]
            orbx = [orbm[:, 0], orb0[:, 0], orbp[:, 0]]
            fit = np.polynomial.polynomial.polyfit(stepx, orbx, 1)
            ios_x = fit[1] * dk1

            orby = [orbm[:, 1], orb0[:, 1], orbp[:, 1]]
            fit = np.polynomial.polynomial.polyfit(stepx, orby, 1)
            ios_y = fit[1] * dk1
        else:
            ios_x = orbp[:, 0] - orb0[:, 0]
            ios_y = orbp[:, 1] - orb0[:, 1]

        # resotre quad
        _str = self._initial_k1
        self._quad.strength.set(_str)
        self.send_callback(Action.APPLY, {"step": self._step, "magnet": self._quad.name, "strength": _str})

        nanx = ~np.isnan(ios_x)
        x = orb0[self._bpmi, 0]
        dkx = self._fit_kick(ios_x, self._ref_ios[:, 0], nanx)

        nany = ~np.isnan(ios_y)
        y = orb0[self._bpmi, 1]
        dky = self._fit_kick(ios_y, self._ref_ios[:, 1], nany)

        return x, dkx, y, dky, ios_x, ios_y

    def measure(
        self,
        sleep_between_step: Optional[float] = None,
        n_avg_meas: Optional[int] = None,
        sleep_between_meas: Optional[float] = None,
        callback: Optional[Callable] = None,
        plane: Optional[str] = None,
    ):
        """
        Measure BBA.

        **Example**

        .. code-block:: python

            sr = Accelerator.load("tests/config/EBSOrbit.yaml")
            SR = sr.live
            bba = SR.get_bba("BBA2-BPM_C04-04")

            # Add a misalignement
            SR.get_bpm("BPM_C04-04").offset.set([200e-6,-150e-6])

            bba.measure(sleep_between_step=6,plane='V',callback=bba_callback)

            print(f"HOffset: {bba.h_offset()*1e6:.3f} um {bba.h_offset_error()}")
            print(f"VOffset: {bba.v_offset()*1e6:.3f} um {bba.v_offset_error()}")

            bba.plot_data()


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
        plane: str, optional
            Plane to perform ("H" or "V", None => both plane)
        """
        if self._cfg.n_step < 2:
            raise PyAMLException(f"{self._cfg.n_step} steps configured but at least 2 steps are required to perform BBA")

        self._nb_meas = n_avg_meas if n_avg_meas is not None else self._cfg.n_avg_meas
        self._sleep_step = sleep_between_step if sleep_between_step is not None else self._cfg.sleep_between_step
        self._sleep_meas = sleep_between_meas if sleep_between_meas is not None else self._cfg.sleep_between_meas

        # Device handles
        self.check_peer()
        self._h_steer = self.peer.magnet.get(self._cfg.hcorr_name)
        self._v_steer = self.peer.magnet.get(self._cfg.vcorr_name)
        self._quad = self.peer.magnet.get(self._cfg.quad_name)
        self._bpms = self.peer.bpms.get(self._cfg.bpm_array_name)
        self._bpmi = self._bpms.names().index(self._cfg.bpm_name)

        # Initial values
        self._initial_k0 = [self._h_steer.strength.get(), self._v_steer.strength.get()]
        self._initial_k1 = self._quad.strength.get()
        self._quad_polarity = np.sign(self._initial_k1) if self._initial_k1 != 0 else 1
        self._register_callback(callback)
        self._init_measure()
        X = BBAData()
        Y = BBAData()

        self._ref_ios, fx, fy = self._init_responses(
            self._cfg.tune_correction_name,
            self._cfg.bpm_array_name,
            self._cfg.quad_name,
            self._cfg.hcorr_name,
            self._cfg.vcorr_name,
            self._bpmi,
        )

        dk0h = self._cfg.hcorr_delta if plane is None or plane == "H" else 0
        dk0v = self._cfg.vcorr_delta if plane is None or plane == "V" else 0
        dk1 = self._cfg.quad_delta
        bidelta = self._cfg.bipolar_delta
        doH = dk0h != 0
        doV = dk0v != 0
        aborted = False
        err = None

        logger.debug(f"Initial H corrector {self._cfg.hcorr_name} value: {self._initial_k0[0]} rad")
        logger.debug(f"Initial V corrector {self._cfg.vcorr_name} value: {self._initial_k0[1]} rad")
        logger.debug(f"Initial quad {self._cfg.quad_name} value: {self._initial_k1} m-1")

        try:
            # Mini cycle
            if self._cfg.minicyle_sleep_time > 0:
                logger.debug(f"Quad mini cycling {self._cfg.quad_name}")
                _str = self._initial_k1 + dk1 * self._quad_polarity
                self._quad.strength.set(_str)
                self.send_callback(Action.APPLY, {"step": -1, "magnet": self._quad.name, "strength": _str})
                time.sleep(self._cfg.minicyle_sleep_time)
                _str = self._initial_k1
                self._quad.strength.set(_str)
                self.send_callback(Action.APPLY, {"step": -1, "magnet": self._quad.name, "strength": _str})
                time.sleep(self._cfg.minicyle_sleep_time)

            stepsx = np.linspace(-dk0h, dk0h, self._cfg.n_step)
            stepsy = np.linspace(-dk0v, dk0v, self._cfg.n_step)

            # IOS measurement loop
            for s in range(self._cfg.n_step):
                self._step = s
                stx = stepsx[s]
                sty = stepsy[s]
                _to = f"{stx},{sty}"
                logger.debug(f"Moving to: {_to}")
                x, dkx, y, dky, dataxbpm, dataybpm = self._one_step_dk([stx, sty], dk1, doH, doV, bidelta)
                X.append(stx, dkx, x, dataxbpm)
                Y.append(sty, dky, y, dataybpm)
                if doH:
                    self.send_callback(Action.MEASURE, {"step": s, "plane": "H", "bpm_pos": x, "ios": dataxbpm})
                if doV:
                    self.send_callback(Action.MEASURE, {"step": s, "plane": "V", "bpm_pos": y, "ios": dataybpm})

            # inter(extra)polate optimum
            stx, x, dkx, errx, lxfit = (0, 0, 0, np.nan, None)
            sty, y, dky, erry, lyfit = (0, 0, 0, np.nan, None)
            opt_type = BBAData.OPT_TYPE.NONE
            if doH:
                stx, lxfit, errx = BBA2._x_intercept(X.steps, X.k)
            if doV:
                sty, lyfit, erry = BBA2._x_intercept(Y.steps, Y.k)
            found = f"{stx},{sty}"
            logger.debug(f"Found optimum: {found}")

            # Optimum check
            if self._cfg.optimum_check:
                logger.debug(f"Moving to optimum: {found}")
                x, dkx, y, dky, dataxbpm, dataybpm = self._one_step_dk([stx, sty], dk1, doH, doV, bidelta)
                X.append(stx, dkx, x, dataxbpm)
                Y.append(sty, dky, y, dataybpm)
                opt_type = BBAData.OPT_TYPE.MEASURED
            else:
                logger.debug(f"Approximate BPM offset at optimum: {found}")
                xfitpos = np.polynomial.polynomial.polyfit(X.steps, X.bpm_pos, 1)
                yfitpos = np.polynomial.polynomial.polyfit(Y.steps, Y.bpm_pos, 1)
                x = stx * xfitpos[1] + xfitpos[0]
                y = sty * yfitpos[1] + yfitpos[0]
                opt_type = BBAData.OPT_TYPE.INTERPOLATED

            if doH:
                X.set_optimum(opt_type, stx, x, dkx, errx * np.fabs(fx), lxfit)

            if doV:
                Y.set_optimum(opt_type, sty, y, dky, erry * np.fabs(fy), lyfit)

            self.latest_measurement["HData"] = X.to_dict()
            self.latest_measurement["VData"] = Y.to_dict()

        except Exception as ex:
            err = ex
        except KeyboardInterrupt as ex:
            aborted = True
        finally:
            # Restore steerer/quad strength
            if doH:
                self._h_steer.strength.set(self._initial_k0[0])
            if doV:
                self._v_steer.strength.set(self._initial_k0[1])
            self._quad.strength.set(self._initial_k1)
            self.send_callback(
                Action.RESTORE,
                {},
                raiseException=False,
            )

        if err is not None:
            raise (err)

        if aborted:
            logger.warning(f"{self.get_name()} : measurement aborted (settings not restored)")
            return False

        return True

    def _check_opt(self, plane):
        if self.latest_measurement is None:
            raise PyAMLException("No BBA data, please call measure() first")
        if self.latest_measurement[plane]["opt_type"] == BBAData.OPT_TYPE.NONE.name:
            raise PyAMLException(f"No BBA data found for {plane}")

    def h_offset(self) -> float:
        self._check_opt("HData")
        return self.latest_measurement["HData"]["opt_offset"]

    def h_offset_error(self) -> float:
        self._check_opt("HData")
        return self.latest_measurement["HData"]["opt_error"]

    def v_offset(self) -> float:
        self._check_opt("VData")
        return self.latest_measurement["VData"]["opt_offset"]

    def v_offset_error(self) -> float:
        self._check_opt("VData")
        return self.latest_measurement["VData"]["opt_error"]

    def plot_plane_data(self, ax, plane: str):
        yp = self.latest_measurement[plane]["k"]
        xp = self.latest_measurement[plane]["steps"]
        ax.plot(xp, yp, marker="o", linewidth=0)

        b = self.latest_measurement[plane]["opt_fit"][0]
        a = self.latest_measurement[plane]["opt_fit"][1]
        ax.axline((0, b), slope=a, linestyle="--", color="lightblue", label="last fit")

        optx = self.latest_measurement[plane]["opt_step"]
        opty = self.latest_measurement[plane]["opt_k"]
        ax.plot([optx], [opty], color="green", marker="o", linewidth=0, label="optimum")

        ax.set_xlabel(f"Steerer (rad)\nOptimun kick @ bpm={self.latest_measurement[plane]['opt_offset'] * 1e6:.3f} um")
        ax.set_ylabel("Fitted kick")
        ax.grid()
        ax.legend()

    def plot_data(self):
        """
        Plot BBA data.
        """
        if self.latest_measurement is None:
            raise PyAMLException("No BBA data, please call measure() first")

        noH = self.latest_measurement["HData"]["opt_type"] == BBAData.OPT_TYPE.NONE.name
        noV = self.latest_measurement["VData"]["opt_type"] == BBAData.OPT_TYPE.NONE.name
        nrow = 0 if noH else 1
        nrow += 0 if noV else 1

        if nrow == 0:
            raise PyAMLException("No BBA data to plot, please call measure() first")

        fig = plt.figure()
        irow = 1
        if not noH:
            ax = fig.add_subplot(nrow, 1, irow)
            self.plot_plane_data(ax, "HData")
            irow += 1
        if not noV:
            ax = fig.add_subplot(nrow, 1, irow)
            self.plot_plane_data(ax, "VData")

        fig.tight_layout()
        fig.canvas.manager.set_window_title(f"BBA {self._cfg.bpm_name}")

        plt.show()
