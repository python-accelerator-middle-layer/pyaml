import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory
from pyaml.magnet.cfm_magnet import CombinedFunctionMagnet
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.model import MagnetModel
from pyaml.magnet.vcorrector import VCorrector


@pytest.mark.parametrize(
    ("magnet_file", "install_test_package"),
    [
        (
            "tests/config/sr-ident-cfm.yaml",
            {"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"},
        ),
    ],
    indirect=["install_test_package"],
)
def test_cfm_magnets(magnet_file, install_test_package):
    sr: Accelerator = Accelerator.load(magnet_file)
    sr.design.get_lattice().disable_6d()
    # magnet_design = sr.design.get_magnet("SH1A-C01")
    # magnet_live = sr.live.get_magnet("SH1A-C01")
    # assert isinstance(magnet_design, CombinedFunctionMagnet)
    # assert isinstance(magnet_live, CombinedFunctionMagnet)
    magnet_h_design = sr.design.get_magnet("SH1A-C01-H")
    magnet_v_design = sr.design.get_magnet("SH1A-C01-V")
    magnet_h_live = sr.live.get_magnet("SH1A-C01-H")
    magnet_v_live = sr.live.get_magnet("SH1A-C01-V")
    assert isinstance(magnet_h_design, HCorrector)
    assert isinstance(magnet_v_design, VCorrector)
    assert isinstance(magnet_h_live, HCorrector)
    assert isinstance(magnet_v_live, VCorrector)
    magnet_h_live.strength.set(0.000010)
    magnet_v_live.strength.set(0.000015)
    magnet_h_design.strength.set(0.000010)
    magnet_v_design.strength.set(0.000015)

    o, _ = sr.design.get_lattice().find_orbit()
    assert np.abs(o[0] + 9.91848416e-05) < 1e-10
    assert np.abs(o[1] + 3.54829761e-07) < 1e-10
    assert np.abs(o[2] + 1.56246320e-06) < 1e-10
    assert np.abs(o[3] + 1.75037311e-05) < 1e-10

    Factory.clear()
