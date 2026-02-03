# Instructions for how to run SOLEIL examples.

## Install pyAML

1. Create a virtual environment and activate it. You need to have Python 3.11+.

2. Install pyAML, including the tango-pyaml TANGO bindings.

  ```bash
  pip install accelerator-middle-layer[tango-pyaml]
  ```

## Start the SOLEIL II virtual accelerator

1. Install [Apptainer](https://apptainer.org/docs/admin/main/installation.html) in case you don't already have it.

For the live control mode, you should have some control system emulation runing. It is possible to do
```
apptainer pull virtual-accelerator.sif oras://gitlab-registry.synchrotron-soleil.fr/software-control-system/containers/apptainer/virtual-accelerator:latest
apptainer run virtual-accelerator.sif
```

***Keep this terminal running and don't do anything else in it.*** The virtual accelerator will run there and you will be able to interact with it from other terminals, jupyter notebooks, IDEs etc over the network. If you want to put it in the background, using something like tmux would be a good option.

this will run SOLEIL II proof-of-concept digital twin on localhost:11000. You can play with the digital twin itself (without pyAML) via jive to check that everything is working. You can run jive in a different terminal with
```
apptainer pull jive.sif https://gitlab.synchrotron-soleil.fr/api/v4/projects/2739/packages/generic/jive/latest/jive.sif
apptainer run jive.sif
```
On linux you may need additionally to configure X11
```
export DISPLAY=:0
xhost +local:root
```

NOTE: This is just a demonstration of pyAML functionality. Certain things may be done stupidly. The person who wrote this jupyter notebook only cared about showing that the code is working, not about intelligently controlling the accelerator.


  ## Run the examples

    There are three jupyter notebook available with some basic examples. Feel free to play around and modify them. A .yaml configuration file is already provided, it was generated procedurally from the .m lattice file and nomenclature description file.
