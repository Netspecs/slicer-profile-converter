"""
gcode_translate.py
==================

Custom start/end G-code uses different *template variable* dialects across
slicers:

* PrusaSlicer / SuperSlicer use square brackets:      ``[first_layer_temperature]``
* OrcaSlicer / Bambu / Snapmaker use curly braces and
  usually index the first extruder:                   ``{first_layer_temperature[0]}``
  or plain ``{nozzle_temperature_initial_layer[0]}``

Within the OrcaSlicer JSON family (Bambu <-> Orca <-> Snapmaker) the dialect
is the same, so translation there is a no-op. The bracket<->brace mapping is
mainly needed when converting to/from PrusaSlicer-style ``.ini`` profiles.

This module keeps the mapping in one place and reports any variables it could
not confidently translate so the user can review them.
"""

from __future__ import annotations

import re
from typing import List, Tuple


# Map PrusaSlicer variable names -> OrcaSlicer variable names (best-effort).
# Only names that genuinely differ are listed; identical names pass through.
PRUSA_TO_ORCA_VARS = {
    "first_layer_temperature": "nozzle_temperature_initial_layer",
    "temperature": "nozzle_temperature",
    "first_layer_bed_temperature": "bed_temperature_initial_layer",
    "bed_temperature": "hot_plate_temp",
    "filament_type": "filament_type",
    "layer_height": "layer_height",
    "first_layer_height": "initial_layer_print_height",
    "nozzle_diameter": "nozzle_diameter",
    "print_speed": "outer_wall_speed",
}

ORCA_TO_PRUSA_VARS = {v: k for k, v in PRUSA_TO_ORCA_VARS.items()}


def prusa_to_orca_gcode(text: str) -> Tuple[str, List[str]]:
    """Convert PrusaSlicer ``[var]`` style G-code to OrcaSlicer ``{var[0]}``.

    Returns (converted_text, warnings). Warnings list bracket variables that
    had no known mapping (kept as-is inside braces for manual review).
    """
    if not text:
        return text, []

    warnings: List[str] = []

    def repl(match: re.Match) -> str:
        var = match.group(1).strip()
        if var in PRUSA_TO_ORCA_VARS:
            return "{" + PRUSA_TO_ORCA_VARS[var] + "[0]}"
        # Unknown variable: keep it but flag it.
        warnings.append(var)
        return "{" + var + "}"

    # Match [word] but NOT things already inside conditionals like [if ...].
    converted = re.sub(r"\[([a-zA-Z_][a-zA-Z0-9_]*)\]", repl, text)
    return converted, warnings


def orca_to_prusa_gcode(text: str) -> Tuple[str, List[str]]:
    """Convert OrcaSlicer ``{var[0]}`` / ``{var}`` style to PrusaSlicer ``[var]``."""
    if not text:
        return text, []

    warnings: List[str] = []

    def repl(match: re.Match) -> str:
        var = match.group(1).strip()
        if var in ORCA_TO_PRUSA_VARS:
            return "[" + ORCA_TO_PRUSA_VARS[var] + "]"
        warnings.append(var)
        return "[" + var + "]"

    # Match {word} or {word[0]} -> strip optional [index].
    converted = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?:\[\d+\])?\}", repl, text)
    return converted, warnings


def translate_gcode(text: str, src_family: str, dst_family: str) -> Tuple[str, List[str]]:
    """Translate G-code between slicer families.

    Families: ``"orca"`` (Bambu/Orca/Snapmaker) or ``"prusa"`` (Prusa/Super).
    Same-family translation is a no-op.
    """
    if src_family == dst_family:
        return text, []
    if src_family == "prusa" and dst_family == "orca":
        return prusa_to_orca_gcode(text)
    if src_family == "orca" and dst_family == "prusa":
        return orca_to_prusa_gcode(text)
    return text, []


if __name__ == "__main__":
    sample = "M104 S[first_layer_temperature] ; heat\nM140 S[first_layer_bed_temperature]\nG28 ; [unknown_var]"
    out, warn = prusa_to_orca_gcode(sample)
    print(out)
    print("warnings:", warn)
    assert "{nozzle_temperature_initial_layer[0]}" in out
    assert "unknown_var" in warn
    print("OK")
