# Instructions for how to run the ESRF ORM example.

## Install pyAML

1. Create a virtual environment and activate it. It needs to have >= Python 3.11.

2. Install pyAML including the tango bindings.

  ```bash
  pip install accelerator-middle-layer[tango]
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


  ### measure_ideal_ORM.py
  Expected output is:


  ### measure_ideal_ORM_and_disp.py
  Expected output is:


  ### measure_reduced_ORM.py
  Expected output is:
