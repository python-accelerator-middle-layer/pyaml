"""
Generate pyAML configuration files for the SOLEIL Storage Ring
from the MML (Matlab Middle Layer) configuration in soleilinit.m.

Usage::

    python generate_config.py [--mml-file PATH] [--output-dir DIR]

Defaults:
  --mml-file   <repo_root>/mml/SOLEIL/StorageRing/soleilinit.m
  --output-dir directory containing this script
"""

import argparse
from pathlib import Path

from mml_to_pyaml.generators import (
    P_YAML,
    TUNING_TOOLS_YAML,
    generate_arrays_yaml,
    generate_catalogs_yaml,
    generate_devices_yaml,
)
from mml_to_pyaml.parsers import load_mml_data

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
_DEFAULT_MML = _REPO_ROOT / "mml/SOLEIL/StorageRing/soleilinit.m"
_DEFAULT_OUT = Path(__file__).parent


def main(mml_file: Path = _DEFAULT_MML, output_dir: Path = _DEFAULT_OUT) -> None:
    print(f"Reading MML file: {mml_file}")
    data = load_mml_data(mml_file)

    nbpms = len(data["bpms"])
    nhcors = len(data["hcors"])
    nvcors = len(data["vcors"])
    nfhcors = len(data["fhcors"])
    nfvcors = len(data["fvcors"])
    nqt = len(data["skewquads"])
    nquads = sum(len(v) for v in data["quads"].values())
    nsexts = len(data["sexts"])
    print(f"  BPMs:          {nbpms}")
    print(f"  HCORs (slow):  {nhcors}")
    print(f"  VCORs (slow):  {nvcors}")
    print(f"  FHCORs (fast): {nfhcors}")
    print(f"  FVCORs (fast): {nfvcors}")
    print(f"  SkewQuads (QT):{nqt}")
    print(f"  Quads:         {nquads} ({', '.join(f'{k}:{len(v)}' for k, v in data['quads'].items())})")
    print(f"  Sextupoles:    {nsexts}")

    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "p.yaml").write_text(P_YAML)
    print("Written: p.yaml")

    (output_dir / "devices.yaml").write_text(generate_devices_yaml(data))
    print("Written: devices.yaml")

    (output_dir / "catalogs.yaml").write_text(generate_catalogs_yaml(data))
    print("Written: catalogs.yaml")

    (output_dir / "arrays.yaml").write_text(generate_arrays_yaml(data))
    print("Written: arrays.yaml")

    (output_dir / "tuning_tools.yaml").write_text(TUNING_TOOLS_YAML)
    print("Written: tuning_tools.yaml")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert SOLEIL SR MML configuration to pyAML YAML files.")
    parser.add_argument(
        "--mml-file",
        type=Path,
        default=_DEFAULT_MML,
        help="Path to soleilinit.m (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUT,
        help="Directory to write YAML files into (default: %(default)s)",
    )
    args = parser.parse_args()
    main(mml_file=args.mml_file, output_dir=args.output_dir)
