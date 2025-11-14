from ophyd_async.epics.signal import epics_signal_r, epics_signal_w

from .types import (
    EpicsConfigRW, EpicsConfigR, EpicsConfigW, ControlSysConfig,
)
from .container import Readback, Setpoint

def get_SP_RB(
    cfg: ControlSysConfig
) -> tuple[Setpoint | None, Readback | None]:

    setpoint: Setpoint | None = None
    readback: Readback | None = None

    assert isinstance(cfg, (EpicsConfigRW, EpicsConfigR, EpicsConfigW))

    if isinstance(cfg, (EpicsConfigR, EpicsConfigRW)):
        r_sig = epics_signal_r(
            datatype=float,
            read_pv=cfg.read_pvname,
            name="",
        )
        readback = Readback(r_sig)

    if isinstance(cfg, (EpicsConfigW, EpicsConfigRW)):
        w_sig = epics_signal_w(
            datatype=float,
            write_pv=cfg.write_pvname,
            name="",
        )
        if isinstance(cfg, EpicsConfigRW):
            setpoint = Setpoint(w_sig, r_signal=readback._r_sig)
        else:
            setpoint = Setpoint(w_sig)

    return setpoint, readback