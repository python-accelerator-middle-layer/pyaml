from pyaml.pyaml import pyaml,PyAML
from pyaml.configuration.factory import Factory
from pyaml.instrument import Instrument
from pyaml.magnet.model import MagnetModel
import numpy as np

def test_arrays():

    ml:PyAML = pyaml("tests/config/sr.yaml")
    sr:Instrument = ml.get('sr')
    sr.design.get_lattice().disable_6d()
    sr.design.get_magnet("SH1A-C01-H").strength.set(0.000010)
    sr.design.get_magnet("SH1A-C01-V").strength.set(0.000015)

    o,_ = sr.design.get_lattice().find_orbit()
    assert(np.abs(o[0] + 9.91848416e-05)<1e-10)
    assert(np.abs(o[1] + 3.54829761e-07)<1e-10)
    assert(np.abs(o[2] + 1.56246320e-06)<1e-10)
    assert(np.abs(o[3] + 1.75037311e-05)<1e-10)

    sr.design.get_magnet("SH1A-C02-H").strength.set(-0.000008)
    sr.design.get_magnet("SH1A-C02-V").strength.set(-0.000017)

    o,_ = sr.design.get_lattice().find_orbit()
    assert(np.abs(o[0] + 1.60277642e-04)<1e-10)
    assert(np.abs(o[1] - 2.36103795e-06)<1e-10)
    assert(np.abs(o[2] - 3.62843295e-05)<1e-10)
    assert(np.abs(o[3] + 6.06571010e-06)<1e-10)

    sr.design.get_magnets("HCORR").strengths.set([0.000010,-0.000008])
    sr.design.get_magnets("VCORR").strengths.set([0.000015,-0.000017])

    o,_ = sr.design.get_lattice().find_orbit()
    assert(np.abs(o[0] + 1.60277642e-04)<1e-10)
    assert(np.abs(o[1] - 2.36103795e-06)<1e-10)
    assert(np.abs(o[2] - 3.62843295e-05)<1e-10)
    assert(np.abs(o[3] + 6.06571010e-06)<1e-10)

    Factory.clear()