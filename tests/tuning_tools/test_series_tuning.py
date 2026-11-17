"""
Tune and chromaticity tools on arrays holding a series.

The magnets of a series share ONE power supply: the series is one knob of the tool, its serialized family. The tools
measure one column for the family and write its power supply once, with the full correction. The array of the tool
can list all the magnets of the series, only one of them, or the family name: the result is the same.

Configuration (tests/config/sr_series_tuning.yaml):
    QF1A: a series of 4 quadrupoles, QD2A-C05..C08: 4 individually powered quadrupoles.
    SF2A: a series of 4 sextupoles, SD1A-C05..C06: 2 individually powered sextupoles.
"""

import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action

CONFIG = "tests/config/sr_series_tuning.yaml"
SETUPS = ["ALL_MAGNETS", "ONE_MAGNET", "FAMILY"]
KNOBS = ["QF1A", "QD2A-C05", "QD2A-C06", "QD2A-C07", "QD2A-C08"]
DTUNE = np.array([0.01, 0.005])


def load_design(six_d: bool):
    """Load the configuration and return the simulator, its series powered like on a real machine."""
    sr = Accelerator.load(CONFIG)
    design = sr.design
    if six_d:
        design.get_lattice().enable_6d()
    else:
        design.get_lattice().disable_6d()
    # In the lattice file, the magnets of a series do not all have the same strength. Writing the power supply once
    # gives them the strengths of a single current, as on the machine, so that the measurements start from there.
    for name in ["QF1A", "SF2A"]:
        family = design.serialized_magnet.get(name)
        family.hardware.set(family.hardware.get())
    return design


def correct_tune(setup: str, tmp_path):
    """Measure the tune response matrix of a setup, load it and add DTUNE, from a fresh machine."""
    design = load_design(six_d=False)
    trm = design.tool.get(f"TRM_{setup}")
    tune = design.tool.get(f"TUNE_{setup}")

    # Measure and load the response matrix
    assert trm.measure()
    path = tmp_path / f"trm_{setup}.json"
    trm.save(path)
    tune.load(path)

    # Correct the tune
    initial_tune = tune.readback()
    tune.add(DTUNE)
    achieved = tune.readback() - initial_tune
    return design, trm.latest_measurement, achieved


@pytest.mark.parametrize("setup", SETUPS)
def test_tune_correction_reaches_the_target_whatever_the_listing_of_the_series(setup, tmp_path):
    design, measurement, achieved = correct_tune(setup, tmp_path)

    # One column per knob: the series is one column, named after its family
    assert measurement["variable_names"] == KNOBS
    assert np.shape(measurement["matrix"]) == (2, 5)

    # The requested tune change is reached, within the nonlinearity of a one-step measurement (about 1 %). With one
    # column per magnet of the series, the series would move by a fraction of the correction only.
    np.testing.assert_allclose(achieved, DTUNE, atol=5e-4)


def test_tune_correction_is_the_same_for_every_listing_of_the_series(tmp_path):
    results = {setup: correct_tune(setup, tmp_path) for setup in SETUPS}
    reference_design, reference_measurement, _ = results["FAMILY"]
    reference_ps = reference_design.serialized_magnet.get("QF1A").hardware.get()

    for setup in ["ALL_MAGNETS", "ONE_MAGNET"]:
        design, measurement, _ = results[setup]
        # Same matrix
        np.testing.assert_allclose(measurement["matrix"], reference_measurement["matrix"])
        # Same power supply current of the series after correction, so the series moved by the full correction,
        # not by 1/N of it
        assert design.serialized_magnet.get("QF1A").hardware.get() == pytest.approx(reference_ps)


def test_tune_measurement_reports_the_family_name_in_callbacks():
    design = load_design(six_d=False)

    # Record the name of the knob given with each excitation
    excited = []

    def callback(action, data):
        if action == Action.APPLY:
            excited.append(data["magnet"])
        return True

    assert design.tool.get("TRM_ALL_MAGNETS").measure(callback=callback)

    # The series is excited once, as a whole
    assert excited == KNOBS


# ---------------------------------------------------------------------------
# A matrix that does not match the knobs
# ---------------------------------------------------------------------------


def test_matrix_with_one_column_per_magnet_of_a_series_is_refused(caplog):
    # At load time, only a warning: the accelerator still loads with a stale matrix file
    with caplog.at_level("WARNING"):
        sr = Accelerator.load(CONFIG)
    assert "TUNE_STALE_MATRIX: the response matrix variables do not match" in caplog.text

    # When correcting, an error asking for a new measurement
    tune = sr.design.tool.get("TUNE_STALE_MATRIX")
    with pytest.raises(PyAMLException, match="measure a new tune response matrix"):
        tune.add(DTUNE)


def test_matrix_with_knobs_in_another_order_is_refused(tmp_path):
    design = load_design(six_d=False)
    trm = design.tool.get("TRM_FAMILY")
    assert trm.measure()

    # Swap the first two columns and their names
    measurement = trm.latest_measurement
    measurement["variable_names"][0:2] = measurement["variable_names"][1::-1]
    for row in measurement["matrix"]:
        row[0:2] = row[1::-1]
    path = tmp_path / "swapped.json"
    trm.save(path)

    tune = design.tool.get("TUNE_FAMILY")
    tune.load(path)
    with pytest.raises(PyAMLException, match="same variables in another order"):
        tune.add(DTUNE)


# ---------------------------------------------------------------------------
# Chromaticity
# ---------------------------------------------------------------------------


def correct_chromaticity(setup: str, tmp_path):
    """Measure the chromaticity response matrix of a setup, load it and add a chromaticity change."""
    design = load_design(six_d=True)
    crm = design.tool.get(f"CRM_{setup}")
    chromaticity = design.tool.get(f"CHROMA_{setup}")

    assert crm.measure()
    path = tmp_path / f"crm_{setup}.json"
    crm.save(path)
    chromaticity.load(path)

    initial = design.get_lattice().get_chrom()[:-1]
    chromaticity.add(np.array([0.2, 0.1]))
    achieved = design.get_lattice().get_chrom()[:-1] - initial
    return design, crm.latest_measurement, achieved


def test_chromaticity_correction_is_the_same_for_the_magnets_and_the_family_of_a_series(tmp_path):
    all_design, all_measurement, all_achieved = correct_chromaticity("ALL_MAGNETS", tmp_path)
    family_design, family_measurement, family_achieved = correct_chromaticity("FAMILY", tmp_path)

    # One column per knob, the series under its family name
    assert all_measurement["variable_names"] == family_measurement["variable_names"] == ["SF2A", "SD1A-C05", "SD1A-C06"]
    np.testing.assert_allclose(all_measurement["matrix"], family_measurement["matrix"])

    # The same correction: same power supply of the series, same chromaticity change
    assert all_design.serialized_magnet.get("SF2A").hardware.get() == pytest.approx(
        family_design.serialized_magnet.get("SF2A").hardware.get()
    )
    np.testing.assert_allclose(all_achieved, family_achieved)
    np.testing.assert_allclose(all_achieved, [0.2, 0.1], atol=5e-2)
