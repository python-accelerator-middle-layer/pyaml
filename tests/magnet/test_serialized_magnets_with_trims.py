"""YAML loading and holder access for serialized families and their trim magnets."""

import at
import pytest
import yaml

from pyaml.accelerator import Accelerator
from pyaml.lattice.abstract_impl import RWStrengthScalar
from pyaml.magnet.serialized_magnet_trims import SerializedMagnetsWithTrims


@pytest.fixture
def trim_config(tmp_path):
    lattice_file = tmp_path / "ring.mat"
    ring = at.Lattice(
        [at.Dipole(name, 1.0, bending_angle=0.01) for name in ["DF8B-C04", "DF8D-C04", "DD5D-C04"]],
        energy=6e9,
    )
    at.save_lattice(ring, lattice_file)
    config = {
        "type": "pyaml.accelerator",
        "facility": "ESRF",
        "machine": "sr",
        "energy": 6e9,
        "simulators": [{"type": "pyaml.lattice.simulator", "name": "design", "lattice": str(lattice_file)}],
        "devices": [
            {
                "class": "pyaml.magnet.serialized_magnet_trims.SerializedMagnetsWithTrims",
                "name": "series",
                "function": "B0",
                "elements": ["DF8B-C04", "DF8D-C04", "DD5D-C04"],
                "model": {
                    "class": "pyaml.magnet.linear_serialized_with_trims_model.LinearSerializedMagnetWithTrimsModel",
                    "unit": "rad",
                    "hardware_unit": "A",
                    "curves": {"type": "pyaml.magnet.inline_curve", "mat": [[0, 0], [1, 1], [2, 4], [3, 9], [4, 16]]},
                    "powerconverter": "test/series/main/current",
                    "trims": [
                        {
                            "class": "pyaml.magnet.trim_coil.TrimCoil",
                            "element": "DF8D-C04",
                            "name": "T2",
                            "trim_factor": -2.0,
                            "hardware_unit": "trim A",
                            "powerconverter": "test/series/trim2/current",
                        },
                        {
                            "class": "pyaml.magnet.trim_coil.TrimCoil",
                            "element": "DF8B-C04",
                            "name": "T1",
                            "powerconverter": "test/series/trim1/current",
                        },
                    ],
                },
            }
        ],
    }

    filename = tmp_path / "trims.yaml"
    filename.write_text(yaml.safe_dump(config))
    return Accelerator.load(str(filename))


def test_yaml_and_trim_holders(trim_config):
    holder = trim_config.design
    family = holder.serialized_magnet.get("series")
    assert isinstance(family, SerializedMagnetsWithTrims)
    assert family.names() == ["DF8B-C04", "DF8D-C04", "DD5D-C04"]
    assert len(family) == len(family.get_magnets()) == 3
    assert [trim.name for trim in family.get_trim_magnets()] == ["T2", "T1"]
    assert holder.magnet.get("T2") is family.get_trim_magnets()[0]
    assert set(holder.magnet["T*"].names()) == {"T1", "T2"}
    for trim, member, unit in [(holder.magnet["T2"], family[1], "trim A"), (holder.magnet["T1"], family[0], "A")]:
        assert type(trim) is type(member)
        assert trim.model.serialized_model is family.model
        assert not trim.model.shares_power_supply()
        assert holder.get_at_elems(trim) == holder.get_at_elems(member)
        assert trim.series_index is None
        assert trim.hardware.unit() == unit
        assert trim.strength.unit() == "rad"
        assert trim.strength.get() == 0
        total = RWStrengthScalar(
            holder.get_at_elems(member), member.polynom, member.model.get_sub_model(family.names().index(member.name))
        )
        assert total.get() == pytest.approx(member.strength.get())
