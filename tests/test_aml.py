from pyaml.pyaml import pyaml,PyAML
from pyaml.instrument import Instrument
from pyaml.configuration import set_root_folder
import pyaml as pyaml_pkg
from pyaml.lattice.simulator import MagnetType

#def test_aml(config_root_dir):
set_root_folder("tests/config")

ml:PyAML = pyaml("sr.yaml")
sr:Instrument = ml.get('sr')
sr.design.get_magnet(MagnetType.HCORRECTOR,"SH1-C01A-H").strength.set(0.000010)

#sr.model.HCORR.strength.set([0.000010,0.000020])
#sr.model.VCORR.strength.set([-0.000015,0.000002])
#pyaml_pkg.configuration.factory._ALL_ELEMENTS.clear()
