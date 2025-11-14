from ophyd_async.tango.core import tango_signal_r, tango_signal_w

from .types import (
    TangoConfigRW, TangoConfigR, TangoConfigW, ControlSysConfig,
)
from .container import Readback, Setpoint

def get_SP_RB(
    cfg: ControlSysConfig
) -> tuple[Setpoint | None, Readback | None]:

    setpoint: Setpoint | None = None
    readback: Readback | None = None

    assert isinstance(cfg, (TangoConfigRW, TangoConfigR, TangoConfigW))

    if isinstance(cfg, (TangoConfigR, TangoConfigRW)):
        r_sig = tango_signal_r(
            datatype=float,
            read_trl=cfg.read_attr,
            name="",
        )
        readback = Readback(r_sig)

    if isinstance(cfg, (TangoConfigW, TangoConfigRW)):
        w_sig = tango_signal_w(
            datatype=float,
            write_trl=cfg.write_attr,
            name="",
        )
        if isinstance(cfg, TangoConfigRW):
            setpoint = Setpoint(w_sig, r_signal=readback._r_sig)
        else:
            setpoint = Setpoint(w_sig)


    return setpoint, readback