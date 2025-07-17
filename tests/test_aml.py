from pyaml.pyaml import pyaml
from pyaml.configuration import set_root_folder
import pyaml as pyaml_pkg

def test_aml(config_root_dir):
    set_root_folder(config_root_dir)

    sr = pyaml("sr.yaml")

    sr.model.HCORR.strength.set([0.000010,0.000020])
    sr.model.VCORR.strength.set([-0.000015,0.000002])
    pyaml_pkg.configuration.factory._ALL_ELEMENTS.clear()
