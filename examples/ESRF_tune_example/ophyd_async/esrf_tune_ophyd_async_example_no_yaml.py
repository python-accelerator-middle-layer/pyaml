CS_NAME = "tango"
# CS_NAME = "epics"

if CS_NAME == "tango":
    import os
    os.environ['TANGO_HOST'] = '127.0.0.1:10000'

import time

import numpy as np

from pyaml.configuration import set_root_folder
from pyaml.control.signal import arun
from pyaml.instrument import Instrument, ConfigModel as InstrumentConfigModel
from pyaml.magnet.quadrupole import Quadrupole, ConfigModel as QuadrupoleConfig
from pyaml.configuration.csvcurve import CSVCurve, ConfigModel as CSVCureveConfig
from pyaml.magnet.linear_model import (
    LinearMagnetModel,
    ConfigModel as LinearMagnetModelConfig,
)
from pyaml.lattice.simulator import Simulator, ConfigModel as SimulatorConfigModel
from pyaml.arrays.magnet import Magnet, ConfigModel as MagnetArrayConfigModel

from pyaml.control.controlsystem import (
    OphydAsyncCompatibleControlSystem,
    OphydAsyncCompatibleControlSystemConfig,
)
from pyaml.control.signal.core import (
    FloatSignalContainer, ConfigModel as FloatSignalContainerConfig)

if CS_NAME == "tango":
    from pyaml.control.signal.core import TangoConfigRW, TangoConfigR
elif CS_NAME == "epics":
    from pyaml.control.signal.core import EpicsConfigRW, EpicsConfigR
else:
    raise ValueError(f"Unsupported CS_NAME: {CS_NAME}")

# Configuration

set_root_folder("../../../tests")

qfCurve = CSVCurve(CSVCureveConfig(file="config/sr/magnet_models/QF1_strength.csv"))
qdCurve = CSVCurve(CSVCureveConfig(file="config/sr/magnet_models/QD2_strength.csv"))

if CS_NAME == "tango":
    elemConfig = [
        {
            "name": "QF1A-C01",
            "attname": "test/simple/1/qf1a_c01_current",
            "calibration_factor": 1.00504,
            "curve": qfCurve,
        },
        {
            "name": "QD2A-C01",
            "attname": "test/simple/1/qd2a_c01_current",
            "calibration_factor": 1.00504,
            "curve": qdCurve,
        },
    ]
elif CS_NAME == "epics":
    elemConfig = [
        {
            "name": "QF1A-C01",
            "setpoint_pvname": "SIMPLE:QF1A_C01:Current-SP",
            "readback_pvname": "SIMPLE:QF1A_C01:Current-RB",
            "calibration_factor": 1.00504,
            "curve": qfCurve,
        },
        {
            "name": "QD2A-C01",
            "setpoint_pvname": "SIMPLE:QD2A_C01:Current-SP",
            "readback_pvname": "SIMPLE:QD2A_C01:Current-RB",
            "calibration_factor": 1.00504,
            "curve": qdCurve,
        },
    ]
else:
    raise ValueError(f"Unsupported CS_NAME: {CS_NAME}")

devices = []
names = []
for cfg in elemConfig:
    if CS_NAME == "tango":
        cs_config=TangoConfigRW(read_attr=cfg["attname"],
                                write_attr=cfg["attname"])
    elif CS_NAME == "epics":
        cs_config = EpicsConfigRW(read_pvname=cfg["readback_pvname"],
                                  write_pvname=cfg["setpoint_pvname"])
    else:
        raise ValueError(f"Unsupported CS_NAME: {CS_NAME}")

    qAtt_cfg = FloatSignalContainerConfig(cs_config=cs_config, unit="A")
    qAtt = FloatSignalContainer(qAtt_cfg)
    qModel = LinearMagnetModel(
        LinearMagnetModelConfig(
            curve=cfg["curve"],
            calibration_factor=cfg["calibration_factor"],
            powerconverter=qAtt,
            unit="1/m",
        )
    )
    devices.append(Quadrupole(QuadrupoleConfig(name=cfg["name"], model=qModel)))
    names.append(cfg["name"])

simulator = Simulator(
    SimulatorConfigModel(name="design", lattice="config/sr/lattices/ebs.mat")
)

quads = Magnet(MagnetArrayConfigModel(name="quadsForTune", elements=names))

control = OphydAsyncCompatibleControlSystem(
    OphydAsyncCompatibleControlSystemConfig(name="live")
)

sr = Instrument(
    InstrumentConfigModel(
        name="sr",
        energy=6e9,
        controls=[control],
        simulators=[simulator],
        devices=devices,
        arrays=[quads],
        data_folder="/tmp",
    )
)

c_m = control.get_magnet("QF1A-C01")

print(c_m.hardware.get())

c_m.hardware.set(10.1)

print(c_m.hardware.get())
print(c_m.strength.get())

RB = c_m.hardware._RWHardwareScalar__model._LinearMagnetModel__ps.RB
SP = c_m.hardware._RWHardwareScalar__model._LinearMagnetModel__ps.SP

print(arun(RB.async_get()))
print(arun(SP.async_get()))

print(RB.get())
print(SP.get())

# Usage exmaple

quadForTuneDesign = sr.design.get_magnets("quadsForTune")
quadForTuneLive = sr.live.get_magnets("quadsForTune")

# Compute tune response matrix for the 4 quads from simulator
sr.design.get_lattice().disable_6d()
tune = sr.design.get_lattice().get_tune()
tunemat = np.zeros((len(quadForTuneDesign), 2))
for idx, m in enumerate(quadForTuneDesign):
    str = m.strength.get()
    m.strength.set(str + 1e-4)
    dq = sr.design.get_lattice().get_tune() - tune
    tunemat[idx] = dq * 1e4
    m.strength.set(str)

# Compute correction matrix
correctionmat = np.linalg.pinv(tunemat.T)

# Correct tune on live
qAtt_cfg = {}
if CS_NAME == "tango":
    for xy, hv in [('x', 'h'), ('y', 'v')]:
        qAtt_cfg[xy] = FloatSignalContainerConfig(
            cs_config=TangoConfigR(read_attr=f"test/simple/1/tune_{hv}"),
            unit="",
        )
elif CS_NAME == "epics":
    for xy, hv in [('x', 'h'), ('y', 'v')]:
        qAtt_cfg[xy] = FloatSignalContainerConfig(
            cs_config=EpicsConfigR(read_pvname=f"SIMPLE:Tune:{hv.upper()}"),
            unit="",
        )
else:
    raise ValueError(f"Unsupported CS_NAME: {CS_NAME}")

qxAtt = FloatSignalContainer(qAtt_cfg['x'])
qyAtt = FloatSignalContainer(qAtt_cfg['y'])

print(f"Tune-X={qxAtt.readback()}, {qxAtt.RB.get()}")
print(f"Tune-Y={qyAtt.readback()}, {qyAtt.RB.get()}")

strs = quadForTuneLive.strengths.get()
strs += np.matmul(correctionmat, [0.1, 0.05])  # Ask for correction [dqx,dqy]
quadForTuneLive.strengths.set(strs)
time.sleep(3)

print(f"Tune-X={qxAtt.readback()}, {qxAtt.RB.get()}")
print(f"Tune-Y={qyAtt.readback()}, {qyAtt.RB.get()}")

