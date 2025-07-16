import numpy as np
import pytest
from pyaml.control.readback_value import Value

class TestBasicValue:
    """
    Test basic usage of the Value class with native types and arithmetic.
    """

    def test_value_basic(self):
        """
        Test basic arithmetic operations between Value instances and scalars or other Value objects.

        This test verifies that:
        - Addition between Value and int works correctly.
        - The result of chained additions is both numerically and semantically equal to an expected Value.
        - Division between two Value instances produces the expected float result.
        - The result of Value / Value is a float and not a Value instance.
        """
        toi = Value(1)
        moi = 2
        tout_ceux_qui_le_veulent = Value(3)
        et_entrez_dans_la_danse = 2

        allez_venez = toi + moi + tout_ceux_qui_le_veulent
        assert allez_venez == 6
        assert allez_venez == Value(6)

        laissez_faire_l_insouciance = Value(allez_venez) / Value(et_entrez_dans_la_danse)
        assert isinstance(laissez_faire_l_insouciance,float)
        assert laissez_faire_l_insouciance == 3

    @pytest.mark.parametrize("scalar,expected", [
        (2, 6.28),
        (0.5, 1.57),
        (-1, -3.14),
    ])
    def test_value_scalar_multiplication(self, value_scalar, scalar, expected):
        """
        Test multiplication between Value and scalar using different coefficients.

        Parameters
        ----------
        scalar : float
            The scalar to multiply the Value with.
        expected : float
            The expected numeric result.
        """
        assert value_scalar  * scalar == expected
        assert scalar * value_scalar  == expected

class TestValueNumpy:

    def test_value_with_numpy(self):
        """
        Test interactions between Value objects and NumPy arrays.

        This test ensures that:
        - Value objects can be multiplied by scalars.
        - A list of Value objects can be converted into a NumPy array.
        - Multiplication between arrays of Value and NumPy vectors works elementwise.
        - The result of operations is unwrapped to native NumPy float types.
        """
        my_list = [Value(3.14) for _ in range(10)]

        # Simple computation tests
        assert my_list[0] * 2 == 6.28

        # Numy computation tests
        my_array = np.array(my_list)
        vector = np.full(10, 2)
        mult_result1 = my_array * vector
        mult_result2 = vector * my_array
        assert np.all(mult_result1 == 6.28)
        assert np.all(mult_result2 == 6.28)

        # Typing tests
        assert isinstance(my_array[0], Value)
        my_array_typed = np.array(my_list, dtype=float)
        assert isinstance(my_array_typed[0], np.float64)
        assert isinstance(mult_result1[0], float)


    @pytest.mark.parametrize("input_array, expected_squared, expected_scaled", [
        (np.array([10, 20, 30]),
         np.array([100, 400, 900]),
         np.array([20, 40, 60])),
        (np.array([1, 2, 3]),
         np.array([1, 4, 9]),
         np.array([2, 4, 6]))
    ])
    def test_value_with_array(self, input_array, expected_squared, expected_scaled):
        """
        Test arithmetic operations on Value instances containing NumPy arrays.

        Parameters
        ----------
        input_array : np.ndarray
            Input array wrapped in a Value.
        expected_squared : np.ndarray
            Expected result of input_array squared.
        expected_scaled : np.ndarray
            Expected result of input_array * 2.
        """
        vector = np.full(len(input_array), 2)
        array_value = Value(input_array)

        squared = array_value * array_value
        assert np.all(squared == expected_squared)

        two_times = array_value * vector
        assert np.all(two_times == expected_scaled)


    def test_of_array_of_value_of_array(self, value_matrix, broadcast_matrix):
        """
        Test multiplication of a 1D array of Value objects (each wrapping a NumPy array)
        by a 2D NumPy matrix.

        This test checks that:
        - The resulting matrix has correct shape and contains correctly multiplied values.
        - Each row in the result corresponds to one of the Value-wrapped arrays,
          multiplied elementwise by 2.
        - The Value instances are preserved in structure and contents are correctly accessed.
        """
        result = value_matrix * broadcast_matrix

        assert result.shape == (3, 3)

        for row in result:
            for computed, original in zip(row, value_matrix):
                assert isinstance(original, Value)
                twice = original * 2
                assert np.all(computed == twice)
