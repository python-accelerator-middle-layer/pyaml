import pytest
import numpy as np
from pyaml.control.readback_value import Value


@pytest.fixture
def value_scalar():
    """Return a basic scalar Value instance."""
    return Value(3.14)


@pytest.fixture
def value_array():
    """Return a Value instance containing a NumPy array."""
    return Value(np.array([10, 20, 30]))


@pytest.fixture
def value_matrix():
    """Return a list of Value instances wrapping NumPy arrays."""
    return [
        Value(np.array([10, 20, 30])),
        Value(np.array([100, 400, 900])),
        Value(np.array([1000, 4000, 9000])),
    ]


@pytest.fixture
def scalar_vector():
    """Return a vector of scalars for broadcasting tests."""
    return np.full(3, 2)


@pytest.fixture
def broadcast_matrix():
    """Return a 3x3 matrix filled with 2s for broadcasted multiplication tests."""
    return np.full((3, 3), 2)
