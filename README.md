# pyAML

**Python Accelerator Middle Layer — Core Package**

[![Documentation Status](https://readthedocs.org/projects/pyaml/badge/?version=stable)](https://pyaml.readthedocs.io/en/stable/?badge=stable)
[![Latest stable release](https://img.shields.io/pypi/v/accelerator-middle-layer.svg)](https://pypi.org/project/accelerator-middle-layer/)

## Overview

Python Accelerator Middle Layer (pyAML) is a joint technology platform for design, commissioning and operation of particle accelerators.

The pyAML core package provides a control-system-independent framework for representing and interacting with particle accelerators. It is designed to work with separate packages implementing control-system-specific interfaces, allowing accelerator models and applications to be used with different control systems.

For more information about the overall project, visit the [Python Accelerator Middle Layer homepage](https://python-accelerator-middle-layer.github.io/).

## Installation

Install from PyPI:

```bash
pip install accelerator-middle-layer
```

## Development

To contribute to pyAML, clone the repository and install it with the development and testing dependencies:

```bash
git clone https://github.com/python-accelerator-middle-layer/pyaml.git
cd pyaml
pip install -e ".[dev,test]"
```

Run the tests:

```bash
pytest
```

Install the pre-commit hooks:

```bash
pre-commit install
```

## Contributing

Contributions are very welcome. Please report issues or suggest improvements through the [GitHub issue tracker](https://github.com/python-accelerator-middle-layer/pyaml/issues), or submit a pull request. To submit a pull request, please first request membership in the project.
