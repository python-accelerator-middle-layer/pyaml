#!/usr/bin/env python3
# simple_ds_20251103.py
import tango
from tango.server import Device, attribute, command, run

class SimpleDevice(Device):
    """
    """

    def init_device(self):
        super().init_device()

        # Set initial values
        self._qf1a_c01_current = 0.0
        self._qd2a_c01_current = 0.0
        self._tune_h = 0.21
        self._tune_v = 0.42
        self.set_state(tango.DevState.ON)
        self.set_status("SimpleDevice initialized")

    # --- Attributes --------------------------------------------------------
    @attribute(
        dtype=tango.DevDouble,
        access=tango.AttrWriteType.READ_WRITE,
        unit="A",
        label="QF1A-C01 Current",
        doc="Example R/W float attribute for QF1A-C01 current."
    )
    def qf1a_c01_current(self):
        """Attribute read callback"""
        return self._qf1a_c01_current

    @qf1a_c01_current.write
    def qf1a_c01_current(self, value):
        """Attribute write callback"""
        try:
            self._qf1a_c01_current = float(value)
            self.set_status(f"qf1a_c01_current updated to {self._qf1a_c01_current} A")
        except Exception as exc:
            # Map to a Tango exception on bad input
            raise tango.DevFailed(str(exc))

    @attribute(
        dtype=tango.DevDouble,
        access=tango.AttrWriteType.READ_WRITE,
        unit="A",
        label="QD2A-C01 Current",
        doc="Example R/W float attribute for QD2A-C01 current."
    )
    def qd2a_c01_current(self):
        """Attribute read callback"""
        return self._qd2a_c01_current

    @qd2a_c01_current.write
    def qd2a_c01_current(self, value):
        """Attribute write callback"""
        try:
            self._qd2a_c01_current = float(value)
            self.set_status(f"qd2a_c01_current updated to {self._qd2a_c01_current} A")
        except Exception as exc:
            # Map to a Tango exception on bad input
            raise tango.DevFailed(str(exc))

    @qd2a_c01_current.write
    def qd2a_c01_current(self, value):
        """Attribute write callback"""
        try:
            self._qd2a_c01_current = float(value)
            self.set_status(f"qd2a_c01_current updated to {self._qd2a_c01_current} A")
        except Exception as exc:
            # Map to a Tango exception on bad input
            raise tango.DevFailed(str(exc))

    @attribute(
        dtype=tango.DevDouble,
        access=tango.AttrWriteType.READ,
        label="Horizontal Tune",
        doc="Example read-only attribute (tune_h)"
    )
    def tune_h(self):
        """Read callback for tune_h"""
        # You can compute or return a stored value
        return self._tune_h

    @attribute(
        dtype=tango.DevDouble,
        access=tango.AttrWriteType.READ,
        label="Vertical Tune",
        doc="Example read-only attribute (tune_v)"
    )
    def tune_v(self):
        """Read callback for tune_v"""
        # You can compute or return a stored value
        return self._tune_v

    # --- Commands ----------------------------------------------------------
    @command(dtype_in=None, dtype_out=None, doc_out="Reset all to initial vals")
    def Reset(self):
        self._qf1a_c01_current = 0.0
        self._tune_h = 0.21
        self._tune_v = 0.42
        self.set_status("reset all to initial vals")

if __name__ == "__main__":
    # Run as: `python simple_ds_20251103.py instance1`
    run((SimpleDevice,))
