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

    print(sr.yellow_pages)

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


@pytest.mark.parametrize(
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_tune(sr_file):
    sr = Accelerator.load(sr_file, use_fast_loader=True, ignore_external=True)
    sr.design.get_lattice().disable_6d()

    quadForTuneDesign = sr.design.get_serialized_magnets("QForTune")
    tune_monitor = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    # Build tune response matrix
    tunemat = np.zeros((len(quadForTuneDesign), 2))

    # Magnet are not actually in series. Here a trick to set them to the same strengths
    for m in quadForTuneDesign:
        strength = m.strengths.get()
        m.strengths.set(strength)
    tune = tune_monitor.tune.get()
    print(f"tune={tune}")

    for idx, m in enumerate(quadForTuneDesign):
        strength = m.strengths.get()
        m.strengths.set(strength + 1e-4)
        dq = tune_monitor.tune.get() - tune
        tunemat[idx] = dq * 1e4
        m.strengths.set(strength)

    # Compute correction matrix
    correctionmat = np.linalg.pinv(tunemat.T)
    print(f"correctionmat.shape={correctionmat.shape}")
    print(f"correctionmat={correctionmat}")

    # Correct tune
    strengths = quadForTuneDesign.strengths.get()
    print(f"len(strengths)={len(strengths)}")
    print(f"strengths={strengths}")
    strengths += np.matmul(correctionmat, [0.1, 0.05])  # Ask for correction [dqx,dqy]
    print(f"strengths={strengths}")
    quadForTuneDesign.strengths.set(strengths)
    newTune = tune_monitor.tune.get()
    print(f"newTune={newTune}")
    diffTune = newTune - tune

    print(f"diffTune={diffTune}")
    assert np.abs(diffTune[0] - 0.1) < 1e-3
    assert np.abs(diffTune[1] - 0.05) < 1e-3
