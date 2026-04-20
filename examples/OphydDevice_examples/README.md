# Ophyd tune device exmaple

This exmaple demonstrate how to add an OphydDevice for the tune monitor.

## Install pyAML

1. Create a virtual environment and activate it. It needs to have >= Python 3.11.

2. Install pyAML including the ophyd-async EPICS bindings.

  ```bash
  pip install accelerator-middle-layer[cs-ao-epics]
  ```

## Start the BESSY II virtual accelerator

1. Install [Apptainer](https://apptainer.org/docs/admin/main/installation.html) by following the instructions in the [documentation](https://pyaml.readthedocs.io/en/latest/how-to/apptainer.html).


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

  Edit tune_ophyd_device.py and update the folloing line with your prefix:

  ```
  "validation_class": "MyControlSystemConfigModel",
  "prefix": "your_prefix:",
  "name": "live",

  ```

## Run the example


  python tune_ophyd_device.py


  ```
  [0.8474559579136044, 0.726251084424095]
  [1059.3199473920054, 907.8138555301188]
  ```
