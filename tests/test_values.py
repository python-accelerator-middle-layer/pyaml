import numpy as np
from pyaml.control.readback_value import Value

def test_value_with_numpy():
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
    assert type(my_array[0])==Value
    my_array_typed = np.array(my_list, dtype=float)
    assert type(my_array_typed[0])==np.float64
    assert type(mult_result1[0])==float
