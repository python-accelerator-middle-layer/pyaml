[![Documentation Status](https://readthedocs.org/projects/pyaml/badge/?version=latest)](https://pyaml.readthedocs.io/en/latest/?badge=latest)
![Current release](https://img.shields.io/github/v/tag/python-accelerator-middle-layer/pyaml)

# pyAML: Python Accelerator Middle Layer

Disclaimer: the pyAML software is still under development.

#### User Installation

1. Clone the repository
2. Create a virtual environment and activate it
3. Install the package.

   ```
   cd pyaml
   pip install .
   ```
   
4. If you want to try the examples using the TANGO bindings you also need [tango-pyaml](https://github.com/python-accelerator-middle-layer/tango-pyaml).
   Clone that repository and install the package inside the same virtual environment as the `pyaml` package.
   tango-pyaml will automatically install pyaml, so step 3 can be skipped.

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
   
5. If you want to try the examples using the TANGO bindings you also need [tango-pyaml](https://github.com/python-accelerator-middle-layer/tango-pyaml).
   Clone that repository and install the package inside the same virtual environment as the `pyaml` package.
   tango-pyaml will automatically install pyaml, so step 3 can be skipped.
   
7. For tests, you may want to install dummy-cs/tango available in
   tests/dummy-cs/tango


#### Documentation

The documentation is hosted on Read the Docs: [pyaml](https://pyaml.readthedocs.io/en/latest/?badge=latest).

#### Examples

Examples are available in the `examples` folder of the repository.
Additionally, in the documentation there are example Jupyter notebooks available.
