import numpy as np
from pyaml.control.readback_value import Value

def test_value_basic():
    toi = Value(1)
    moi = 2
    tout_ceux_qui_le_veulent = Value(3)
    et_entrez_dans_la_danse = 2

    allez_venez = toi + moi + tout_ceux_qui_le_veulent
    assert allez_venez==6
    assert allez_venez==Value(6)
    laissez_faire_l_insouciance = Value(allez_venez) / et_entrez_dans_la_danse
    assert laissez_faire_l_insouciance == 3



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

def test_value_with_array():
    a = np.array([10, 20, 30])
    a2 = np.array([100, 400, 900])
    vector = np.full(3, 2)
    array_value = Value(a)
    squared = array_value * array_value
    assert (squared == a2).all()
    a3 = np.array([20, 40, 60])
    two_times = array_value * vector
    assert (two_times == a3).all()
