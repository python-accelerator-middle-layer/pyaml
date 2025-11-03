from pyaml.pyaml import pyaml,PyAML
from pyaml.configuration.factory import Factory
from pyaml.instrument import Instrument
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.arrays.bpm_array import BPMArray
import importlib

import numpy as np
import pytest

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango-pyaml",
    "path": "tests/dummy_cs/tango-pyaml"
}], indirect=True)
def test_arrays(install_test_package):

    ml:PyAML = pyaml("tests/config/sr.yaml")
    sr:Instrument = ml.get('sr')
    sr.design.get_lattice().disable_6d()

    # Test on model

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

    # Test on control system

    # Assert that the virtual magnet share the same model
    assert( sr.live.get_magnet("SH1A-C01-H").model == sr.live.get_magnet("SH1A-C01-V").model )
    assert( sr.live.get_magnet("SH1A-C02-H").model == sr.live.get_magnet("SH1A-C02-V").model )

    # Using aggregators
    sr.live.get_magnets("HCORR").strengths.set([0.000010,-0.000008])    
    ps1 = sr.live.get_magnet("SH1A-C01-H").model.read_hardware_values()
    ps2 = sr.live.get_magnet("SH1A-C02-H").model.read_hardware_values()
    assert(np.abs(ps1[0] - 0.02956737880874648)<1e-10)
    assert(np.abs(ps1[1] - 0)<1e-10)
    assert(np.abs(ps1[2] - 0)<1e-10)
    assert(np.abs(ps2[0] + 0.02365390304699716)<1e-10)
    assert(np.abs(ps2[1] - 0)<1e-10)
    assert(np.abs(ps2[2] - 0)<1e-10)
    sr.live.get_magnets("VCORR").strengths.set([0.000015,-0.000017])
    ps1 = sr.live.get_magnet("SH1A-C01-H").model.read_hardware_values()
    ps2 = sr.live.get_magnet("SH1A-C02-H").model.read_hardware_values()
    assert(np.abs(ps1[0] - 0.02956737880874648)<1e-10)
    assert(np.abs(ps1[1] + 0.058240333933172066)<1e-10)
    assert(np.abs(ps1[2] - 0.05601656539392866)<1e-10)
    assert(np.abs(ps2[0] + 0.02365390304699716)<1e-10)
    assert(np.abs(ps2[1] - 0.06600571179092833)<1e-10)
    assert(np.abs(ps2[2] + 0.0634854407797858)<1e-10)

    strHV = sr.live.get_magnets("HVCORR").strengths.get()
    assert(np.abs(strHV[0] - 0.000010)<1e-10)
    assert(np.abs(strHV[1] + 0.000008)<1e-10)
    assert(np.abs(strHV[2] - 0.000015)<1e-10)
    assert(np.abs(strHV[3] + 0.000017)<1e-10)

    # Reset to 0
    ma = importlib.import_module("tango.pyaml.multi_attribute")
    ma.LAST_NB_WRITTEN = 0 # Total number of setpoints done by multi_attribute
    sr.live.get_magnets("HVCORR").strengths.set(0.)
    assert(ma.LAST_NB_WRITTEN == 6) # 6 power supply setpoints are needed
    ps1 = sr.live.get_magnet("SH1A-C01-H").model.read_hardware_values()
    ps2 = sr.live.get_magnet("SH1A-C02-H").model.read_hardware_values()
    assert(np.abs(ps1[0])<1e-10)
    assert(np.abs(ps1[1])<1e-10)
    assert(np.abs(ps1[2])<1e-10)
    assert(np.abs(ps2[0])<1e-10)
    assert(np.abs(ps2[1])<1e-10)
    assert(np.abs(ps2[2])<1e-10)

    # Check that the behavior is the same without aggregator
    mags = []
    for m in  sr.live.get_magnets("HVCORR"):
        mags.append(m)
    array = MagnetArray("HVCOOR_noagg",mags) # holder = None, no aggregator
    array.strengths.set([0.000010,-0.000008,0.000015,-0.000017])
    ps1 = sr.live.get_magnet("SH1A-C01-H").model.read_hardware_values()
    ps2 = sr.live.get_magnet("SH1A-C02-H").model.read_hardware_values()
    assert(np.abs(ps1[0] - 0.02956737880874648)<1e-10)
    assert(np.abs(ps1[1] + 0.058240333933172066)<1e-10)
    assert(np.abs(ps1[2] - 0.05601656539392866)<1e-10)
    assert(np.abs(ps2[0] + 0.02365390304699716)<1e-10)
    assert(np.abs(ps2[1] - 0.06600571179092833)<1e-10)
    assert(np.abs(ps2[2] + 0.0634854407797858)<1e-10)


    # Test BPMs array

    # Using aggragtor
    pos = sr.design.get_bpms("BPMS").positions.get()
    assert(np.abs(pos[0][0] + 7.21154171490481e-05)<1e-10)
    assert(np.abs(pos[0][1] - 3.3988843436571406e-05)<1e-10)
    assert(np.abs(pos[1][0] - 1.1681211772781844e-04)<1e-10)
    assert(np.abs(pos[1][1] - 7.072972488250373e-06)<1e-10)

    # No aggregator
    bpms = []
    for b in sr.design.get_bpms("BPMS"):
        bpms.append(b)

    bpms = BPMArray("BPM_noagg",bpms) # holder = None, no aggregator
    pos = bpms.positions.get()
    assert(np.abs(pos[0][0] + 7.21154171490481e-05)<1e-10)
    assert(np.abs(pos[0][1] - 3.3988843436571406e-05)<1e-10)
    assert(np.abs(pos[1][0] - 1.1681211772781844e-04)<1e-10)
    assert(np.abs(pos[1][1] - 7.072972488250373e-06)<1e-10)

    Factory.clear()


