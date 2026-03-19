import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.magnet.serialized_magnet import SerializedMagnets


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
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_config_load(sr_file):
    sr: Accelerator = Accelerator.load(sr_file, use_fast_loader=True, ignore_external=True)
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


@pytest.mark.parametrize(
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_magnet_modification(sr_file):
    sr = Accelerator.load(sr_file, use_fast_loader=True, ignore_external=True)

    sm: SerializedMagnets = sr.design.get_serialized_magnet("mySeriesOfMagnets")
    element_names = sm._SerializedMagnets__elements

    lattice = sr.design.get_lattice()
    indices = [ii for ii in range(len(lattice)) if lattice[ii].FamName in element_names]

    print("Reading lattice strengths")
    print("FamName   K*L                L")
    for ii in indices:
        el = lattice[ii]
        print(el.FamName, el.K * el.Length, el.Length)

    print()
    print("Reading strengths from serialized magnets")

    for ii in range(len(sm.strengths.elements)):
        print(element_names[ii], sm.strengths.elements[ii].get())

    print()
    strength0 = sm.strengths.get()
    print(f"sm.strengths.get() = {strength0}")
    print()

    sm.strengths.set(strength0)

    print(f"Running sm.strengths.set({strength0})")
    print()

    print("Reading lattice strengths")
    print("FamName   K*L                L")
    for ii in indices:
        el = lattice[ii]
        print(el.FamName, el.K * el.Length, el.Length)

    print()
    print("Reading strengths from serialized magnets")

    for ii in range(len(sm.strengths.elements)):
        print(element_names[ii], sm.strengths.elements[ii].get())

    assert check_no_diff([sm.strengths.elements[ii].get() for ii in range(len(sm.strengths.elements))])
