"""
Parse SOLEIL Storage Ring MML configuration (soleilinit.m).

Each ``parse_*`` function returns a list of dicts, one per device.
``load_mml_data`` calls all of them and returns a single dict keyed by
family name.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _extract_block(text: str, start_marker: str, end_marker: str) -> str:
    """Return the substring of *text* between *start_marker* and *end_marker*."""
    start = text.find(start_marker)
    if start == -1:
        raise ValueError(f"Marker not found: {start_marker!r}")
    end = text.find(end_marker, start)
    if end == -1:
        raise ValueError(f"End marker not found after start: {end_marker!r}")
    return text[start:end]


# ---------------------------------------------------------------------------
# Family parsers
# ---------------------------------------------------------------------------


def parse_bpm_varlist(block: str) -> list[dict]:
    """Parse BPM varlist rows.

    Expected row format::

        <elem>  [<sector> <num>]  '<tango_device>'  <status>  '<common>'
    """
    pattern = re.compile(
        r"""^\s*(\d+)\s+\[\s*(\d+)\s+(\d+)\s*\]\s*'([^']+)'\s+(\d+)\s+'(\w+)'""",
        re.MULTILINE,
    )
    entries = []
    for m in pattern.finditer(block):
        entries.append(
            {
                "elem": int(m.group(1)),
                "sector": int(m.group(2)),
                "bpm_num": int(m.group(3)),
                "device": m.group(4).strip(),
                "status": int(m.group(5)),
                "name": m.group(6).strip(),
            }
        )
    return entries


def parse_cor_varlist(block: str) -> list[dict]:
    """Parse slow-corrector varlist rows (HCOR / VCOR).

    Expected row format::

        <elem>  [<sector> <num>]  '<tango_device>'  <status>  '<common>'
        '<attr_read>'  '<attr_write>'  [<min> <max>]
    """
    pattern = re.compile(
        r"""^\s*(\d+)\s+\[\s*(\d+)\s+(\d+)\s*\]\s*'([^']+)'\s+(\d+)\s+'(\w+)'\s*'(\w+)\s*'\s*'(\w+)\s*'\s*\[\s*([-\d.]+)\s+([-\d.]+)\s*\]""",
        re.MULTILINE,
    )
    entries = []
    for m in pattern.finditer(block):
        entries.append(
            {
                "elem": int(m.group(1)),
                "sector": int(m.group(2)),
                "cor_num": int(m.group(3)),
                "device": m.group(4).strip(),
                "status": int(m.group(5)),
                "name": m.group(6).strip(),
                "attr_read": m.group(7).strip(),
                "attr_write": m.group(8).strip(),
                "range_min": float(m.group(9)),
                "range_max": float(m.group(10)),
            }
        )
    return entries


def parse_fcor_varlist(block: str) -> list[dict]:
    """Parse fast-corrector varlist rows (FHCOR / FVCOR).

    Same column layout as slow correctors; reuses :func:`parse_cor_varlist`.
    """
    return parse_cor_varlist(block)


def parse_skewquad_varlist(block: str) -> list[dict]:
    """Parse skew-quadrupole (QT) varlist rows.

    Expected row format::

        <elem>  [<sector> <num>]  '<tango_device>'  <status>  '<common>'
        [<min> <max>]
    """
    pattern = re.compile(
        r"""^\s*(\d+)\s+\[\s*(\d+)\s+(\d+)\s*\]\s*'([^']+)'\s+(\d+)\s+'(\w+)'\s*\[\s*([-\d.]+)\s+([-\d.]+)\s*\]""",
        re.MULTILINE,
    )
    entries = []
    for m in pattern.finditer(block):
        entries.append(
            {
                "elem": int(m.group(1)),
                "sector": int(m.group(2)),
                "qt_num": int(m.group(3)),
                "device": m.group(4).strip(),
                "status": int(m.group(5)),
                "name": m.group(6).strip(),
                "range_min": float(m.group(7)),
                "range_max": float(m.group(8)),
            }
        )
    return entries


def parse_quad_varlist(block: str) -> list[dict]:
    """Parse quadrupole varlist rows (Q1..Q12)."""
    pattern = re.compile(
        r"""^\s*(\d+)\s+\[\s*(\d+)\s+(\d+)\s*\]\s*'([^']+)'\s+(\d+)\s+'([^']+)'\s+\[\s*([-+\d.]+)\s+([-+\d.]+)\s*\]""",
        re.MULTILINE,
    )
    entries = []
    for m in pattern.finditer(block):
        entries.append(
            {
                "elem": int(m.group(1)),
                "sector": int(m.group(2)),
                "quad_num": int(m.group(3)),
                "device": m.group(4).strip(),
                "status": int(m.group(5)),
                "name": m.group(6).strip(),
                "range_min": float(m.group(7)),
                "range_max": float(m.group(8)),
            }
        )
    return entries


def parse_sext_varlist(block: str) -> list[dict]:
    """Parse sextupole power-supply varlist rows (S1..S12)."""
    pattern = re.compile(
        r"""^\s*(\d+)\s+\[\s*(\d+)\s+(\d+)\s*\]\s*'([^']+)'\s+(\d+)\s+'(\S+)\s*'\s*\[\s*([-+\d.]+)\s+([-+\d.]+)\s*\]""",
        re.MULTILINE,
    )
    entries = []
    for m in pattern.finditer(block):
        entries.append(
            {
                "elem": int(m.group(1)),
                "sector": int(m.group(2)),
                "sext_num": int(m.group(3)),
                "device": m.group(4).strip(),
                "status": int(m.group(5)),
                "name": m.group(6).strip(),
                "range_min": float(m.group(7)),
                "range_max": float(m.group(8)),
            }
        )
    return entries


def parse_memberof_roles(text: str) -> dict[str, list[str]]:
    """Parse ``AO.<Family>.MemberOf = {...  '<Role>'}`` appending assignments.

    Returns a dict mapping role name → list of family names that carry it.
    Example::

        {'Tune Corrector': ['Q7', 'Q9'],
         'Chromaticity Corrector': ['S9', 'S10']}
    """
    pattern = re.compile(
        r"""AO\.(\w+)\.MemberOf\s*=\s*\{AO\.\w+\.MemberOf\{:\}\s*'([^']+)'\}""",
        re.MULTILINE,
    )
    roles: dict[str, list[str]] = {}
    for m in pattern.finditer(text):
        family = m.group(1)
        role = m.group(2)
        roles.setdefault(role, []).append(family)
    return roles
    """Parse sextupole power-supply varlist rows (S1..S12)."""
    # pattern = re.compile(
    #     r"""^\s*(\d+)\s+\[\s*(\d+)\s+(\d+)\s*\]\s*'([^']+)'\s+(\d+)\s+'(\S+)\s*'\s*\[\s*([-+\d.]+)\s+([-+\d.]+)\s*\]""",
    #     re.MULTILINE,
    # )
    # entries = []
    # for m in pattern.finditer(block):
    #     entries.append(
    #         {
    #             "elem": int(m.group(1)),
    #             "sector": int(m.group(2)),
    #             "sext_num": int(m.group(3)),
    #             "device": m.group(4).strip(),
    #             "status": int(m.group(5)),
    #             "name": m.group(6).strip(),
    #             "range_min": float(m.group(7)),
    #             "range_max": float(m.group(8)),
    #         }
    #     )
    # return entries
    #
    #


# ---------------------------------------------------------------------------
# Top-level loader
# ---------------------------------------------------------------------------


def load_mml_data(mml_path: Path) -> dict:
    """Parse *soleilinit.m* and return all device families as a dict."""
    text = mml_path.read_text(encoding="utf-8")

    # --- BPMs ---
    bpm_block = _extract_block(
        text,
        "% ElemList devlist tangoname status common\nvarlist = {",
        "AO.(ifam).Monitor.TangoNames{k}  = strcat(AO.(ifam).DeviceName{k}, '/XPosSA')",
    )
    bpms = parse_bpm_varlist(bpm_block)

    # --- Slow HCORs ---
    hcor_block = _extract_block(
        text,
        "% elemlist devlist tangoname       status  common  attR           attW      range\nvarlist = {",
        "AO.(ifam).Monitor.TangoNames(k)  = strcat(AO.(ifam).DeviceName{k}, '/', deblank(varlist(k,6)));",
    )
    hcors = parse_cor_varlist(hcor_block)

    # --- Slow VCORs ---
    vcor_section_start = text.find("%% SLOW VERTICAL CORRECTORS")
    vcor_block_start = text.find("varlist = {", vcor_section_start)
    vcor_block_end = text.find(
        "AO.(ifam).Monitor.TangoNames(k)  = strcat(AO.(ifam).DeviceName{k}, '/', deblank(varlist(k,6)));",
        vcor_block_start,
    )
    vcors = parse_cor_varlist(text[vcor_block_start:vcor_block_end])

    # --- Fast HCORs ---
    fhcor_section_start = text.find("%% FAST HORIZONTAL CORRECTORS")
    fhcor_block_start = text.find("varlist = {", fhcor_section_start)
    fhcor_block_end = text.find("};", fhcor_block_start) + 2
    fhcors = parse_fcor_varlist(text[fhcor_block_start:fhcor_block_end])

    # --- Fast VCORs ---
    fvcor_section_start = text.find("%% FAST VERTICAL CORRECTORS")
    fvcor_block_start = text.find("varlist = {", fvcor_section_start)
    fvcor_block_end = text.find("};", fvcor_block_start) + 2
    fvcors = parse_fcor_varlist(text[fvcor_block_start:fvcor_block_end])

    # --- Skew Quadrupoles (QT) ---
    qt_section_start = text.find("%% Skew Quadrupole data\n")
    qt_block_start = text.find("varlist = {", qt_section_start)
    qt_block_end = text.find("};", qt_block_start) + 2
    skewquads = parse_skewquad_varlist(text[qt_block_start:qt_block_end])

    # --- Quadrupoles Q1..Q12 ---
    quads: dict[str, list[dict]] = {}
    quad_section_start = text.find("%% QUADRUPOLE MAGNETS")
    quad_section_end = text.find("%% All quadrupoles", quad_section_start)
    quad_section = text[quad_section_start:quad_section_end]
    for k in range(1, 13):
        key = f"Q{k}"
        sub_start = quad_section.find(f"varlist.{key}={{")
        if sub_start == -1:
            sub_start = quad_section.find(f"varlist.{key}= {{")
        if sub_start == -1:
            continue
        sub_end = quad_section.find("};", sub_start) + 2
        quads[key] = parse_quad_varlist(quad_section[sub_start:sub_end])

    # --- Sextupoles S1..S12 (one power supply each) ---
    sext_start = text.find("%% SEXTUPOLE MAGNETS")
    sext_block_start = text.find("\nvarlist={", sext_start)
    sext_block_end = text.find("};", sext_block_start) + 2
    sexts = parse_sext_varlist(text[sext_block_start:sext_block_end])

    return {
        "bpms": bpms,
        "hcors": hcors,
        "vcors": vcors,
        "fhcors": fhcors,
        "fvcors": fvcors,
        "skewquads": skewquads,
        "quads": quads,
        "sexts": sexts,
        "roles": parse_memberof_roles(text),
    }
