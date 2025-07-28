import pytest


@pytest.mark.parametrize("install_test_package", [{
    "name": "dummy-cs-pyaml",
    "path": "tests/control/dummy-cs-pyaml"
}], indirect=True)
def test_dummy_cs_pyaml(install_test_package):
    print("Hello there !")
    assert True
