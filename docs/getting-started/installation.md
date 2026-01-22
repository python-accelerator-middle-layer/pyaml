Installation
==================

## User Installation

The latest release can be installed from PyPI. If you want to communicate with a control system you in addition need to install the bindings you want by specifing extras.

You need at least Python 3.11.

**Remember to always install in a virtual environment to avoid breaking your Python environment.**

### Installing without Control System Bindings


For example if you just want to use the simulator.

```
pip install accelerator-middle-layer
```


### Installing with Control System Bindings

Available options for installing with control system bindings are:

- `tango-pyaml` for the tango-pyaml bindings.
-  `cs-oa-epics` for `ophyd-async` bindings with both EPICS channel and PV access.
-  `cs-oa-tango` for `ophyd-async` bindings for TANGO.

Example usage:

```
pip install accelerator-middle-layer[cs-oa-epics] 
```

## Developer Installation

To do development work you need to clone the source code from GitHub and install in editable mode.

**Note: if you are not a maintainer of the code and have write permissions to the repository you need to first fork the repository.**

1. Clone the repository (or your fork)

    The repository uses submodules so they also need to be initialized. This can be done in the same step by including ``--recurse-submodules``.

    Example usage:

    ```
    git clone --recurse-submodules https://github.com/python-accelerator-middle-layer/pyaml.git
    ```

2. Make a virtual environment and activate it. It needs to use >= Python 3.11.

3. Install the code in editable mode including development dependencies.

    ```
    cd pyaml
    pip install -e .[dev]
    ```

4. Install the pre-commit hooks.

    ```
    pre-commit install
    ```

5. Install control system bindings *(optional)*

    If you want to use control system bindings you need to also install the package for the binding you want to use. Follow the installation instructions in the corresponding repository.
    
    If you want to do development work on the bindings they need to be installed in editable mode, but if not you can install the latest release from PyPI.

6. Install dummy control system for TANGO *(optional)*

    If you want to test the TANGO bindings without requiring a live machine or virtual accelerator you can install the dummy TANGO control system available in `tests/dummy-cs/tango`. It is a simple emulation that allows to check the interface to the control system. The control system doesn't do anything but is only intended for tests during development.
