import importlib
import inspect
import os
from pathlib import Path

# List of PyAML modules to include in the API reference
# for i in `find . | grep ".py" | grep -v "cache" | grep -v "__init__"`;
# do echo "\"pyaml.${i:2:-3}\"," | tr '/' '.';
# done

modules = [
    "pyaml.accelerator",
    "pyaml.arrays.array",
    "pyaml.arrays.bpm",
    "pyaml.arrays.bpm_array",
    "pyaml.arrays.cfm_magnet",
    "pyaml.arrays.cfm_magnet_array",
    "pyaml.arrays.element",
    "pyaml.arrays.element_array",
    "pyaml.arrays.magnet",
    "pyaml.arrays.magnet_array",
    "pyaml.arrays.serialized_magnet",
    "pyaml.arrays.serialized_magnet_array",
    "pyaml.bpm.bpm",
    "pyaml.bpm.bpm_model",
    "pyaml.bpm.bpm_simple_model",
    "pyaml.bpm.bpm_tiltoffset_model",
    "pyaml.common.abstract",
    "pyaml.common.abstract_aggregator",
    "pyaml.common.constants",
    "pyaml.common.element",
    "pyaml.common.element_holder",
    "pyaml.common.exception",
    "pyaml.configuration.csvcurve",
    "pyaml.configuration.csvmatrix",
    "pyaml.configuration.curve",
    "pyaml.configuration.factory",
    "pyaml.configuration.fileloader",
    "pyaml.configuration.inline_curve",
    "pyaml.configuration.inline_matrix",
    "pyaml.configuration.matrix",
    "pyaml.control.abstract_impl",
    "pyaml.control.controlsystem",
    "pyaml.control.deviceaccess",
    "pyaml.control.deviceaccesslist",
    "pyaml.control.readback_value",
    "pyaml.diagnostics.chromaticity_monitor",
    "pyaml.diagnostics.tune_monitor",
    "pyaml.external.pySC_interface",
    "pyaml.lattice.abstract_impl",
    "pyaml.lattice.attribute_linker",
    "pyaml.lattice.element",
    "pyaml.lattice.lattice_elements_linker",
    "pyaml.lattice.polynom_info",
    "pyaml.lattice.simulator",
    "pyaml.magnet.cfm_magnet",
    "pyaml.magnet.corrector",
    "pyaml.magnet.function_mapping",
    "pyaml.magnet.hcorrector",
    "pyaml.magnet.identity_cfm_model",
    "pyaml.magnet.identity_model",
    "pyaml.magnet.linear_cfm_model",
    "pyaml.magnet.linear_model",
    "pyaml.magnet.linear_serialized_model",
    "pyaml.magnet.magnet",
    "pyaml.magnet.model",
    "pyaml.magnet.octupole",
    "pyaml.magnet.quadrupole",
    "pyaml.magnet.serialized_magnet",
    "pyaml.magnet.sextupole",
    "pyaml.magnet.skewoctu",
    "pyaml.magnet.skewquad",
    "pyaml.magnet.skewsext",
    "pyaml.magnet.spline_model",
    "pyaml.magnet.vcorrector",
    "pyaml.rf.rf_plant",
    "pyaml.rf.rf_transmitter",
    # "pyaml.tuning_tools.LOCO.loco",
    # "pyaml.tuning_tools.SOFB.sofb",
    "pyaml.tuning_tools.dispersion",
    "pyaml.tuning_tools.orbit",
    "pyaml.tuning_tools.orbit_response_matrix",
    "pyaml.tuning_tools.response_matrix",
    "pyaml.tuning_tools.tune",
]


def generate_selective_module(m):
    # Module introspection
    p = importlib.import_module(m)
    classes = inspect.getmembers(p, inspect.isclass)
    all_cls = []
    for clsname, c in classes:
        if c.__module__ == p.__name__:
            # ConfigModel at the beginning if present
            if "ConfigModel" in clsname:
                all_cls.insert(0, c)
            else:
                all_cls.append(c)

    # Generate mddule
    if len(all_cls) > 0:
        with open(f"api/{p.__name__}.rst", "w") as file:
            title = p.__name__.split(".")[-1:][0]
            file.write(f"{title}\n")
            file.write("-" * len(title) + "\n\n")
            # file.write("   .. rubric:: Classes\n\n")
            file.write(f".. automodule:: {p.__name__}\n")
            file.write(
                f"   :exclude-members: {','.join([c.__name__ for c in all_cls])}\n\n"
            )
            for c in all_cls:
                file.write(f"   .. autoclass:: {c.__name__}\n")
                file.write("         :members:\n")
                file.write("         :exclude-members: model_config\n")
                file.write("         :undoc-members:\n")
                file.write("         :show-inheritance:\n\n")


def generate_toctree(filename: str, title: str, level: int, module: str):
    sub_modules = [m for m in modules if m.startswith(module)]
    level_path = set([m.split(".")[level + 1 : level + 2][0] for m in sub_modules])
    paths = []

    with open(f"{filename}", "w") as file:
        file.write(f"{title}\n")
        file.write("=" * len(title) + "\n\n")
        file.write(".. toctree::\n")

        file.write("   :maxdepth: 1\n")
        file.write("   :caption: PyAML packages:\n\n")

        for p in level_path:
            module_name = module + "." + p
            if level == 0:
                file.write(f"   api/{module_name}\n")
            else:
                file.write(f"   {module_name}\n")
            if module_name not in modules:
                paths.append(p)
            else:
                generate_selective_module(module_name)

    return paths


# Generate toctrees
paths = generate_toctree("api.rst", "API Reference", 0, "pyaml")
level = 1
while len(paths) > 0:
    for p in paths:
        paths = generate_toctree(f"api/{'pyaml.' + p}.rst", f"{p}", level, "pyaml." + p)
    level += 1
