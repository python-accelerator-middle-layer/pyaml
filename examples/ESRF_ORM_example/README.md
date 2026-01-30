# Instructions for how to run the ESRF ORM example.

## Install pyAML

1. Create a virtual environment and activate it. It needs to have >= Python 3.11.

2. Install pyAML including the tango bindings and SimulatedCommissioning (pySC).

  ```bash
  pip install accelerator-middle-layer[tango]
  pip install accelerator-commissioning
  ```

3. install EBS dummy Control system. This is valid untill an ESRF virtual machine will be available as for BESSYII and SOLEIL
   ```bash
   pip install tests/dummy_cs/tango-pyaml
   ```

  ## Run the examples
  Several examples are available for ORM correction.

    To run the examples:
  1. navigate to the pyaml root directory
  2. Download (or clone) the example files.
  3. run the files

  ### The correct_orbit.py  shows the standard orbit correction
  Expected output is:
    Creating dummy TangoControlSystem: live
    R.m.s. orbit before correction H:  85.1 µm, V:  24.1 µm.
    30 Jan 2026, 14:25:55 | INFO | (Re-)Building pseudoinverse RM with method='svd_values' and parameter=162 with zerosum=True.
    30 Jan 2026, 14:25:55 | INFO | (Re-)Building pseudoinverse RM with method='svd_values' and parameter=162 with zerosum=False.
    R.m.s. orbit after correction H:  0.7 µm, V:  0.4 µm,

  ### The measure_dispersion.py  shows the standard orbit correction
  Expected output is:
  30 Jan 2026, 15:05:47 | WARNING | PyAML Tango control system binding (0.3.2) initialized with name 'live' and TANGO_HOST=ebs-simu-3:10000
  Reading orbit.
  Changing RF frequency.
  Reading orbit.
  Changing RF frequency.
  Reading orbit.
  Restoring RF frequency.
  Reading orbit.


  ### measure_ideal_ORM.py
  Expected output is:

  30 Jan 2026, 15:02:25 | WARNING | PyAML Tango control system binding (0.3.2) initialized with name 'live' and TANGO_HOST=ebs-simu-3:10000
  30 Jan 2026, 15:02:27 | INFO | Measuring correctors from the default arrays: HCorr and VCorr.
  30 Jan 2026, 15:02:28 | INFO | Measured response of SH1A-C04-H.
  ...

  ### measure_ideal_ORM_and_disp.py
  Expected output is:
  as the two ouputs above

  ### measure_reduced_ORM.py
  Expected output is:
  30 Jan 2026, 15:04:26 | WARNING | PyAML Tango control system binding (0.3.2) initialized with name 'live' and TANGO_HOST=ebs-simu-3:10000
  [0/64], Measured response of SJ2A-C04-H: r.m.s H.: 5.75 mm/mrad, r.m.s. V: 0.00 mm/mrad
  [1/64], Measured response of SF2A-C05-H: r.m.s H.: 5.75 mm/mrad, r.m.s. V: 0.00 mm/mrad
  [2/64], Measured response of SF2A-C06-H: r.m.s H.: 5.75 mm/mrad, r.m.s. V: 0.00 mm/mrad
  ...
  [61/64], Measured response of SF2A-C01-V: r.m.s H.: 0.00 mm/mrad, r.m.s. V: 2.08 mm/mrad
  [62/64], Measured response of SF2A-C02-V: r.m.s H.: 0.00 mm/mrad, r.m.s. V: 2.08 mm/mrad
  [63/64], Measured response of SI2A-C03-V: r.m.s H.: 0.00 mm/mrad, r.m.s. V: 2.08 mm/mrad
