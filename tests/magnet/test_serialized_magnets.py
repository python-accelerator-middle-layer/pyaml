import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.magnet.serialized_magnet import SerializedMagnets
from pyaml.magnet.sextupole import Sextupole


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
    sr: Accelerator = Accelerator.load(sr_file, include_locations=False, ignore_external=True)
    assert sr is not None
    magnets = [
        sr.design["QF8B-C04"],
        sr.design["QF8B-C04"],
        sr.design["QD5D-C04"],
        sr.design["QF6D-C04"],
        sr.design["QF4D-C04"],
    ]
    assert None not in [magnets]

    magnets[3].strength.set(0.6)
    strengths = [magnet.strength.get() for magnet in magnets]
    currents = [magnet.hardware.get() for magnet in magnets]
    # assert check_no_diff(strengths)
    # assert check_no_diff(currents)

    magnets[2].hardware.set(50)
    strengths = [magnet.strength.get() for magnet in magnets]
    currents = [magnet.hardware.get() for magnet in magnets]
    # assert check_no_diff(strengths)
    # assert check_no_diff(currents)


@pytest.mark.parametrize(
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_magnet_modification(sr_file):
    sr = Accelerator.load(sr_file, include_locations=False, ignore_external=True)

    print(sr.yellow_pages)

    sm: SerializedMagnets = sr.design.serialized_magnet.get("mySeriesOfMagnets")
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

    for ii, magnet in enumerate(sm.get_magnets()):
        print(element_names[ii], magnet.strength.get())

    print()
    strength0 = sm.strength.get()
    print(f"sm.strength.get() = {strength0}")
    print()

    sm.strength.set(strength0)

    print(f"Running sm.strengt.set({strength0})")
    print()

    print("Reading lattice strengths")
    print("FamName   K*L                L")
    for ii in indices:
        el = lattice[ii]
        print(el.FamName, el.K * el.Length, el.Length)

    print()
    print("Reading strengths from serialized magnets")

    for ii, magnet in enumerate(sm.get_magnets()):
        print(element_names[ii], magnet.strength.get())


@pytest.mark.parametrize(
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_tune(sr_file):
    sr = Accelerator.load(sr_file, include_locations=False, ignore_external=True)
    sr.design.get_lattice().disable_6d()

    m = sr.design.serialized_magnet.get("QF1A")
    print(f"m.strength.get()={m.strength.get()}")
    assert len(m.get_magnets()) == m.get_nb_magnets()

    quadForTuneDesign = sr.design.serialized_magnets.get("QForTune")
    tune_monitor = sr.design.diagnostic.get("BETATRON_TUNE")
    # Build tune response matrix
    tunemat = np.zeros((len(quadForTuneDesign), 2))

    # Magnet are not actually in series. Here a trick to set them to the same strengths
    for m in quadForTuneDesign:
        strength = m.strength.get()
        m.strength.set(strength)
    tune = tune_monitor.tune.get()
    print(f"tune={tune}")

    for idx, m in enumerate(quadForTuneDesign):
        strength = m.strength.get()
        m.strength.set(strength + 1e-4)
        dq = tune_monitor.tune.get() - tune
        tunemat[idx] = dq * 1e4
        m.strength.set(strength)

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


@pytest.mark.parametrize(
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_get_device_names(sr_file):
    sr: Accelerator = Accelerator.load(sr_file, include_locations=False, ignore_external=True)
    sm: SerializedMagnets = sr.design.serialized_magnet.get("QF1A")

    device_names = sm.get_device_names()

    # Serialized magnets share a single power converter: exactly 1 device
    assert len(device_names) == 1
    # Strength and hardware computation must remain consistent after the fix
    initial_strength = sm.strength.get()
    sm.strength.set(initial_strength * 1.01)
    assert abs(sm.strength.get() - initial_strength * 1.01) < 1e-3
    sm.strength.set(initial_strength)


def get_strengths_from_lattice(sr: Accelerator, sm: SerializedMagnets) -> list:
    ring = sr.design.get_lattice()
    strs = []
    for m in sm.get_magnets():
        elt = ring.get_elements(f"{m.get_name()}")[0]
        strs.append(elt.K * elt.Length)
    return strs


@pytest.mark.parametrize(
    "sr_file",
    [
        "tests/config/sr_serialized_magnets.yaml",
    ],
)
def test_strength_computation(sr_file):
    sr: Accelerator = Accelerator.load(sr_file, include_locations=False, ignore_external=True)
    sm: SerializedMagnets = sr.design.serialized_magnet.get("QF1A")
    assert sm.get_nb_magnets() == 31
    sm.strength.set(0.8)
    assert abs(sm.strength.get() - 0.8) < 1e-6

    magnets_strengths = [m.strength.get() for m in sm.get_magnets()]
    magnets_from_lattice_strengths = get_strengths_from_lattice(sr, sm)
    # The family strength is the average strength of the magnets
    assert abs(np.mean(magnets_from_lattice_strengths) - 0.8) < 1e-6
    assert magnets_strengths == magnets_from_lattice_strengths


SR_FILE = "tests/config/sr_serialized_magnets.yaml"
# A quadrupole (B1) and a sextupole (B2) on the same power supply
MIXED = "mixedFunctionSeries"


def _effective_length(element) -> float:
    return element.Length if element.Length else 1.0


def test_partial_strength_request_keeps_one_hardware_value_per_power_supply():
    sr: Accelerator = Accelerator.load(SR_FILE, include_locations=False, ignore_external=True)
    family: SerializedMagnets = sr.design.serialized_magnet.get("QF1A")
    model = family.model
    current = np.array([family.hardware.get()])

    assert model.compute_hardware_values_partial(current, {1: 0.8}).shape == current.shape
    with pytest.raises(PyAMLException, match="current_hardware"):
        model.compute_hardware_values_partial(np.array([80.0, 80.0]), {1: 0.8})


def test_series_with_one_function_is_homogeneous():
    sr: Accelerator = Accelerator.load(SR_FILE, include_locations=False, ignore_external=True)
    assert sr.design.serialized_magnet.get("QF1A").is_homogeneous()
    assert not sr.design.serialized_magnet.get(MIXED).is_homogeneous()


def test_mixed_function_series_has_no_single_family_strength():
    sr: Accelerator = Accelerator.load(SR_FILE, include_locations=False, ignore_external=True)
    family: SerializedMagnets = sr.design.serialized_magnet.get(MIXED)
    with pytest.raises(PyAMLException, match="mixing magnet functions"):
        family.strength.get()
    with pytest.raises(PyAMLException, match="mixing magnet functions"):
        family.strength.set(0.5)


def test_mixed_function_series_keeps_hardware_and_per_magnet_access():
    sr: Accelerator = Accelerator.load(SR_FILE, include_locations=False, ignore_external=True)
    family: SerializedMagnets = sr.design.serialized_magnet.get(MIXED)
    quad, sextu = family.get_magnets()
    assert isinstance(quad, Quadrupole)
    assert isinstance(sextu, Sextupole)

    family.hardware.set(50.0)

    assert family.hardware.get() == pytest.approx(50.0)
    assert np.allclose(family.hardwares.get(), 50.0)
    assert np.allclose(family.strengths.get(), [quad.strength.get(), sextu.strength.get()])


def test_mixed_function_series_writes_each_magnet_in_its_own_polynom():
    sr: Accelerator = Accelerator.load(SR_FILE, include_locations=False, ignore_external=True)
    family: SerializedMagnets = sr.design.serialized_magnet.get(MIXED)
    ring = sr.design.get_lattice()
    quad_element = ring.get_elements("QF6D-C01")[0]
    sextu_element = ring.get_elements("SD1A-C01")[0]
    sextu_b1_before = sextu_element.PolynomB[1]

    family.hardware.set(50.0)

    quad_strength = family.model.get_sub_model(0).compute_strengths([50.0])[0]
    sextu_strength = family.model.get_sub_model(1).compute_strengths([50.0])[0]
    assert quad_element.PolynomB[1] * _effective_length(quad_element) == pytest.approx(quad_strength)
    assert sextu_element.PolynomB[2] * _effective_length(sextu_element) == pytest.approx(sextu_strength)
    assert sextu_element.PolynomB[1] == sextu_b1_before


def test_mixed_function_series_strengths_converge_for_a_consistent_request(caplog):
    sr: Accelerator = Accelerator.load(SR_FILE, include_locations=False, ignore_external=True)
    family: SerializedMagnets = sr.design.serialized_magnet.get(MIXED)
    family.hardware.set(50.0)
    requested = family.strengths.get()
    family.hardware.set(30.0)

    with caplog.at_level("WARNING"):
        family.strengths.set(requested)

    assert family.hardware.get() == pytest.approx(50.0)
    assert np.allclose(family.strengths.get(), requested)
    assert "Inconsistent strengths" not in caplog.text


def test_mixed_function_series_strengths_warn_for_an_inconsistent_request(caplog):
    sr: Accelerator = Accelerator.load(SR_FILE, include_locations=False, ignore_external=True)
    family: SerializedMagnets = sr.design.serialized_magnet.get(MIXED)
    family.hardware.set(50.0)
    requested = family.strengths.get() * np.array([1.0, 1.1])

    with caplog.at_level("WARNING"):
        family.strengths.set(requested)

    # One power supply: the series gets the hardware value solving sum((f_i(I) - k_i) / span_i) == 0. Both magnets
    # of this family share the same curve and calibration, so their spans are equal and the obtained strengths
    # average to the requested ones
    assert np.mean(family.strengths.get()) == pytest.approx(np.mean(requested))
    assert "Inconsistent strengths" in caplog.text
