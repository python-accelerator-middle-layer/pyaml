Installation
============

Since the code is still under development the best option to get the latest version is to install directly from github.

1. Clone the repository. The repository uses submodules so they also need to be initialized. This can be done in the same step by including ``--recurse-submodules``.

    ```
    git clone --recurse-submodules https://github.com/python-accelerator-middle-layer/pyaml.git
    ```

2. Make a virtual environment and activate it. It needs to use >= Python 3.11.

3. Depending on which bindings you want to use for the control system you need to install including different dependencies.

    The available bindings are:

    - **tango-pyaml**: For TANGO. 

        ```
        pip install .[tango-pyaml]
        ```

    - **pyaml-cs-oa**: For TANGO or EPICS using `ophyd-async`.

        ```
        pip install .[pyaml-cs-oa]
        ```
