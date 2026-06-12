import numpy as np
import pytest

from pyaml.accelerator import Accelerator


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_aggregator(install_test_package):
    sr = Accelerator.load("tests/config/sr.yaml")
    agg = sr.live.get_aggregator()
    agg.add_devices(sr.live.get_device("srdiag/bpm/c04-01/SA_HPosition"))
    agg.add_devices(sr.live.get_device("srdiag/bpm/c04-01/SA_VPosition"))
    agg.add_devices(sr.live.get_device("srdiag/bpm/c04-02/SA_HPosition"))
    agg.add_devices(sr.live.get_device("srdiag/bpm/c04-02/SA_VPosition"))

    # Iterator and index
    assert agg.len() == 4

    for idx, d in enumerate(agg):
        plane = "H" if idx % 2 == 0 else "V"
        assert f"c04-{(idx >> 1) + 1:02d}/SA_{plane}" in repr(d)

    assert "srdiag/bpm/c04-02/SA_HPosition" in repr(agg[2])

    # Immutable behavior
    with pytest.raises(TypeError, match="does not support item assignment"):
        agg[1] = sr.live.get_device("srdiag/bpm/c04-01/SA_HPosition")

    # Values
    assert np.shape(agg.get()) == (4,)
    assert agg.unit() == ["m", "m", "m", "m"]
