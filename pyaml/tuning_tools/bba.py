"""
Beam-based alignment measurement tools.

The :class:`BBA` tool determines the magnetic center of a quadrupole by
combining controlled quadrupole-strength changes with orbit measurements from
nearby beam-position monitors.
"""

import logging
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pySC
from pySC.apps import measure_bba
from pySC.apps.bba import BBAAnalysis
from pySC.apps.codes import BBACode

from ..common.constants import Action
from ..common.exception import PyAMLException
from ..external.pySC_interface import pySCInterface
from ..validation import DynamicValidation, register_schema
from .measurement_tool import MeasurementTool

logger = logging.getLogger(__name__)

PYAMLCLASS = "BBA"


@register_schema
class BBA(MeasurementTool, DynamicValidation):
    """
    Beam-based alignment measurement tool.

    This tool determines the magnetic center of a quadrupole by varying its
    strength while applying controlled horizontal and vertical orbit offsets.
    The quadrupole center is identified from the corresponding zero crossings
    in the BPM response.

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
    hcorr_delta : float
        Change in horizontal corrector strength used for each horizontal
        orbit-offset step.
    vcorr_delta : float
        Change in vertical corrector strength used for each vertical
        orbit-offset step.
    hquad_delta : float
        Change in quadrupole strength used during the horizontal alignment
        measurement.
    vquad_delta : float
        Change in quadrupole strength used during the vertical alignment
        measurement.
    n_step : int, default=1
        Number of orbit-offset steps to perform in each plane.
    sleep_between_step : float, default=0
        Time in seconds to wait after changing an orbit offset.
    n_avg_meas : int, default=1
        Number of BPM measurements to average at each step.
    sleep_between_meas : float, default=0
        Time in seconds to wait between individual BPM measurements.
    """

    def __init__(
        self,
        name: str,
        bpm_array_name: str,
        bpm_name: str,
        hcorr_name: str,
        vcorr_name: str,
        quad_name: str,
        hcorr_delta: float,
        vcorr_delta: float,
        hquad_delta: float,
        vquad_delta: float,
        n_step: int = 1,
        sleep_between_step: float = 0,
        n_avg_meas: int = 1,
        sleep_between_meas: float = 0,
    ):
        """
        Initialize the BBA.

        Parameters
        ----------
        name : str
            Name of the measurement tool.
        bpm_array_name : str
            Name of the BPM array used to measure the orbit.
        bpm_name : str
            Name of the BPM located near the quadrupole whose center is measured.
        hcorr_name : str
            Name of the horizontal corrector used to create horizontal orbit offsets at the quadrupole.
        vcorr_name : str
            Name of the vertical corrector used to create vertical orbit offsets at the quadrupole.
        quad_name : str
            Name of the quadrupole to align.
        hcorr_delta : float
            Change in horizontal corrector strength used for each horizontal orbit-offset step.
        vcorr_delta : float
            Change in vertical corrector strength used for each vertical orbit-offset step.
        hquad_delta : float
            Change in quadrupole strength used during the horizontal alignment measurement.
        vquad_delta : float
            Change in quadrupole strength used during the vertical alignment measurement.
        n_step : int
            Number of orbit-offset steps to perform in each plane.
        sleep_between_step : float
            Time in seconds to wait after changing an orbit offset.
        n_avg_meas : int
            Number of BPM measurements to average at each step.
        sleep_between_meas : float
            Time in seconds to wait between individual BPM measurements.
        """
        super().__init__(name)
        self.bpm_array_name = bpm_array_name
        self.bpm_name = bpm_name
        self.hcorr_name = hcorr_name
        self.vcorr_name = vcorr_name
        self.quad_name = quad_name
        self.hcorr_delta = hcorr_delta
        self.vcorr_delta = vcorr_delta
        self.hquad_delta = hquad_delta
        self.vquad_delta = vquad_delta
        self.n_step = n_step
        self.sleep_between_step = sleep_between_step
        self.n_avg_meas = n_avg_meas
        self.sleep_between_meas = sleep_between_meas

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
            SR = sr.design
            bba = SR.get_bba("BBA-BPM_C04-04")

            # Add a misalignement
            SR.get_bpm("BPM_C04-04").offset.set([20e-6,-15e-6])

            bba.measure(plane="H")
            print(f"HOffset: {bba.h_offset()}")

            bba.plot_data("H")

        Parameters
        ----------
        sleep_between_step : float
            Default time sleep after steerer or quad exitation
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
        nb_meas = n_avg_meas if n_avg_meas is not None else self.n_avg_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self.sleep_between_meas

        element_holder = self._peer
        interface = pySCInterface(
            element_holder=element_holder,
            bpm_array_name=self.bpm_array_name,
        )
        interface.set_wait_time = sleep_step
        interface.read_wait_time = sleep_meas

        bpms_names = element_holder.bpms.get(self.bpm_array_name).names()

        bba_pySC_config = {
            "number": bpms_names.index(self.bpm_name),
            "QUAD": self.quad_name,
            "HCORR": self.hcorr_name,
            "VCORR": self.vcorr_name,
            "HCORR_delta": self.hcorr_delta,
            "QUAD_dk_H": self.hquad_delta,
            "VCORR_delta": self.vcorr_delta,
            "QUAD_dk_V": self.vquad_delta,
            "magnet_type": "normal_quadrupole",
        }

        # logging.getLogger("pySC.apps.measurements").setLevel(logging.DEBUG)
        # logging.getLogger("pySC.apps.bba").setLevel(logging.DEBUG)

        generator = measure_bba(
            interface=interface,
            bpm_name=self.bpm_name,
            config=bba_pySC_config,
            shots_per_orbit=nb_meas,
            n_corr_steps=self.n_step,
            bipolar=False,
            skip_save=True,
            plane=plane,
            live_ios=True,
        )

        pySC.disable_pySC_rich()
        aborted = False
        err = None
        hstep = 0
        vstep = 0

        try:
            self._register_callback(callback)
            self._init_measure()
            self.latest_measurement["HData"] = None
            self.latest_measurement["VData"] = None
            for code, measurement_object in generator:
                if code == BBACode.HORIZONTAL_IOS_READY:
                    self.send_callback(
                        Action.MEASURE,
                        {
                            "step": hstep,
                            "plane": "H",
                            "bpm_pos": measurement_object.last_bpm_pos,
                            "ios": measurement_object.last_ios,
                            "bba_data": measurement_object.H_data,
                        },
                    )
                    hstep += 1
                if code == BBACode.VERTICAL_IOS_READY:
                    self.send_callback(
                        Action.MEASURE,
                        {
                            "step": vstep,
                            "plane": "V",
                            "bpm_pos": measurement_object.last_bpm_pos,
                            "ios": measurement_object.last_ios,
                            "bba_data": measurement_object.V_data,
                        },
                    )
                    vstep += 1
                if code == BBACode.HORIZONTAL_DONE:
                    result = BBAAnalysis.analyze(measurement_object.H_data)
                    self.latest_measurement["HData"] = result
                if code == BBACode.VERTICAL_DONE:
                    result = BBAAnalysis.analyze(measurement_object.V_data)
                    self.latest_measurement["VData"] = result

        except Exception as ex:
            err = ex
        except KeyboardInterrupt as ex:
            aborted = True
        finally:
            # Restore steerer/quad strength
            # TODO
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
        return self.latest_measurement["HData"].offset_error if self.latest_measurement["HData"] is not None else np.nan

    def v_offset(self) -> float:
        """Return the measured vertical magnetic-center offset."""
        return self.latest_measurement["VData"].offset if self.latest_measurement["VData"] is not None else np.nan

    def v_offset_error(self) -> float:
        """Return the uncertainty of the vertical center offset."""
        return self.latest_measurement["VData"].offset_error if self.latest_measurement["VData"] is not None else np.nan

    def plot_data(self, plane: str):
        """
        Plot BBA data.

        Parameters
        ----------
        plane : str
            Plane to plot ("H" or "V")
        """

        planeData = plane + "Data"
        if planeData not in self.latest_measurement or self.latest_measurement[planeData] is None:
            raise PyAMLException("No BBA data to plot, please call measure() first")

        fig, axes = plt.subplot_mosaic(mosaic=[["A", "A", "S", "S"], ["A", "A", "C", "C"]])

        bpm_pos = self.latest_measurement[planeData].bpm_position
        ios = self.latest_measurement[planeData].induced_orbit_shift
        slopes = self.latest_measurement[planeData].slopes
        centers = self.latest_measurement[planeData].centers
        final_mask = self.latest_measurement[planeData].mask_accepted
        offset = self.latest_measurement[planeData].offset

        xp_min = np.min(bpm_pos) * 1e6
        xp_max = np.max(bpm_pos) * 1e6
        for kk in range(len(ios[0, :])):
            p0 = np.polyfit(bpm_pos[:] * 1e6, ios[:, kk] * 1e6, 1)
            xp = np.linspace(xp_min, xp_max, 10)
            yp = p0[0] * xp + p0[1]
            axes["A"].plot(xp, yp, "-", c="C0" if final_mask[kk] else "C1", alpha=0.3)

        for kk in range(len(bpm_pos[:])):
            yy = ios[kk] * 1e6
            xx = np.ones_like(yy) * bpm_pos[kk] * 1e6
            axes["A"].plot(xx[final_mask], yy[final_mask], ".", c="C0")
            axes["A"].plot(xx[~final_mask], yy[~final_mask], ".", c="C1")

        axes["A"].set_xlabel(f"BPM position [μm]\n{self.bpm_name} offset = {offset * 1e6:.3f} [μm]")
        axes["A"].set_ylabel("Modulation [μm]")
        axes["A"].grid()

        bpm_numbers = np.arange(len(final_mask))
        axes["S"].plot(bpm_numbers[final_mask], slopes[final_mask], ".", c="C0", label="")
        axes["S"].plot(bpm_numbers[~final_mask], slopes[~final_mask], ".", c="C1")
        axes["S"].set_xlabel("BPM number")
        axes["S"].set_ylabel("Slope")
        axes["S"].grid()

        axes["C"].plot(bpm_numbers[final_mask], centers[final_mask] * 1e6, ".", c="C0")
        axes["C"].plot(bpm_numbers[~final_mask], centers[~final_mask] * 1e6, ".", c="C1", label="rejected")
        axes["C"].set_xlabel("BPM number")
        axes["C"].set_ylabel("Center [μm]")
        axes["C"].legend()
        axes["C"].grid()

        fig.tight_layout()
        fig.canvas.manager.set_window_title(f"{plane} BBA {self.bpm_name}")

        plt.show()
