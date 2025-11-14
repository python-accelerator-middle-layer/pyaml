#!/usr/bin/env python3
#
# EPICS IOC implemented with caproto, mirroring the Tango server:
# - QF1A_C01:Current (RW, A)
# - QD2A_C01:Current (RW, A)
# - Tune:H (RO)
# - Tune:V (RO)
# - Reset (WO: write 1 to reset; auto-returns to 0)
# - STATUS (string: status text similar to Tango set_status)
#
# Run:
#   python simple_epics_ioc_20251103.py --prefix SIMPLE: --list-pvs
#
# Example caput/caget:
#   caput SIMPLE:QF1A_C01:Current-SP 12.3
#   caget SIMPLE:QF1A_C01:Current-SP
#   caget SIMPLE:QF1A_C01:Current-RB
#   caget SIMPLE:Tune:H
#   caput SIMPLE:Reset 1
#

from caproto.server import PVGroup, pvproperty, ioc_arg_parser, run

INIT_QF1A = 0.0
INIT_QD2A = 0.0
INIT_TUNE_H = 0.21
INIT_TUNE_V = 0.42

class SimpleIOC(PVGroup):
    # ----------------- Status -----------------
    status = pvproperty(
        name="STATUS",
        value="SimpleIOC not started",
        dtype=str,
        doc="Status text analogous to Tango Device status."
    )

    # ----------------- QF1A currents -----------------
    qf1a_current_sp = pvproperty(
        name="QF1A_C01:Current-SP",
        value=INIT_QF1A,
        dtype=float,
        precision=4,
        units="A",
        doc="Setpoint for QF1A-C01 current (A). R/W",
    )

    qf1a_current_rb = pvproperty(
        name="QF1A_C01:Current-RB",
        value=INIT_QF1A,
        dtype=float,
        precision=4,
        units="A",
        read_only=True,
        doc="Readback for QF1A-C01 current (A). R/O",
    )

    # ----------------- QD2A currents -----------------
    qd2a_current_sp = pvproperty(
        name="QD2A_C01:Current-SP",
        value=INIT_QD2A,
        dtype=float,
        precision=4,
        units="A",
        doc="Setpoint for QD2A-C01 current (A). R/W",
    )

    qd2a_current_rb = pvproperty(
        name="QD2A_C01:Current-RB",
        value=INIT_QD2A,
        dtype=float,
        precision=4,
        units="A",
        read_only=True,
        doc="Readback for QD2A-C01 current (A). R/O",
    )

    # ----------------- Tunes (R/O) -----------------
    tune_h = pvproperty(
        name="Tune:H",
        value=INIT_TUNE_H,
        dtype=float,
        precision=5,
        read_only=True,
        doc="Read-only horizontal tune (matches Tango tune_h).",
    )

    tune_v = pvproperty(
        name="Tune:V",
        value=INIT_TUNE_V,
        dtype=float,
        precision=5,
        read_only=True,
        doc="Read-only vertical tune (matches Tango tune_v).",
    )

    # ----------------- Command -----------------
    reset = pvproperty(
        name="Reset",
        value=0,
        dtype=int,
        doc="Write 1 to reset all values to initial; auto-returns to 0.",
    )

    # ----------------- Lifecycle -----------------
    async def startup(self, async_lib):
        await self.status.write("SimpleIOC initialized")
        # Ensure initial values are explicit
        await self.qf1a_current_sp.write(INIT_QF1A)
        await self.qf1a_current_rb.write(INIT_QF1A)
        await self.qd2a_current_sp.write(INIT_QD2A)
        await self.qd2a_current_rb.write(INIT_QD2A)
        await self.tune_h.write(INIT_TUNE_H)
        await self.tune_v.write(INIT_TUNE_V)

    # ----------------- Putters -----------------
    @qf1a_current_sp.putter
    async def qf1a_current_sp(self, instance, value):
        fval = float(value)
        # Mirror SP to RB immediately (no slew). Swap for a ramp if desired.
        await self.qf1a_current_rb.write(fval)
        await self.status.write(f"QF1A setpoint updated to {fval} A")
        return fval

    @qd2a_current_sp.putter
    async def qd2a_current_sp(self, instance, value):
        fval = float(value)
        await self.qd2a_current_rb.write(fval)
        await self.status.write(f"QD2A setpoint updated to {fval} A")
        return fval

    @reset.putter
    async def reset(self, instance, value):
        val = int(value)
        if val == 1:
            # Reset both SP and RB to initial values
            await self.qf1a_current_sp.write(INIT_QF1A)
            await self.qf1a_current_rb.write(INIT_QF1A)
            await self.qd2a_current_sp.write(INIT_QD2A)
            await self.qd2a_current_rb.write(INIT_QD2A)
            await self.tune_h.write(INIT_TUNE_H)
            await self.tune_v.write(INIT_TUNE_V)
            await self.status.write("reset all to initial vals")
            await instance.write(0)  # pulse back to 0
        return val

if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="SIMPLE:",
        desc="Caproto IOC with SP/RB split for currents."
    )
    ioc = SimpleIOC(**ioc_options)
    run(ioc.pvdb, **run_options)
