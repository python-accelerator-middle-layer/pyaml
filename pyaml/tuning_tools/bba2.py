"""
Beam-based alignment analysis tools.

This module contains data structures and analysis helpers for estimating
quadrupole magnetic-center offsets from beam-position-monitor responses.
"""

import logging
import time
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np

from ..common.constants import Action
from ..common.exception import PyAMLException
from ..validation import DynamicValidation, register_schema
from .measurement_tool import MeasurementTool

logger = logging.getLogger(__name__)

PYAMLCLASS = "BBA2"


class BBAData:
    """
    Store intermediate data from one beam-based alignment plane.

    The container keeps fitted kicks, steerer steps, BPM responses, and the
    latest magnetic-center estimate for either the horizontal or vertical
    measurement.

    Methods
    -------
    append(st, dk, bpm, allbpm)
        Append one steerer-step measurement to the alignment data.
    update_offset(x, error, fit)
        Store the fitted magnetic-center offset and its uncertainty.
    """

    def __init__(self):
        """
        Initialize the BBAData.
        """
        self.k = []  # Fitted kick
        self.bpm_pos = []  # BPM#i position
        self.allbpm_pos = []  # IOS (Induced Orbit Shift)
        self.s2 = []  # sum of square
        self.steps = []  # steerer step
        self.lastfit = []  # Last linear fit

        self.offset = np.nan
        self.error = np.nan

    def append(self, st, dk, bpm, allbpm):
        # Append new dataset
        """
        Append one steerer-step measurement to the alignment data.

        Parameters
        ----------
        st : object
            Steerer kick applied for the measurement.
        dk : object
            Fitted kick response.
        bpm : object
            Orbit position at the reference BPM.
        allbpm : object
            Induced orbit shift measured at all BPMs.
        """
        self.steps.append(st)
        self.k.append(dk)
        self.bpm_pos.append(bpm)
        self.allbpm_pos.append(allbpm)

    def update_offset(self, x, error, fit):
        # Update offset value
        """
        Store the fitted magnetic-center offset and its uncertainty.

        Parameters
        ----------
        x : object
            Estimated magnetic-center offset.
        error : object
            Estimated standard error of the offset.
        fit : object
            Coefficients of the final linear fit.
        """
        self.offset = x
        self.error = error
        self.lastfit = fit


@register_schema
class BBA2(MeasurementTool, DynamicValidation):
    """
    Beam-based alignment tool with tune correction.

    This tool determines the magnetic center of a quadrupole from the BPM
    response to controlled horizontal and vertical orbit offsets. During the
    measurement, the quadrupole strength is varied and tune correction is used
    to compensate for the resulting tune change.

    Parameters
    ----------
    name : str
        Name of the measurement tool.
    bpm_array_name : str
        Name of the BPM array used to measure the orbit.
    bpm_name : str
        Name of the BPM located near the quadrupole whose center is measured.
    hcorr_name : str
        Name of the horizontal corrector used to create horizontal orbit
        offsets at the quadrupole.
    vcorr_name : str
        Name of the vertical corrector used to create vertical orbit offsets
        at the quadrupole.
    quad_name : str
        Name of the quadrupole to align.
    tune_correction_name : str
        Name of the tune-correction tool used to compensate for tune changes
        caused by varying the quadrupole strength.
    hcorr_delta : float
        Change in horizontal corrector strength used for each horizontal
        orbit-offset step.
    vcorr_delta : float
        Change in vertical corrector strength used for each vertical
        orbit-offset step.
    quad_delta : float
        Change in quadrupole strength used for the alignment measurement.
    bipolar_delta : bool, default=False
        If `True`, vary the quadrupole strength both above and below its
        initial value by `quad_delta`. If `False`, apply the change in one
        direction only.
    minicycle_sleep_time : float, default=5
        Time in seconds to wait for the quadrupole minicycle to complete after
        changing its strength.
    n_step : int, default=1
        Number of orbit-offset steps to perform in each plane.
    sleep_between_step : float, default=0
        Time in seconds to wait after changing an orbit offset.
    n_avg_meas : int, default=1
        Number of BPM measurements to average at each step.
    sleep_between_meas : float, default=0
        Time in seconds to wait between individual BPM measurements.

    Methods
    -------
    measure(...)
        Measure BBA.
    h_offset()
        Return the measured horizontal magnetic-center offset.
    h_offset_error()
        Return the uncertainty of the horizontal center offset.
    v_offset()
        Return the measured vertical magnetic-center offset.
    v_offset_error()
        Return the uncertainty of the vertical center offset.
    plot_plane_data(ax, plane)
        Plot measured kicks and the fitted alignment response for one plane.
    plot_data()
        Plot BBA data.
    """

    def __init__(
        self,
        name: str,
        bpm_array_name: str,
        bpm_name: str,
        hcorr_name: str,
        vcorr_name: str,
        quad_name: str,
        tune_correction_name: str,
        hcorr_delta: float,
        vcorr_delta: float,
        quad_delta: float,
        bipolar_delta: bool = False,
        minicycle_sleep_time: float = 5,
        n_step: int = 1,
        sleep_between_step: float = 0,
        n_avg_meas: int = 1,
        sleep_between_meas: float = 0,
    ):
        """
        Initialize a beam-based alignment tool with tune compensation.
        """
        super().__init__(name)
        self.bpm_array_name = bpm_array_name
        self.bpm_name = bpm_name
        self.hcorr_name = hcorr_name
        self.vcorr_name = vcorr_name
        self.quad_name = quad_name
        self.tune_correction_name = tune_correction_name
        self.hcorr_delta = hcorr_delta
        self.vcorr_delta = vcorr_delta
        self.quad_delta = quad_delta
        self.bipolar_delta = bipolar_delta
        self.minicycle_sleep_time = minicycle_sleep_time
        self.n_step = n_step
        self.sleep_between_step = sleep_between_step
        self.n_avg_meas = n_avg_meas
        self.sleep_between_meas = sleep_between_meas

    @staticmethod
    def _x_intercept(x, k, n):
        # Linear fit on last n points
        # x is not necessary ordered
        """
        Estimate the zero crossing of a linear fit.

        A first-degree polynomial is fitted to the final ``n`` samples of
        ``(x, k)``. The zero crossing of that fit and, when enough samples are
        available, its propagated standard error are returned.

        Parameters
        ----------
        x : array_like
            Independent-variable samples used for the fit.
        k : array_like
            Dependent-variable samples to fit as a function of ``x``.
        n : int
            Number of trailing samples to include in the fit.

        Returns
        -------
        intercept : float
            Estimated value of ``x`` for which the fitted ``k`` is zero.
        coefficients : numpy.ndarray
            Polynomial coefficients in increasing order, ``[intercept,
            slope]`` for the fitted ``k`` values.
        error : float
            Propagated standard error of ``intercept``. This is zero when
            fewer than three samples are used.
        """
        xx = np.polynomial.polynomial.polyfit(x[-n:], k[-n:], 1)
        err = 0
        if n > 2:
            # Compute error of the ratio r = -xx[0] / xx[1]
            X = np.polynomial.polynomial.polyvander(x[-n:], 1)
            R = k[-n:] - X @ xx
            S2 = np.sum(R**2) / float(n - 2)
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
        """
        Calculate normalized model responses for the alignment scan.

        The responses describe the effect of a dipole kick at the quadrupole
        and the horizontal and vertical steerers at the reference BPM.

        Parameters
        ----------
        tunename : str
            Name of the tune-correction tool.
        bpmname : str
            Name of the BPM array.
        quadname : str
            Name of the quadrupole.
        steererhname : str
            Name of the horizontal steerer.
        steerervname : str
            Name of the vertical steerer.
        bpmi : int
            Index of the reference BPM.
        dk0 : object
            Small calibration kick used to calculate model responses.
        """
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

        """
        Fit a scale factor between measured and reference orbit shifts.

        The fit is performed through the origin using the selected samples.
        This estimates the kick amplitude that best matches ``ref`` to
        ``meas`` in a least-squares sense.

        Parameters
        ----------
        meas : array_like
            Measured induced orbit shifts.
        ref : array_like
            Reference or theoretical orbit shifts.
        mask : array_like
            Boolean mask selecting samples included in the fit.

        Returns
        -------
        float
            Fitted scale factor. Returns ``0`` when the selected reference
            shifts contain no signal.
        """
        xy = np.multiply(meas[mask], ref[mask])
        xx = np.multiply(ref[mask], ref[mask])
        if sum(xx) == 0:
            return 0
        else:
            return sum(xy) / sum(xx)

    def _get_averaged_orbit(self):
        # Get averaged orbit

        """Return the orbit averaged over the configured measurements."""
        avgorb = np.zeros((len(self._bpms), 2))
        for avg in range(self._nb_meas):
            o = self._bpms.positions.get()
            avgorb += o
            if avg < self._nb_meas - 1:
                time.sleep(self._sleep_meas)

        avgorb /= float(self._nb_meas)
        return avgorb

    def _one_step_dk(self, dk0: list[float], dk1: float, bipolar_delta: bool):
        # Measrue IOS

        """
        Measure the induced orbit shift for one quadrupole-strength step.

        The configured steerers and quadrupole are changed temporarily. The
        orbit is measured before and after the quadrupole step, then the
        quadrupole is restored to its initial strength. For bipolar steps, the
        response is calculated from both positive and negative perturbations.

        Parameters
        ----------
        dk0 : list[float]
            Horizontal and vertical steerer kicks to apply.
        dk1 : float
            Quadrupole-strength step.
        bipolar_delta : bool
            If ``True``, measure both positive and negative quadrupole steps.

        Returns
        -------
        tuple
            ``(x, dkx, y, dky, ios_x, ios_y)`` containing the orbit at the
            reference BPM, fitted horizontal and vertical kick factors, and
            the horizontal and vertical induced orbit shifts.

        Raises
        ------
        PyAMLException
            If either requested steerer kick exceeds 200 microradians.
        """
        if any(abs(dk) > 200e-6 for dk in dk0):
            raise PyAMLException("Requested dk too high (>200urad), consider using bump")

        # Set steerer
        if np.fabs(dk0[0]) > 0:
            _str = dk0[0] + self._initial_k0[0]
            self._h_steer.strength.set(_str)
            self.send_callback(Action.APPLY, {"step": self._step, "magnet": self._h_steer.name, "strength": _str})
        if np.fabs(dk0[1]) > 0:
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
        sleep_between_step : float
            Default time sleep after steerer or quad excitation
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
        plane : str, optional
            Plane to perform ("H" or "V", None => both plane)
        """
        self._nb_meas = n_avg_meas if n_avg_meas is not None else self.n_avg_meas
        self._sleep_step = sleep_between_step if sleep_between_step is not None else self.sleep_between_step
        self._sleep_meas = sleep_between_meas if sleep_between_meas is not None else self.sleep_between_meas

        # Device handles
        self.check_peer()
        self._h_steer = self.peer.magnet.get(self.hcorr_name)
        self._v_steer = self.peer.magnet.get(self.vcorr_name)
        self._quad = self.peer.magnet.get(self.quad_name)
        self._bpms = self.peer.bpms.get(self.bpm_array_name)
        self._bpmi = self._bpms.names().index(self.bpm_name)

        # Initial values
        self._initial_k0 = [self._h_steer.strength.get(), self._v_steer.strength.get()]
        self._initial_k1 = self._quad.strength.get()
        self._quad_polarity = np.sign(self._initial_k1) if self._initial_k1 != 0 else 1

        self._ref_ios, fx, fy = self._init_responses(
            self.tune_correction_name,
            self.bpm_array_name,
            self.quad_name,
            self.hcorr_name,
            self.vcorr_name,
            self._bpmi,
        )

        dk0h = self.hcorr_delta if plane is None or plane == "H" else 0
        dk0v = self.vcorr_delta if plane is None or plane == "V" else 0
        dk1 = self.quad_delta
        bidelta = self.bipolar_delta
        doH = dk0h != 0
        doV = dk0v != 0
        aborted = False
        err = None

        logger.debug(f"Initial H corrector {self.hcorr_name} value: {self._initial_k0[0]} rad")
        logger.debug(f"Initial V corrector {self.vcorr_name} value: {self._initial_k0[1]} rad")
        logger.debug(f"Initial quad {self.quad_name} value: {self._initial_k1} m-1")

        try:
            self._register_callback(callback)
            self._init_measure()
            self.latest_measurement["HData"] = None
            self.latest_measurement["VData"] = None
            X = BBAData()
            Y = BBAData()

            # Mini cycle
            if self.minicycle_sleep_time > 0:
                logger.debug(f"Quad mini cycling {self.quad_name}")
                _str = self._initial_k1 + dk1 * self._quad_polarity
                self._quad.strength.set(_str)
                self.send_callback(Action.APPLY, {"step": -1, "magnet": self._quad.name, "strength": _str})
                time.sleep(self.minicycle_sleep_time)
                _str = self._initial_k1
                self._quad.strength.set(_str)
                self.send_callback(Action.APPLY, {"step": -1, "magnet": self._quad.name, "strength": _str})
                time.sleep(self.minicycle_sleep_time)

            opt_found = False
            self._step = 0
            stx = 0
            sty = 0
            while not opt_found and self._step < 9:
                ist = self._step % 3
                _from = f"{stx},{sty}"

                if ist == 0:
                    stx -= dk0h
                    sty -= dk0v
                    _to = f"{stx},{sty}"
                    logger.debug(f"Moving in the negative direction: {_from} -> {_to}")

                if ist == 1:
                    stx += 2 * dk0h
                    sty += 2 * dk0v
                    _to = f"{stx},{sty}"
                    logger.debug(f"Moving in the positive direction: {_from} -> {_to}")

                if ist == 2:
                    H_found = False
                    V_found = False

                    if doH:
                        stx, _, _ = BBA2._x_intercept(X.steps, X.k, 2)
                        H_found = X.steps[-2] <= stx <= X.steps[-1]  # don't rely on extrapolation
                    if doV:
                        sty, _, _ = BBA2._x_intercept(Y.steps, Y.k, 2)
                        V_found = Y.steps[-2] <= sty <= Y.steps[-1]  # don't rely on extrapolation

                    opt_found = (
                        doH and not doV and H_found or not doH and doV and V_found or doH and doV and H_found and V_found
                    )

                    _to = f"{stx},{sty}"
                    logger.debug(f"Moving to the best guess: {_from} -> {_to}")

                x, dkx, y, dky, dataxbpm, dataybpm = self._one_step_dk([stx, sty], dk1, bidelta)
                X.append(stx, dkx, x, dataxbpm)
                Y.append(sty, dky, y, dataybpm)

                if doH:
                    self.send_callback(Action.MEASURE, {"step": self._step, "plane": "H", "bpm_pos": x, "ios": dataxbpm})

                if doV:
                    self.send_callback(Action.MEASURE, {"step": self._step, "plane": "V", "bpm_pos": y, "ios": dataybpm})

                self._step += 1

            # Final step

            if doH:
                stx, lxfit, errx = BBA2._x_intercept(X.steps, X.k, 3)

            if doV:
                sty, lyfit, erry = BBA2._x_intercept(Y.steps, Y.k, 3)

            _to = f"{stx},{sty}"
            logger.debug(f"Moving to the optimum: {_to}")

            x, dkx, y, dky, dataxbpm, dataybpm = self._one_step_dk([stx, sty], dk1, bidelta)
            X.append(stx, dkx, x, dataxbpm)
            Y.append(sty, dky, y, dataybpm)

            if doH:
                X.update_offset(x, errx * np.fabs(fx), lxfit)
                self.latest_measurement["HData"] = X

            if doV:
                Y.update_offset(y, erry * np.fabs(fy), lyfit)
                self.latest_measurement["VData"] = Y

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

    def h_offset(self) -> float:
        """Return the measured horizontal magnetic-center offset."""
        return self.latest_measurement["HData"].offset if self.latest_measurement["HData"] is not None else np.nan

    def h_offset_error(self) -> float:
        """Return the uncertainty of the horizontal center offset."""
        return self.latest_measurement["HData"].error if self.latest_measurement["HData"] is not None else np.nan

    def v_offset(self) -> float:
        """Return the measured vertical magnetic-center offset."""
        return self.latest_measurement["VData"].offset if self.latest_measurement["VData"] is not None else np.nan

    def v_offset_error(self) -> float:
        """Return the uncertainty of the vertical center offset."""
        return self.latest_measurement["VData"].error if self.latest_measurement["VData"] is not None else np.nan

    def plot_plane_data(self, ax, plane: str):
        """
        Plot measured kicks and the fitted alignment response for one plane.

        Parameters
        ----------
        ax : object
            Matplotlib axes on which to draw the data.
        plane : str
            Plane data key, typically ``"HData"`` or ``"VData"``.
        """
        yp = self.latest_measurement[plane].k
        xp = self.latest_measurement[plane].steps

        b = self.latest_measurement[plane].lastfit[0]
        a = self.latest_measurement[plane].lastfit[1]

        ax.plot(xp, yp, marker="o", linewidth=0)
        ax.axline((0, b), slope=a, linestyle="--", color="lightblue", label="last fit")
        ax.plot(xp[-4:-1], yp[-4:-1], color="salmon", marker="o", linewidth=0, label="last fit")
        ax.plot(xp[-1:], yp[-1:], color="green", marker="o", linewidth=0, label="optimum")
        ax.set_xlabel(f"Steerer (rad)\nOptimun kick @ bpm={self.latest_measurement[plane].offset * 1e6:.3f} um")
        ax.set_ylabel("Fitted kick")
        ax.grid()
        ax.legend()

    def plot_data(self):
        """
        Plot BBA data.
        """

        noH = "HData" not in self.latest_measurement or self.latest_measurement["HData"] is None
        noV = "VData" not in self.latest_measurement or self.latest_measurement["VData"] is None
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
        fig.canvas.manager.set_window_title(f"BBA {self.bpm_name}")

        plt.show()
