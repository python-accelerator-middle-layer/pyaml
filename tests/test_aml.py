from pyaml.pyaml import pyaml,PyAML
from pyaml.instrument import Instrument
from pyaml.configuration import set_root_folder
import pyaml as pyaml_pkg
from pyaml.lattice.element_holder import MagnetType
import at

#def test_aml(config_root_dir):
set_root_folder("tests/config")

ml:PyAML = pyaml("sr.yaml")
sr:Instrument = ml.get('sr')
sr.design.get_lattice().disable_6d()
sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").strength.set(0.000010)
pcurrent = sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").current.get()
print(pcurrent)
rcurrents = sr.design.get_magnet(MagnetType.COMBINED,"SH1A-C01").unitconv.compute_currents([0.000010,0,0])
print(rcurrents)
print(sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").strength.unit())
print(sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1A-C01-H").current.unit())

o,_ = sr.design.get_lattice().find_orbit()
print(o)

#pyaml.configuration.factory._ALL_ELEMENTS.clear()
