### Main files
- Run either the Jupyter notebook
  `esrf_tune_ophyd_async_example_no_yaml.ipynb`
  or the Python script `esrf_tune_ophyd_async_example_no_yaml.py`.

- Confirmed both the Jupyter notebook and the script work with Python
  3.12 on 11/14/2025.

- You may have to manually adjust the path `set_root_folder("../../../tests")`
  in both files such that files like
  `pyaml/tests/config/sr/magnet_models/QF1_strength.csv` can be found.

- You can try the EPICS version even if you only have access to Tango,
  as `caproto` can just start up an EPICS IOC server very easily.
  However, if you only have access to EPICS, you will have to first
  set up a base Tango environment in order to try the Tango version.

### Pre-requisites for both Tango & EPICS

- You need to install `ophyd-async` in your environment with `$ pip
  install ophyd-async`

### Test Tango

- You need to have `pytango` installed in your environment. If not, run `$ pip install pytango`.

- Register and start a simple Tango server and leave this terminal open:
```bash
$ python register_device_20251103.py
$ python simple_ds_20251103.py instance1
```

- In a separate terminal, run either the Jupyter notebook or the Python
  script, but make sure that `CS_NAME = "tango"` at the top of the files.

### Test EPICS

- You need to have `aioca` and `caproto` installed in your environment.
  If not, run `$ pip install aioca caproto`.

- Start a simple EPICS IOC and leave this terminal open:
```bash
$ python simple_epics_ioc_20251103.py --prefix SIMPLE: --list-pvs
```

- In a separate terminal, run either the Jupyter notebook or the Python
  script, but make sure that `CS_NAME = "epics"` at the top of the files.
