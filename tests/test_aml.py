from pyaml.pyaml import pyaml,PyAML
from pyaml.instrument import Instrument
from pyaml.configuration import set_root_folder
import pyaml as pyaml_pkg
from pyaml.lattice.element_holder import MagnetType
from pyaml.magnet.model import MagnetModel
import at

#def test_aml(config_root_dir):
set_root_folder("tests/config")

ml:PyAML = pyaml("sr.yaml")
sr:Instrument = ml.get('sr')
sr.design.get_lattice().disable_6d()
sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").strength.set(0.000010)
o,_ = sr.design.get_lattice().find_orbit()
print(o)

pcurrent = sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").hardware.get()
print(pcurrent)
model:MagnetModel = sr.design.get_magnet(MagnetType.COMBINED,"SH1A-C01").model
rcurrents = model.compute_hardware_values([0.000010,0,0])
print(rcurrents)
print(sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").strength.unit())
print(sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").hardware.unit())

sr.design.get_magnets("HCORR").strengths.set([0.000010,-0.000010])
o,_ = sr.design.get_lattice().find_orbit()
print(o)



#pyaml.configuration.factory._ALL_ELEMENTS.clear()
