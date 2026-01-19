[![Documentation Status](https://readthedocs.org/projects/pyaml/badge/?version=latest)](https://pyaml.readthedocs.io/en/latest/?badge=latest)
![Current release](https://img.shields.io/github/v/tag/python-accelerator-middle-layer/pyaml)

# Python Accelerator Middle Layer

Python Accelerator Middle Layer (pyAML) is a joint technology platform for design, commissioning and operation of particle accelerators.

The code is still under development. The features include among others:

- A control system agnostic interface to interact with the accelerator.
- Same interface to different backends: live accelerator, virtual accelerator and simulator.
- Machine independence allowing configuration of different type of accelerators and facility specific naming conventions.
- Unit conversions.
- Automatic generation of metadata and standardized format for measurement data.
- A set of standard applications and a framework for developing new applications.

**This repository is for the core of pyAML.** It is control system independent and provides the core functionality of pyAML. It is intended to be used together with a package that implements the control system specific interface.

Available packages for bindings:

TANGO: [tango-pyaml](https://github.com/python-accelerator-middle-layer/tango-pyaml)  
TANGO or EPICS: [pyaml-cs-oa](https://github.com/python-accelerator-middle-layer/pyaml-cs-oa)

### Installation

Installation instructions for both user and development installation can be found in the [documentation](https://pyaml.readthedocs.io/en/latest/?badge=latest)

#### Documentation

The documentation is available [here](https://pyaml.readthedocs.io/en/latest/?badge=latest).

In the documentation there is both examples and Jupyter notebooks available for how to use the package.
