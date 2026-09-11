import numpy as np
import pytest

from pyaml.accelerator import Accelerator


def test_tune():
    sr: Accelerator = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    quadForTune = sr.design.magnets.get("QForTune")
    assert len(quadForTune.names()) == 124

    quadForTest = sr.design.magnets.get("QForTest")
    assert sr.design.magnet.get("QF1E-C06") is not None
    assert sr.design.magnet.get("QF1E-C05") is not None
    assert "QF1E-C05" not in quadForTest.names()
    assert all([not (name.startswith("Q") and name.endswith("-C06")) for name in quadForTest.names()])
