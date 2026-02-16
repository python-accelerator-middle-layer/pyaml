import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.arrays.element_array import ElementArray
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.configuration.factory import Factory
from pyaml.magnet.magnet import Magnet


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_element_array_and_array_intersection_is_autotyped(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    hcorr = sr.live.get_magnets("HCORR")
    hvcorr = sr.live.get_magnets("HVCORR")

    inter = hvcorr & hcorr

    assert isinstance(inter, MagnetArray)
    assert inter.names() == hcorr.names()

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_element_array_and_mask_filters_and_is_autotyped_list_mask(
    install_test_package,
):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    # "ElArray" is a mixed ElementArray in the dummy config (see existing tests)
    elts = sr.design.get_elements("ElArray")
    assert isinstance(elts, ElementArray)
    assert len(elts) > 0

    mask = [isinstance(e, Magnet) for e in elts]
    res = elts & mask

    # Only magnets are kept -> result should be MagnetArray
    assert isinstance(res, MagnetArray)
    assert all(isinstance(e, Magnet) for e in res)
    assert len(res) == sum(mask)

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_element_array_and_mask_filters_and_is_autotyped_numpy_mask(
    install_test_package,
):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    elts = sr.design.get_elements("ElArray")
    assert len(elts) > 0

    mask_list = [isinstance(e, Magnet) for e in elts]
    mask_np = np.array(mask_list, dtype=bool)

    res = elts & mask_np

    assert isinstance(res, MagnetArray)
    assert all(isinstance(e, Magnet) for e in res)
    assert len(res) == int(mask_np.sum())

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_element_array_sub_mask_removes_true_inverse_of_and(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    elts = sr.design.get_elements("ElArray")
    assert len(elts) > 0

    # Keep only magnets with '& mask'
    is_magnet = [isinstance(e, Magnet) for e in elts]
    only_magnets = elts & is_magnet
    assert all(isinstance(e, Magnet) for e in only_magnets)

    # Remove magnets with '- mask' (inverse operation)
    without_magnets = elts - is_magnet

    # Result may be ElementArray or a more specific type depending on what's left,
    # but it must not contain magnets.
    if isinstance(without_magnets, list):
        remaining = without_magnets
    else:
        remaining = list(without_magnets)

    assert all(not isinstance(e, Magnet) for e in remaining)
    assert len(remaining) + len(only_magnets) == len(elts)

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_element_array_mask_length_mismatch_raises_for_and_and_sub(
    install_test_package,
):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    elts = sr.design.get_elements("ElArray")
    assert len(elts) > 0

    bad_mask = [True] * (len(elts) - 1)

    with pytest.raises(ValueError):
        _ = elts & bad_mask

    with pytest.raises(ValueError):
        _ = elts - bad_mask

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_mask_by_type_returns_correct_boolean_mask(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    elts = sr.design.get_elements("ElArray")
    mask = elts.mask_by_type(Magnet)

    assert isinstance(mask, list)
    assert len(mask) == len(elts)
    assert all(isinstance(v, bool) for v in mask)

    # Check semantic correctness
    for e, m in zip(elts, mask, strict=True):
        assert m == isinstance(e, Magnet)

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_filter_by_type_returns_autotyped_array(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/sr.yaml")
    sr.design.get_lattice().disable_6d()

    elts = sr.design.get_elements("ElArray")
    filtered = elts.of_type(Magnet)

    if len(filtered) == 0:
        assert filtered == []
    else:
        assert isinstance(filtered, MagnetArray)
        assert all(isinstance(e, Magnet) for e in filtered)
