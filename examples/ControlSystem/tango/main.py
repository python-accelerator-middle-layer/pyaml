from pyaml.accelerator import Accelerator

sr = Accelerator.load("config.yaml")

# print the BPM position
bpm = sr.live.get_bpm("BPM_C01-01")  # bpm is a BPM
print(bpm.positions.get())

# Direct access to control system
da = sr.live.get_device("srdiag/bpm/c01-01/SA_HPosition")  # da is a DeviceAccess
print(f"h={da.get()} {da.unit()}")
