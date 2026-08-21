import logging
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pySC
from pydantic import ConfigDict
from pySC.apps import measure_bba
from pySC.apps.bba import BBAAnalysis
from pySC.apps.codes import BBACode

from ..common.constants import Action
from ..common.exception import PyAMLException
from ..external.pySC_interface import pySCInterface
from .measurement_tool import MeasurementTool, MeasurementToolConfigModel

logger = logging.getLogger(__name__)

PYAMLCLASS = "BBA"


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
    hcorr_delta : float
        Horizontal corrector delta strength
    vcorr_delta : float
        Vertical corrector delta strength
    hquad_delta : float
        Quadrupole delta strength (for h search)
    vquad_delta : float
        Quadrupole delta strength (for v search)

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    bpm_name: str
    hcorr_name: str
    vcorr_name: str
    quad_name: str
    hcorr_delta: float
    vcorr_delta: float
    hquad_delta: float
    vquad_delta: float


class BBA(MeasurementTool):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

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
        nb_meas = n_avg_meas if n_avg_meas is not None else self._cfg.n_avg_meas
        sleep_step = sleep_between_step if sleep_between_step is not None else self._cfg.sleep_between_step
        sleep_meas = sleep_between_meas if sleep_between_meas is not None else self._cfg.sleep_between_meas

        element_holder = self._peer
        interface = pySCInterface(
            element_holder=element_holder,
            bpm_array_name=self._cfg.bpm_array_name,
        )
        interface.set_wait_time = sleep_step
        interface.read_wait_time = sleep_meas

        bpms_names = element_holder.bpms.get(self._cfg.bpm_array_name).names()

        bba_pySC_config = {
            "number": bpms_names.index(self._cfg.bpm_name),
            "QUAD": self._cfg.quad_name,
            "HCORR": self._cfg.hcorr_name,
            "VCORR": self._cfg.vcorr_name,
            "HCORR_delta": self._cfg.hcorr_delta,
            "QUAD_dk_H": self._cfg.hquad_delta,
            "VCORR_delta": self._cfg.vcorr_delta,
            "QUAD_dk_V": self._cfg.vquad_delta,
            "magnet_type": "normal_quadrupole",
        }

        # logging.getLogger("pySC.apps.measurements").setLevel(logging.DEBUG)
        # logging.getLogger("pySC.apps.bba").setLevel(logging.DEBUG)

        generator = measure_bba(
            interface=interface,
            bpm_name=self._cfg.bpm_name,
            config=bba_pySC_config,
            shots_per_orbit=nb_meas,
            n_corr_steps=self._cfg.n_step,
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
        return self.latest_measurement["HData"].offset if self.latest_measurement["HData"] is not None else np.nan

    def h_offset_error(self) -> float:
        return self.latest_measurement["HData"].offset_error if self.latest_measurement["HData"] is not None else np.nan

    def v_offset(self) -> float:
        return self.latest_measurement["VData"].offset if self.latest_measurement["VData"] is not None else np.nan

    def v_offset_error(self) -> float:
        return self.latest_measurement["VData"].offset_error if self.latest_measurement["VData"] is not None else np.nan

    def plot_data(self, plane: str):
        """
        Plot BBA data.

        Parameters
        ----------
        plane: str
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

        axes["A"].set_xlabel(f"BPM position [μm]\n{self._cfg.bpm_name} offset = {offset * 1e6:.3f} [μm]")
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
        fig.canvas.manager.set_window_title(f"{plane} BBA {self._cfg.bpm_name}")

        plt.show()
