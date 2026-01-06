import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory


def check_no_diff(array: list[np.float64]) -> bool:
    d = None
    for i, a in enumerate(array):
        for j, b in enumerate(array):
            if i != j:
                if d:
                    d = max(d, abs(a - b))
                else:
                    d = abs(a - b)
    return d < 0.001


@pytest.mark.parametrize(
    ("sr_file", "install_test_package"),
    [
        (
            "tests/config/sr_serialized_magnets.yaml",
            {"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"},
        ),
    ],
    indirect=["install_test_package"],
)
def test_config_load(sr_file, install_test_package):
    sr: Accelerator = Accelerator.load(sr_file)
    assert sr is not None
    magnets = [
        sr.design.get_element("QF8B-C04"),
        sr.design.get_element("QF8B-C04"),
        sr.design.get_element("QD5D-C04"),
        sr.design.get_element("QF6D-C04"),
        sr.design.get_element("QF4D-C04"),
    ]
    assert None not in [magnets]

    magnets[3].strength.set(0.6)
    strengths = [magnet.strength.get() for magnet in magnets]
    currents = [magnet.hardware.get() for magnet in magnets]
    assert check_no_diff(strengths)
    assert check_no_diff(currents)

    magnets[2].hardware.set(50)
    strengths = [magnet.strength.get() for magnet in magnets]
    currents = [magnet.hardware.get() for magnet in magnets]
    assert check_no_diff(strengths)
    assert check_no_diff(currents)
    Factory.clear()
