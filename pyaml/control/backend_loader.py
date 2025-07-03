import os
import importlib

def load_backend():
    backend = detect_backend()
    module_name = f"{backend}-pyaml"
    try:
        module = importlib.import_module(module_name)
        return module
    except ImportError:
        raise ImportError(f"Backend module '{module_name}' not found. Ensure it is installed.")

def detect_backend():
    if 'FORCED_PYAML_CS' in os.environ and len(os.environ['FORCED_PYAML_CS'])>0:
        return os.environ['FORCED_PYAML_CS']
    if 'TANGO_HOST' in os.environ:
        return 'tango'
    elif 'EPICS_CA_ADDR_LIST' in os.environ or 'EPICS_CA_SERVER_PORT' in os.environ:
        return 'epics'
    else:
        raise RuntimeError("Unknown control system: set TANGO_HOST, EPICS_CA_ADDR_LIST, FORCED_PYAML_CS")
