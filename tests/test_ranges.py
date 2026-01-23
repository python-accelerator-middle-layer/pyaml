import numpy as np
import pytest

from pyaml.control.abstract_impl import check_range


@pytest.mark.parametrize(
    "values,dev_range,expected",
    [
        # --- scalar with single range ---
        (3.0, [0.0, 10.0], True),
        (12.0, [0.0, 10.0], False),

        # --- list with matching number of ranges ---
        ([3.0, 2.0], [0.0, 10.0, 1.0, 5.0], True),
        ([3.0, 6.0], [0.0, 10.0, 1.0, 5.0], False),

        # --- numpy arrays ---
        (np.array([1.0, 2.0]), [0.0, 2.0, 1.0, 3.0], True),
        (np.array([1.0, 4.0]), [0.0, 2.0, 1.0, 3.0], False),

        # --- None bounds (unbounded side) ---
        ([3.0, 2.0], [None, 10.0, 1.0, None], True),
        ([3.0, 0.5], [None, 10.0, 1.0, None], False),

        # --- single value checked against ALL ranges (broadcast value) ---
        (3.0, [0.0, 10.0, -15.0, 15.0], True),
        (3.0, [0.0, 10.0, 4.0, 15.0], False),

        # --- single range applied to ALL values (broadcast range) ---
        ([1.0, 2.0, 3.0], [0.0, 5.0], True),
        ([1.0, 6.0, 3.0], [0.0, 5.0], False),
    ],
)
def test_check_range(values, dev_range, expected):
    assert check_range(values, dev_range) is expected


@pytest.mark.parametrize(
    "dev_range",
    [
        [0.0, 5.0, 0.0],          # odd length
        np.array([0.0, 5.0, 0.0])  # odd length (numpy)
    ],
)
def test_check_range_raises_on_odd_dev_range_length(dev_range):
    with pytest.raises(ValueError):
        check_range(1.0, dev_range)


@pytest.mark.parametrize(
    "values,dev_range",
    [
        # N=2 values, K=2.5 ranges -> odd length already covered, so here: N=2, K=3 (size 6)
        ([1.0, 2.0], [0.0, 5.0, 0.0, 10.0, -1.0, 1.0]),
        # N=3 values, K=2 ranges (size 4) and neither N==1 nor K==1
        ([1.0, 2.0, 3.0], [0.0, 5.0, 0.0, 10.0]),
    ],
)
def test_check_range_raises_on_inconsistent_sizes(values, dev_range):
    with pytest.raises(ValueError):
        check_range(values, dev_range)


@pytest.mark.parametrize(
    "dev_range",
    [
        [0.0, 10.0, -15.0, 15.0],
        np.array([0.0, 10.0, -15.0, 15.0], dtype=object),
        np.array([0.0, 10.0, -15.0, 15.0], dtype=float),
    ],
)
def test_check_range_single_value_is_equivalent_to_explicit_duplication(dev_range):
    assert check_range(3.0, dev_range) == check_range([3.0, 3.0], dev_range)
