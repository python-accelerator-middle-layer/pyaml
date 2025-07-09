from pyaml.pyaml import pyaml
from pyaml.configuration import set_root_folder
set_root_folder("tests/config")

sr = pyaml("sr.yaml")

sr.model.HCORR.strength.set([0.000010,0.000020])
sr.model.VCORR.strength.set([-0.000015,0.000002])
