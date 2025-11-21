import os
import time

import numpy as np
from pyaml.instrument import ConfigModel as InstrumentConfigModel
from pyaml.instrument import Instrument
from tango.pyaml.attribute import Attribute
from tango.pyaml.attribute import ConfigModel as AttributeConfig
from tango.pyaml.attribute_read_only import (
    AttributeReadOnly,
)
from tango.pyaml.attribute_read_only import (
    ConfigModel as AttributeReadOnlyConfig,
)
from tango.pyaml.controlsystem import (
    ConfigModel as ControlSystemConfig,
)
from tango.pyaml.controlsystem import (
    TangoControlSystem,
)

from pyaml.arrays.magnet import ConfigModel as MagnetArrayConfigModel
from pyaml.arrays.magnet import Magnet
from pyaml.configuration import set_root_folder
from pyaml.configuration.csvcurve import ConfigModel as CSVCureveConfig
from pyaml.configuration.csvcurve import CSVCurve
from pyaml.lattice.simulator import ConfigModel as SimulatorConfigModel
from pyaml.lattice.simulator import Simulator
from pyaml.magnet.linear_model import (
    ConfigModel as LinearMagnetModelConfig,
)
from pyaml.magnet.linear_model import (
    LinearMagnetModel,
)
from pyaml.magnet.quadrupole import ConfigModel as QuadrupoleConfig
from pyaml.magnet.quadrupole import Quadrupole

# Get the directory of the current script
script_dir = os.path.dirname(__file__)

# Go up one level and then into 'data'
relative_path = os.path.join(script_dir, "..", "..", "tests")

# Normalize the path (resolves '..')
absolute_path = os.path.abspath(relative_path)

set_root_folder(absolute_path)

# Configuration

tangocs = ControlSystemConfig(name="live", tango_host="ebs-simu-3:10000")
control = TangoControlSystem(tangocs)
control.init_cs()

qfCurve = CSVCurve(CSVCureveConfig(file="config/sr/magnet_models/QF1_strength.csv"))
qdCurve = CSVCurve(CSVCureveConfig(file="config/sr/magnet_models/QD2_strength.csv"))

elemConfig = [
    {
        "name": "QF1A-C01",
        "attname": "srmag/vps-qf1/c01-a/current",
        "calibration_factor": 1.00504,
        "curve": qfCurve,
    },
    {
        "name": "QF1E-C01",
        "attname": "srmag/vps-qf1/c01-e/current",
        "calibration_factor": 0.998212,
        "curve": qfCurve,
    },
    {
        "name": "QD2A-C01",
        "attname": "srmag/vps-qd2/c01-a/current",
        "calibration_factor": 1.00504,
        "curve": qdCurve,
    },
    {
        "name": "QD2E-C01",
        "attname": "srmag/vps-qd2/c01-e/current",
        "calibration_factor": 1.003485189,
        "curve": qdCurve,
    },
]

devices = []
names = []
for cfg in elemConfig:
    qAtt = Attribute(AttributeConfig(attribute=cfg["attname"], unit="A"))
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
qxAtt = AttributeReadOnly(
    AttributeReadOnlyConfig(attribute="sys/ringsimulator/ebs/Tune_h", unit="")
)
qyAtt = AttributeReadOnly(
    AttributeReadOnlyConfig(attribute="sys/ringsimulator/ebs/Tune_v", unit="")
)

print(f"Tune={qxAtt.readback()}, {qyAtt.readback()}")

strs = quadForTuneLive.strengths.get()
strs += np.matmul(correctionmat, [0.1, 0.05])  # Ask for correction [dqx,dqy]
quadForTuneLive.strengths.set(strs)
time.sleep(3)
print(f"Tune={qxAtt.readback()}, {qyAtt.readback()}")
