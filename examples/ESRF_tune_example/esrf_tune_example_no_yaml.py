from pyaml.instrument import Instrument,ConfigModel as InstrumentConfigModel
from pyaml.magnet.quadrupole import Quadrupole,ConfigModel as QuadrupoleConfig
from pyaml.configuration.csvcurve import CSVCurve,ConfigModel as CSVCureveConfig
from pyaml.magnet.linear_model import LinearMagnetModel,ConfigModel as LinearMagnetModelConfig
from pyaml.lattice.simulator import Simulator,ConfigModel as SimulatorConfigModel
from pyaml.arrays.magnet import Magnet,ConfigModel as MagnetArrayConfigModel
from tango.pyaml.controlsystem import TangoControlSystem,ConfigModel as ControlSystemConfig
from tango.pyaml.attribute import Attribute,ConfigModel as AttributeConfig
from tango.pyaml.attribute_read_only import AttributeReadOnly,ConfigModel as AttributeReadOnlyConfig


import numpy as np
import time

# Configuration

tangocs = ControlSystemConfig(name="live",tango_host="ebs-simu-3:10000")
control = TangoControlSystem(tangocs)
control.init_cs()

qfCurve = CSVCurve(CSVCureveConfig(file="config/sr/magnet_models/QF1_strength.csv"))
qdCurve = CSVCurve(CSVCureveConfig(file="config/sr/magnet_models/QD2_strength.csv"))

elemConfig = [ {"name":"QF1A-C01", "attname":"srmag/vps-qf1/c01-a/current", "calibration_factor":1.00504, "curve":qfCurve},
               {"name":"QF1E-C01", "attname":"srmag/vps-qf1/c01-e/current", "calibration_factor":0.998212, "curve":qfCurve},
               {"name":"QD2A-C01", "attname":"srmag/vps-qd2/c01-a/current", "calibration_factor":1.00504,  "curve":qdCurve},
               {"name":"QD2E-C01", "attname":"srmag/vps-qd2/c01-e/current", "calibration_factor":1.003485189, "curve":qdCurve} ]
  
devices=[]
names=[]
for cfg in elemConfig:
    qAtt = Attribute(AttributeConfig(attribute=cfg["attname"],unit="A"))
    qModel = LinearMagnetModel(LinearMagnetModelConfig(curve=cfg["curve"],calibration_factor=cfg["calibration_factor"],powerconverter=qAtt,unit="1/m"))
    devices.append( Quadrupole(QuadrupoleConfig(name=cfg["name"],model=qModel)) )
    names.append(cfg["name"])


simulator = Simulator(SimulatorConfigModel(name="design",lattice="config/sr/lattices/ebs.mat"))

quads = Magnet(MagnetArrayConfigModel(name="quadsForTune",elements=names))

sr = Instrument(InstrumentConfigModel(name="sr",energy=6e9,controls=[control],simulators=[simulator],devices=devices,arrays=[quads],data_folder="/tmp"))



# Usage exmaple

quadForTuneDesign = sr.design.get_magnets("quadsForTune")
quadForTuneLive = sr.live.get_magnets("quadsForTune")

# Compute tune response matrix for the 4 quads from simulator
sr.design.get_lattice().disable_6d()
tune = sr.design.get_lattice().get_tune()
tunemat = np.zeros((len(quadForTuneDesign),2))
for idx,m in enumerate(quadForTuneDesign):
    str = m.strength.get()
    m.strength.set(str+1e-4)
    dq = sr.design.get_lattice().get_tune() - tune
    tunemat[idx] = dq*1e4
    m.strength.set(str)

# Compute correction matrix
correctionmat = np.linalg.pinv(tunemat.T)

# Correct tune on live
qxAtt = AttributeReadOnly(AttributeReadOnlyConfig(attribute="sys/ringsimulator/ebs/Tune_h",unit=""))
qyAtt = AttributeReadOnly(AttributeReadOnlyConfig(attribute="sys/ringsimulator/ebs/Tune_v",unit=""))

print(f"Tune={qxAtt.readback()}, {qyAtt.readback()}")

strs = quadForTuneLive.strengths.get()
strs += np.matmul(correctionmat,[0.1,0.05]) # Ask for correction [dqx,dqy]
quadForTuneLive.strengths.set(strs)
time.sleep(3)
print(f"Tune={qxAtt.readback()}, {qyAtt.readback()}")

        
