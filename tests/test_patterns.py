import numpy as np
import pytest

from pyaml.accelerator import Accelerator


def test_tune():
    sr: Accelerator = Accelerator.load(
        "tests/config/EBSTune-patterns.yaml", ignore_external=True
    )
    sr.design.get_lattice().disable_6d()

    quadForTune = sr.design.get_magnets("QForTune")
    assert len(quadForTune.names()) == 124

    quadForTest = sr.design.get_magnets("QForTest")
    assert sr.design.get_magnet("QF1E-C06") is not None
    assert sr.design.get_magnet("QF1E-C05") is not None
    assert "QF1E-C05" not in quadForTest.names()
    assert all(
        [
            not (name.startswith("Q") and name.endswith("-C06"))
            for name in quadForTest.names()
        ]
    )
