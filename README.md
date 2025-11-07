[![Documentation Status](https://readthedocs.org/projects/pyaml/badge/?version=latest)](https://pyaml.readthedocs.io/en/latest/?badge=latest)

# pyAML: Python Accelerator Middle Layer

Disclaimer: the pyAML software is still under development.

#### Installation

1. Clone the repository
2. Create a virtual environment and activate it
3. Install the package. For editable installation:
   
   ```
   cd pyaml
   pip install -e .
   ```
4. If you want to try the examples using the TANGO bindings you also need [tango-pyaml](https://github.com/python-accelerator-middle-layer/tango-pyaml).
   Clone that repository and install the package inside the same virtual environment as the `pyaml` package.
   tango-pyaml will automatically install pyaml, so step 3 can be skipped.
5. For tests, you may want to install dummy-cs/tango available in
   tests/dummy-cs/tango

#### Documentation

The documentation is hosted on Read the Docs: [pyaml](https://pyaml.readthedocs.io/en/latest/?badge=latest).

#### Examples

Examples are available in the `examples` folder of the repository.
Additionally, in the documentation there are example Jupyter notebooks available.
