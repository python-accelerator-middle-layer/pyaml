import importlib

import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.arrays.bpm import BPM
from pyaml.arrays.bpm_array import BPMArray
from pyaml.arrays.cfm_magnet import CombinedFunctionMagnet
from pyaml.arrays.element_array import ElementArray
from pyaml.arrays.magnet import Magnet
from pyaml.arrays.magnet_array import MagnetArray


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_arrays(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    # Test on model

    sr.design.magnet.get("SH1A-C01-H").strength.set(0.000010)
    sr.design.magnet.get("SH1A-C01-V").strength.set(0.000015)

    o, _ = sr.design.get_lattice().find_orbit()
    assert np.abs(o[0] - 9.90267693e-05) < 1e-10
    assert np.abs(o[1] - 3.39661431e-07) < 1e-10
    assert np.abs(o[2] + 1.59928207e-06) < 1e-10
    assert np.abs(o[3] + 1.74771216e-05) < 1e-10

    sr.design.magnet.get("SH1A-C02-H").strength.set(-0.000008)
    sr.design.magnet.get("SH1A-C02-V").strength.set(-0.000017)

    o, _ = sr.design.get_lattice().find_orbit()
    assert np.abs(o[0] - 1.60555804e-04) < 1e-10
    assert np.abs(o[1] + 2.37234366e-06) < 1e-10
    assert np.abs(o[2] - 3.62695844e-05) < 1e-10
    assert np.abs(o[3] + 5.97692290e-06) < 1e-10

    sr.design.magnets.get("HCORR").strengths.set([0.000010, -0.000008])
    sr.design.magnets.get("VCORR").strengths.set([0.000015, -0.000017])

    o, _ = sr.design.get_lattice().find_orbit()
    assert np.abs(o[0] - 1.60555804e-04) < 1e-10
    assert np.abs(o[1] + 2.37234366e-06) < 1e-10
    assert np.abs(o[2] - 3.62695844e-05) < 1e-10
    assert np.abs(o[3] + 5.97692290e-06) < 1e-10

    p0 = o[0]

    # Test kick angle (small angle, no change from above)
    sr.design.magnet.get("SH1A-C02-H").angle.set(-0.000008)
    o, _ = sr.design.get_lattice().find_orbit()
    assert np.abs(o[0] - 1.60555804e-04) < 1e-10
    assert np.abs(o[1] + 2.37234366e-06) < 1e-10
    assert np.abs(o[2] - 3.62695844e-05) < 1e-10
    assert np.abs(o[3] + 5.97692290e-06) < 1e-10

    p1 = o[0]
    # Diff between small angle approximation and angle
    assert np.abs(p0 - p1) - 1.3504822260479443e-15 < 1e-20

    # Test on control system

    # Assert that the virtual magnet share the same model
    assert sr.live.magnet.get("SH1A-C01-H").model == sr.live.magnet.get("SH1A-C01-V").model
    assert sr.live.magnet.get("SH1A-C02-H").model == sr.live.magnet.get("SH1A-C02-V").model

    # Using aggregators
    sr.live.magnets.get("HCORR").strengths.set([0.000010, -0.000008])
    ps1 = sr.live.combined_function_magnet.get("SH1A-C01").hardwares.get()
    ps2 = sr.live.combined_function_magnet.get("SH1A-C02").hardwares.get()
    assert np.abs(ps1[0] - 0.02956737880874648) < 1e-10
    assert np.abs(ps1[1] - 0) < 1e-10
    assert np.abs(ps1[2] - 0) < 1e-10
    assert np.abs(ps2[0] + 0.02365390304699716) < 1e-10
    assert np.abs(ps2[1] - 0) < 1e-10
    assert np.abs(ps2[2] - 0) < 1e-10
    sr.live.magnets.get("VCORR").strengths.set([0.000015, -0.000017])
    ps1 = sr.live.combined_function_magnet.get("SH1A-C01").hardwares.get()
    ps2 = sr.live.combined_function_magnet.get("SH1A-C02").hardwares.get()
    assert np.abs(ps1[0] - 0.02956737880874648) < 1e-10
    assert np.abs(ps1[1] + 0.058240333933172066) < 1e-10
    assert np.abs(ps1[2] - 0.05601656539392866) < 1e-10
    assert np.abs(ps2[0] + 0.02365390304699716) < 1e-10
    assert np.abs(ps2[1] - 0.06600571179092833) < 1e-10
    assert np.abs(ps2[2] + 0.0634854407797858) < 1e-10

    strHV = sr.live.magnets.get("HVCORR").strengths.get()
    assert np.abs(strHV[0] - 0.000010) < 1e-10
    assert np.abs(strHV[1] + 0.000008) < 1e-10
    assert np.abs(strHV[2] - 0.000015) < 1e-10
    assert np.abs(strHV[3] + 0.000017) < 1e-10

    # Reset to 0
    ma = importlib.import_module("tango.pyaml.multi_attribute")
    ma.LAST_NB_WRITTEN = 0  # Total number of setpoints done by multi_attribute
    sr.live.magnets.get("HVCORR").strengths.set(0.0)
    assert ma.LAST_NB_WRITTEN == 6  # 6 power supply setpoints are needed
    ps1 = sr.live.combined_function_magnet.get("SH1A-C01").hardwares.get()
    ps2 = sr.live.combined_function_magnet.get("SH1A-C02").hardwares.get()
    assert np.abs(ps1[0]) < 1e-10
    assert np.abs(ps1[1]) < 1e-10
    assert np.abs(ps1[2]) < 1e-10
    assert np.abs(ps2[0]) < 1e-10
    assert np.abs(ps2[1]) < 1e-10
    assert np.abs(ps2[2]) < 1e-10

    # Check that the behavior is the same without aggregator
    mags = []
    for m in sr.live.magnets.get("HVCORR"):
        mags.append(m)
    array = MagnetArray("HVCOOR_noagg", mags, use_aggregator=False)
    array.strengths.set([0.000010, -0.000008, 0.000015, -0.000017])
    ps1 = sr.live.combined_function_magnet.get("SH1A-C01").hardwares.get()
    ps2 = sr.live.combined_function_magnet.get("SH1A-C02").hardwares.get()
    assert np.abs(ps1[0] - 0.02956737880874648) < 1e-10
    assert np.abs(ps1[1] + 0.058240333933172066) < 1e-10
    assert np.abs(ps1[2] - 0.05601656539392866) < 1e-10
    assert np.abs(ps2[0] + 0.02365390304699716) < 1e-10
    assert np.abs(ps2[1] - 0.06600571179092833) < 1e-10
    assert np.abs(ps2[2] + 0.0634854407797858) < 1e-10

    # Test BPMs array

    # Using aggregator
    pos = sr.design.bpms.get("BPMS").positions.get()
    assert np.abs(pos[0][0] - 7.22262850488348e-05) < 1e-10
    assert np.abs(pos[0][1] - 3.4291613955705856e-05) < 1e-10
    assert np.abs(pos[1][0] + 1.1696152238807462e-04) < 1e-10
    assert np.abs(pos[1][1] - 7.4265634524358045e-06) < 1e-10

    # Using aggregator (h and v)
    pos_h = sr.design.bpms.get("BPMS").h.get()
    pos_v = sr.design.bpms.get("BPMS").v.get()
    assert np.all(np.isclose(pos[:, 0], pos_h, rtol=1e-15, atol=1e-15))
    assert np.all(np.isclose(pos[:, 1], pos_v, rtol=1e-15, atol=1e-15))

    # Test BPM transformation matrices
    sr.design.bpm.get("BPM_C04-01").offset.set([0.1, 0.2])
    sr.design.bpm.get("BPM_C04-02").offset.set([0.3, 0.4])
    pos = sr.design.bpms.get("BPMS").positions.get()
    assert np.abs(pos[0][0] - 7.22262850488348e-05 - 0.1) < 1e-10
    assert np.abs(pos[0][1] - 3.4291613955705856e-05 - 0.2) < 1e-10
    assert np.abs(pos[1][0] + 1.1696152238807462e-04 - 0.3) < 1e-10
    assert np.abs(pos[1][1] - 7.4265634524358045e-06 - 0.4) < 1e-10
    sr.design.bpm.get("BPM_C04-01").offset.set([0.0, 0.0])
    sr.design.bpm.get("BPM_C04-02").offset.set([0.0, 0.0])

    # No aggregator
    bpms = []
    for b in sr.design.bpms.get("BPMS"):
        bpms.append(b)

    bpms = BPMArray("BPM_noagg", bpms, use_aggregator=False)
    pos = bpms.positions.get()
    assert np.abs(pos[0][0] - 7.22262850488348e-05) < 1e-10
    assert np.abs(pos[0][1] - 3.4291613955705856e-05) < 1e-10
    assert np.abs(pos[1][0] + 1.1696152238807462e-04) < 1e-10
    assert np.abs(pos[1][1] - 7.4265634524358045e-06) < 1e-10

    # Radom array
    elts = sr.design.get_elements("ElArray")

    # Create an array that contains all elements
    allElts = ElementArray("AllElements", sr.design.get_all_elements())
    assert len(allElts) == 11

    # Create an array that contains all elements
    allMags = MagnetArray("AllMagnets", sr.design.magnets.get())
    assert len(allMags) == 7

    # Create an array that contains all BPM
    allBpms = BPMArray("AllBPMs", sr.design.bpm.all())
    assert len(allBpms) == 2

    cfm = sr.design.combined_function_magnets.get("CFM")
    strHVSQ = cfm.strengths.get()
    assert np.abs(strHVSQ[0] - 0.000010) < 1e-10  # H
    assert np.abs(strHVSQ[1] - 0.000015) < 1e-10  # V
    assert np.abs(strHVSQ[2] + 0.0) < 1e-10  # SQ
    assert np.abs(strHVSQ[3] + 0.000008) < 1e-10  # H
    assert np.abs(strHVSQ[4] + 0.000017) < 1e-10  # V
    assert np.abs(strHVSQ[5] + 0.0) < 1e-10  # SQ

    strHVSQu = cfm.strengths.unit()
    assert strHVSQu[0] == "rad"
    assert strHVSQu[1] == "rad"
    assert strHVSQu[2] == "m-1"
    assert strHVSQu[3] == "rad"
    assert strHVSQu[4] == "rad"
    assert strHVSQu[5] == "m-1"

    cfm.strengths.set([0.000010, 0.000015, 1e-6, -0.000008, -0.000017, 1e-6])
    strHVSQ = cfm.strengths.get()
    assert np.abs(strHVSQ[0] - 0.000010) < 1e-10  # H
    assert np.abs(strHVSQ[1] - 0.000015) < 1e-10  # V
    assert np.abs(strHVSQ[2] - 1.0e-6) < 1e-10  # SQ
    assert np.abs(strHVSQ[3] + 0.000008) < 1e-10  # H
    assert np.abs(strHVSQ[4] + 0.000017) < 1e-10  # V
    assert np.abs(strHVSQ[5] - 1e-6) < 1e-10  # SQ

    bpmsLive = BPMArray("", sr.live.bpm.all())
    bpmsLive.positions.get()

    # Test dynamic arrays

    sr: Accelerator = Accelerator.load("tests/config/EBSOrbit.yaml", include_locations=False)
    ae = ElementArray("All", sr.design.get_all_elements())
    acfm = ElementArray("AllCFM", sr.design.combined_function_magnet.all(), use_aggregator=False)

    bpmC5 = ae["BPM*"][10:20]  # All BPM C5
    assert isinstance(bpmC5, BPMArray) and len(bpmC5) == 10
    bpmc10 = ae["BPM*C10*"]  # All BPM C10
    assert isinstance(bpmc10, BPMArray) and len(bpmc10) == 10
    magSHV = ae["SH*-V"]  # All SH vertical corrector
    assert isinstance(magSHV, MagnetArray) and len(magSHV) == 96
    magSH1A = ae["model_name:SH1A-*"]  # All SH1A magnets (including the CFMs)
    assert isinstance(magSH1A, ElementArray) and len(magSH1A) == 129
    magSH1AC = acfm["model_name:SH1A-*"]  # All SH1A magnets (CFMs only)
    assert isinstance(magSH1AC, ElementArray) and len(magSH1AC) == 32

    # Empty arrays
    emptyMag = Magnet(name="EmptyMag", elements=[])
    emptyMag.fill_array(sr.design)  # Attach the array
    v = sr.design.magnets.get("EmptyMag").strengths.get()  # Ensure good attach
    assert np.shape(v) == (0,)

    emptyBPM = BPM(name="emptyBPM", elements=[])
    emptyBPM.fill_array(sr.design)  # Attach the array
    v = sr.design.bpms.get("emptyBPM").positions.get()  # Ensure good attach
    assert np.shape(v) == (0,)

    emptyCFM = CombinedFunctionMagnet(name="emptyCFM", elements=[])
    emptyCFM.fill_array(sr.design)  # Attach the array
    v = sr.design.combined_function_magnets.get("emptyCFM").strengths.get()  # Ensure good attach
    assert np.shape(v) == (0,)


@pytest.mark.parametrize(
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_serialized_magnets_arrays(sr_file):
    sr: Accelerator = Accelerator.load(sr_file, include_locations=False, ignore_external=True)
    the_serie = sr.design.serialized_magnets.get("series")
    strength = the_serie.strengths.get()
    assert len(strength) == 1
    print(strength)
    the_serie.strengths.set([0.000010])
    hardwares = the_serie.hardwares.get()
    assert len(hardwares) == 1
    print(hardwares)
    the_serie.hardwares.set([10])
