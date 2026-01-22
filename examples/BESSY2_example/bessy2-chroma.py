from pyaml.accelerator import Accelerator

sr = Accelerator.load("BESSY2Chroma.yaml")
sr.design.get_lattice().disable_6d()
# Retreive MCF from the model
alphac = sr.design.get_lattice().get_mcf()
print(f"Moment compaction factor: {alphac}")
chromaticity_monitor = sr.live.get_chromaticity_monitor("KSI")
chromaticity_monitor.chromaticity_measurement(do_plot=True, alphac=alphac)
ksi = chromaticity_monitor.chromaticity.get()
print(ksi)
