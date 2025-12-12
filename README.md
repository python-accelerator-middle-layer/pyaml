[![Documentation Status](https://readthedocs.org/projects/pyaml/badge/?version=latest)](https://pyaml.readthedocs.io/en/latest/?badge=latest)
![Current release](https://img.shields.io/github/v/tag/python-accelerator-middle-layer/pyaml)

# pyAML: Python Accelerator Middle Layer

Disclaimer: the pyAML software is still under development.

This repository is pyAML core. It is control system independent and provides the main functionality of pyAML (device abstraction for magnets, bpms, etc.; access to simulator (pyAT) and abstract implementation for control system). It is intended to be used together with a package that implements control system specific interface.

If you want to only tests for your machine and not develop, you shouldn't install this package. Instead go to the package for the bindings and install that one. It will install this package automatically.

Available packages for bindings:

TANGO: [tango-pyaml](https://github.com/python-accelerator-middle-layer/tango-pyaml)
TANGO or EPICS: [pyaml-cs-oa](https://github.com/python-accelerator-middle-layer/pyaml-cs-oa)

#### Developer Installation

1. Clone the repository. You need to also update the submodules.

   ```
   cd pyaml
   git submodule update --init --recursive
   ```
2. Create a virtual environment and activate it
3. Install the package in editable mode:

   ```
   pip install -e .
   ```
4. Install the development dependencies and pre-commit hooks

   ```
   pip install -e .[dev]
   pre-commit install
   ```

5. If you want to try the examples using the control system bindings you also need to install those. See:

   TANGO: [tango-pyaml](https://github.com/python-accelerator-middle-layer/tango-pyaml)
   TANGO or EPICS: [pyaml-cs-oa](https://github.com/python-accelerator-middle-layer/pyaml-cs-oa)

6. If you want to run tests manually using the TANGO bindings without requiring a live machine you can also install the the Dummy TANGO control system available in tests/dummy-cs/tango. It is a simple emulation that allows to check the interface to the control system. The implemented control system doesn't do anything but it is only intended for tests during the development.


#### Documentation

The documentation is hosted on Read the Docs: [pyaml](https://pyaml.readthedocs.io/en/latest/?badge=latest).

#### Examples

Examples are available in the `examples` folder of the repository.
Additionally, in the documentation there are example Jupyter notebooks available.
