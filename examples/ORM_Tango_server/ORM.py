"""
ORM

Orbit Response Matrix Measurement
"""

# PyTango imports
import threading

import numpy as np
import tango
from tango import AttrQuality, AttrWriteType, DebugIt, DevState, DispLevel
from tango.server import Device, attribute, command, device_property, run

from pyaml.accelerator import Accelerator

# Additional import
from pyaml.common.constants import ACTION_RESTORE

__all__ = ["ORM", "main"]

DEVICE: "ORM" = None


# Callback wrapper
def orbit_callback(action: int, cdata):
    return DEVICE.orbit_callback(action, cdata)


class ORM(Device):
    """
    Orbit Response Matrix Measurement

    **Properties:**

    - Device Property
        ConfigFileName
            - PyAML yaml comfig file
            - Type:'str'
    """

    # -----------------
    # Device Properties
    # -----------------

    ConfigFileName = device_property(dtype="str", doc="PyAML yaml comfig file")

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        """Initializes the attributes and properties of the ORM."""
        global DEVICE
        Device.init_device(self)
        DEVICE = self

        self.SR = Accelerator.load(self.ConfigFileName)
        self.orm_data = None
        nb_hsteer = len(self.SR.design.get_magnets("HCorr"))
        nb_vsteer = len(self.SR.design.get_magnets("VCorr"))
        self.progress_data = [0] * 2 * (nb_hsteer + nb_vsteer)
        self.set_status(f"Ready to scan: {self.ConfigFileName}")
        self.set_state(DevState.ON)

    def always_executed_hook(self):
        """Method always executed before any TANGO command is executed."""
        pass

    def delete_device(self):
        """Hook to delete resources allocated in init_device.

        This method allows for any memory or other resources allocated in the
        init_device method to be released.  This method is called by the device
        destructor and by the device Init command.
        """
        pass

    # Orbit callback
    def orbit_callback(self, action: int, cdata):
        if action == ACTION_RESTORE:
            i = cdata.last_number
            n_bpms = cdata.raw_up.shape[0] // 2
            n_correctors = cdata.raw_up.shape[1]
            corrector = cdata.last_input
            response = cdata.raw_up[:, i] - cdata.raw_down[:, i]
            response = response / cdata.inputs_delta[i]
            std_x_resp = np.std(response[:n_bpms])
            std_y_resp = np.std(response[n_bpms:])
            self.progress_data[2 * i : 2 * i + 2] = [std_x_resp, std_y_resp]
            self.set_status(
                f"[{i}/{n_correctors}], Measured response of {corrector}: "
                f"r.m.s H.: {std_x_resp:.2f} um/mrad, "
                f"r.n.s V: {std_y_resp:.2f} um/mrad"
            )
        return True

    def orm_run(self):
        # On design sleep 10ms to allow thread schedule
        self.SR.design.orm.measure(callback=orbit_callback, set_wait_time=0.01)
        self.orm_data = self.SR.design.orm.get()
        self.set_status(f"Ready to scan: {self.ConfigFileName}")
        self.set_state(DevState.ON)

    # ----------
    # Attributes
    # ----------
    @attribute(
        label="Progress",
        dtype=("DevDouble",),
        max_dim_x=2048,
    )
    def progress(self):
        return self.progress_data

    @attribute(
        label="Matrix",
        dtype=(("DevDouble",),),
        max_dim_x=1024,
        max_dim_y=1024,
    )
    def matrix(self):
        if self.orm_data:
            return np.array(self.orm_data["matrix"])
        else:
            return [[0.0]]

    # --------
    # Commands
    # --------

    @command()
    @DebugIt()
    def Start(self):
        if self.get_state() == DevState.ON:
            t1 = threading.Thread(target=self.orm_run)
            t1.start()
            self.set_state(DevState.MOVING)
        else:
            raise ValueError("A scan is in already progress")


# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    """Main function of the ORM module."""
    return run((ORM,), args=args, **kwargs)


if __name__ == "__main__":
    main()
