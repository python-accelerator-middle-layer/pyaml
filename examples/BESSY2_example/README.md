# Instructions for how to run the BESSY II examples.

## Install pyAML

1. Create a virtual environment and activate it. It needs to have >= Python 3.11.

2. Install pyAML including the ophyd-async EPICS bindings.

  ```bash
  pip install accelerator-middle-layer[cs-ao-epics]
  ```

## Start the BESSY II virtual accelerator

1. Install [Apptainer](https://apptainer.org/docs/admin/main/installation.html) in case you don't already have it.

2. Open a terminal and start the container.

  ```bash
  apptainer run oras://registry.hzdr.de/digital-twins-for-accelerators/containers/pyat-softioc-digital-twin:default-v0-5-1-bessy.2711893
  ```

  ***Keep this terminal running and don't do anything else in it.*** The virtual accelerator will run there and you will be able to interact with it from other terminals, jupyter notebooks, IDEs etc over the network.

3. If you want to see which PVs are available in the twin you need EPICS tools. A separate container is available for this.

  Open a new terminal and start the container.

  ```bash
  apptainer run oras://registry.hzdr.de/digital-twins-for-accelerators/epics-tools:latest
  ```

  In the container run `pvlist`. It will output something like:

  ```
  GUID 0x15EB588C5158BCD5284BE8F0 version 2: tcp@[ 134.30.9.13:5075 134.30.190.240:5075 ]
  ```

  To see the list of available PVs do:

  ```
  pvlist 0x15EB588C5158BCD5284BE8F0
  ```

  You will see that all PVs start with a prefix corresponding to your username. This is to make the PVs for your virtual accelerator instance unique on the network.


  ## Run the examples

  1. Download (or clone) the example files. They exist both as a notebook or scripts depending on what you prefer to use.

  2. Edit the yaml config files so the control system prefix matches the prefix for your virtual accelerator or you won't be able to connect to it. This is the part to change:

  ```yaml
  controls:
    - type: pyaml_cs_oa.controlsystem
      prefix: "your_prefix:"
      name: live
  ```
