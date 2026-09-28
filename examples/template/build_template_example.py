from pyaml.accelerator import Accelerator

sr = Accelerator.load("templated_config.yaml")
for dev in sr._devices:
    print(dev)
