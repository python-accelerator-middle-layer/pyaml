import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory


def _in_range(vmin, vmax) -> float:
    if vmin is None and vmax is None:
        return 0.0
    if vmin is None:
        return float(vmax) - 0.1
    if vmax is None:
        return float(vmin) + 0.1
    return (float(vmin) + float(vmax)) / 2.0


def _out_of_range(vmin, vmax) -> float:
    if vmax is not None:
        return float(vmax) + 0.1
    if vmin is not None:
        return float(vmin) - 0.1
    raise RuntimeError("Unbounded range [None, None], cannot build an out-of-range value.")


@pytest.mark.parametrize(
    ("magnet_file", "install_test_package"),
    [
        (
            "tests/config/sr-range-cfm.yaml",
            {"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"},
        ),
    ],
    indirect=["install_test_package"],
)
def test_cfm_ranges_from_yaml_are_propagated_and_enforced(magnet_file, install_test_package):
    sr: Accelerator = Accelerator.load(magnet_file)
    sr.design.get_lattice().disable_6d()

    # Parent CFM magnet (the one defined in SH1AC01-range.yaml)
    m = sr.live.get_cfm_magnet("SH1A-C01")

    devs = m.model.get_devices()
    assert len(devs) == 3

    # Exact ranges coming from the YAML configuration file (powerconverters[*].range)
    expected_ranges = [
        [-1.5, 1.5],
        [None, 1.5],
        [-1.5, None],
    ]

    got_ranges = [d.get_range() for d in devs]
    assert got_ranges == expected_ranges

    # Build an in-range current vector (3 values)
    in_currents = np.array([
        _in_range(*expected_ranges[0]),
        _in_range(*expected_ranges[1]),
        _in_range(*expected_ranges[2]),
    ])

    # Convert currents -> strengths (vector size 3)
    in_strengths = m.model.compute_strengths(in_currents)
    m.strengths.set(in_strengths)  # must succeed

    # Build an out-of-range current vector (break only channel 2 for instance)
    out_currents = in_currents.copy()
    out_currents[1] = _out_of_range(*expected_ranges[1])

    out_strengths = m.model.compute_strengths(out_currents)

    with pytest.raises(PyAMLException, match="out of range"):
        m.strengths.set(out_strengths)

    Factory.clear()
