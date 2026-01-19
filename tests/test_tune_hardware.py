import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory


def test_tune():
    sr: Accelerator = Accelerator.load("tests/config/EBSTune.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    quadForTuneDesign = sr.design.get_magnets("QForTune")

    # Build tune response matrix (hardware units)

    tune_monitor = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    tune = tune_monitor.tune.get()
    print(tune)
    tunemat = np.zeros((len(quadForTuneDesign), 2))

    idx = 0
    for m in quadForTuneDesign:
        current = m.hardware.get()
        m.hardware.set(current + 1e-6)
        dq = tune_monitor.tune.get() - tune
        tunemat[idx] = dq * 1e6
        m.hardware.set(current)
        idx += 1

    # Compute correction matrix
    correctionmat = np.linalg.pinv(tunemat.T)

    # Correct tune
    currents = quadForTuneDesign.hardwares.get()
    currents += np.matmul(correctionmat, [0.1, 0.05])  # Ask for correction [dqx,dqy]
    quadForTuneDesign.hardwares.set(currents)
    newTune = tune_monitor.tune.get()
    units = quadForTuneDesign.hardwares.unit()
    diffTune = newTune - tune
    assert np.abs(diffTune[0] - 0.1) < 1e-3
    assert np.abs(diffTune[1] - 0.05) < 1.1e-3
    assert np.abs(currents[0] - 88.04522942) < 1e-8
    assert np.abs(currents[1] - 88.26677735) < 1e-8
    assert units[0] == "A" and units[1] == "A"
    Factory.clear()
