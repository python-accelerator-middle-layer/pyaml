from pyaml.accelerator import Accelerator

sr = Accelerator.load("config.yaml")
print(sr.live.get_bpm("BPM_C01-01").positions.get())
