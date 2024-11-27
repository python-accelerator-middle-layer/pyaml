import numpy
import pytest

def test_nothing():
    val = numpy.zeros(6)
    numpy.testing.assert_equal(val, numpy.zeros(6))
