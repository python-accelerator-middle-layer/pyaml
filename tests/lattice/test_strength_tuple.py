from unittest.mock import Mock

import at
import numpy as np
import pytest

from pyaml.common.abstract import ReadWriteFloatScalar
from pyaml.lattice.abstract_impl import RWStrengthScalar, RWStrengthTuple
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.identity_model import IdentityMagnetModel
from pyaml.magnet.vcorrector import VCorrector


@pytest.fixture
def total():
    accessor = Mock(spec=ReadWriteFloatScalar)
    accessor.unit.return_value = "rad"
    return accessor


def test_initialization_and_paired_writes(total):
    strengths = RWStrengthTuple(total, initial=(2.0, 0.5))
    total.set.assert_called_once_with(2.5)
    assert strengths.get() == (2.0, 0.5)
    assert isinstance(strengths.get(), tuple)
    total.get.assert_not_called()

    assert strengths.unit() == "rad"
    total.unit.return_value = "1/m"
    assert strengths.unit() == "1/m"

    previous = strengths.get()
    total.set.reset_mock()
    strengths.set((3.0, strengths.get()[1]))
    total.set.assert_called_once_with(3.5)
    assert strengths.get() == (3.0, 0.5)
    assert previous == (2.0, 0.5)

    total.set.reset_mock()
    strengths.set((strengths.get()[0], -0.5))
    total.set.assert_called_once_with(2.5)
    assert strengths.get() == (3.0, -0.5)

    total.set.reset_mock()
    strengths.set((np.float64(4.0), np.int64(1)))
    total.set.assert_called_once_with(5.0)
    assert strengths.get() == (4.0, 1.0)


@pytest.mark.parametrize(
    "values, error",
    [
        ((), ValueError),
        ((1,), ValueError),
        ((1, 2, 3), ValueError),
        (None, TypeError),
        (1, TypeError),
    ],
)
def test_invalid_pairs_do_not_write(total, values, error):
    with pytest.raises(error):
        RWStrengthTuple(total, initial=values)
    total.set.assert_not_called()

    strengths = RWStrengthTuple(total, initial=(1, 2))
    total.set.reset_mock()
    with pytest.raises(error):
        strengths.set(values)
    total.set.assert_not_called()
    assert strengths.get() == (1, 2)


def test_failed_writes_preserve_pair(total):
    strengths = RWStrengthTuple(total, initial=(1, 2))
    total.set.side_effect = RuntimeError("write failed")
    with pytest.raises(RuntimeError, match="write failed"):
        strengths.set((3, 4))
    assert strengths.get() == (1, 2)
    with pytest.raises(RuntimeError, match="write failed"):
        RWStrengthTuple(total, initial=(3, 4))


def test_waiting_has_no_side_effects(total):
    strengths = RWStrengthTuple(total, initial=(1, 2))
    total.reset_mock()
    with pytest.raises(NotImplementedError):
        strengths.set_and_wait((3, 4))
    assert total.mock_calls == []
    assert strengths.get() == (1, 2)


@pytest.mark.parametrize("polynom", [HCorrector.polynom, VCorrector.polynom])
@pytest.mark.parametrize("lengths", [(0.0,), (0.4,), (0.0, 0.0), (0.2, 0.6)])
def test_lattice_integration(polynom, lengths):
    elements = [at.Dipole(f"B{i}", length, 0.01 * (i + 1)) for i, length in enumerate(lengths)]
    model = IdentityMagnetModel(physics="COR", unit="rad")
    total = RWStrengthScalar(elements, polynom, model)
    strengths = RWStrengthTuple(total, initial=(0.03, 0.005))
    effective_length = sum(lengths) or len(lengths)
    bend = sum(e.BendingAngle for e in elements) if polynom.attName == "PolynomB" else 0.0

    def check_total(expected):
        assert total.get() == pytest.approx(expected)
        for element in elements:
            coefficient = getattr(element, polynom.attName)[0]
            assert coefficient == pytest.approx((expected - bend) / (polynom.sign * effective_length))

    check_total(0.035)
    strengths.set((strengths.get()[0], -0.002))
    check_total(0.028)
    strengths.set((0.04, strengths.get()[1]))
    check_total(0.038)
    strengths.set((0.02, 0.003))
    check_total(0.023)
    assert [e.BendingAngle for e in elements] == [0.01 * (i + 1) for i in range(len(elements))]

    # The tuple owns the decomposition; an explicit paired write restores its total.
    total.set(0.1)
    assert strengths.get() == (0.02, 0.003)
    strengths.set(strengths.get())
    check_total(0.023)
