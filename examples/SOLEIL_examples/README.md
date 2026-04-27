# Instructions for how to run SOLEIL examples.

## Install pyAML

1. Create a virtual environment and activate it. You need to have Python 3.11+.

2. Install pyAML, including the tango-pyaml TANGO bindings.

  ```bash
  pip install accelerator-middle-layer[tango-pyaml]
  ```
3. Alternatively, you can install ophyd-async Tango bindings
   ```bash
    pip install accelerator-middle-layer[pyaml-cs-oa]
    ```

If this does not work, you can proceed to do a developer installation directly from git repository.
```bash
# pyAML core
git clone git@github.com:python-accelerator-middle-layer/pyaml.git
cd pyaml
pip install -e .[dev]
# pyAML TANGO bindings
git clone git@github.com:python-accelerator-middle-layer/tango-pyaml.git
cd tango-pyaml
pip install -e .
#pyAML ophyd-async bindings (supports both TANGO and EPICS)
git clone git@github.com:python-accelerator-middle-layer/pyaml-cs-oa.git
cd pyaml-cs-oa
pip install -e .
```

You can verify that everything is installed correctly by running in Python or IPython terminal the start of the examples.

```python
from pyaml.accelerator import Accelerator

sr = Accelerator.load("p.yaml")
sr  # string representation
```

The following or a similar message will be printed
```
Accelerator(facility='Synchrotron SOLEIL', machine='sr', energy=2750000000.0, controls=[TangoControlSystem(name='live', tango_host='localhost:11000', debug_level=None, lazy_devices=True, scalar_aggregator='tango.pyaml.multi_attribute', vector_aggregator=None, timeout_ms=3000)], simulators=[Simulator(name='design', lattice='SOLEIL_II_V3631_sym1_V001_database_rf.m', mat_key=None, linker=<pyaml.lattice.attribute_linker.PyAtAttributeElementsLinker object at 0x7a1ce1e9deb0>, description=None)], data_folder='/data/store', description=None)
```

pyAML has two control modes: "live" and "design" (named in the config file). "live" connects to a control system (or a control system emulator), "design" only requires pyAT lattice file and will run pyAT. If you want to avoid having any control system connection, you can delete "controls: " section from the configuration file.

### Start the SOLEIL II virtual accelerator

SOLEIL II virtual accelerator is an emulation of TANGO control system that runs pyAT under the hood.

1. Install [Apptainer](https://apptainer.org/docs/admin/main/installation.html) in case you don't already have it.

For the live control mode, you should have some control system emulation running. It is possible to do
```
apptainer pull -F virtual-accelerator.sif oras://gitlab-registry.synchrotron-soleil.fr/software-control-system/containers/apptainer/virtual-accelerator:latest
apptainer run virtual-accelerator.sif
```

***Keep this terminal running and don't do anything else in it.*** The virtual accelerator will run there, and you will be able to interact with it from other terminals, jupyter notebooks, IDEs, etc., over the network. If you want to put it in the background, using something like tmux would be a good option.

This will run SOLEIL II proof-of-concept digital twin on localhost:11000. You can play with the digital twin itself (without pyAML) via jive to check that everything is working. You can run Jive in a different terminal with
```
apptainer pull -F jive.sif https://gitlab.synchrotron-soleil.fr/api/v4/projects/2739/packages/generic/jive/latest/jive.sif
apptainer run jive.sif
```
On Linux you may need to configure X11 to display Jive
```
export DISPLAY=:0
xhost +local:root
```

NOTE: This is just a demonstration of pyAML functionality. Certain things may be done stupidly. The person who wrote this jupyter notebook only cared about showing that the code is working, not about intelligently controlling the accelerator.


  ## Run the examples

    There are three jupyter notebook available with some basic examples. Feel free to play around and modify them. The main configuration entry point is `p.yaml`; it now loads `arrays.yaml`, `devices.yaml`, and `tuning_tools.yaml`, all generated procedurally from the .m lattice file and nomenclature description file.
