from pyaml.pyaml import pyaml
from pyaml.configuration import set_root_folder
set_root_folder("tests/config")

sr = pyaml("sr.yaml")

sr.HCORR.strength.set([0.000010,0.000020])
