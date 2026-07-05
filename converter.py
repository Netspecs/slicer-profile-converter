"""
converter.py
============

Core conversion engine. Converts an OrcaSlicer-family profile (Bambu Studio,
OrcaSlicer, Snapmaker Orca) so it can be used in a different slicer of the same
family, targeting a specific printer in the destination slicer.

Because the three slicers share the same JSON schema, "conversion" is mostly:

1. **Flatten inheritance** so the profile is self-contained and won't vanish in
   the target because a parent is missing.
2. **Retarget printer compatibility** -- rewrite ``compatible_printers`` (and the
   condition string) to the destination printer name the user picked.
3. **Fix identity fields** -- ``name`` (add a suffix so it's obviously a converted
   copy), mark it as a user/custom preset, drop source-only ids that would clash.
4. **Translate G-code** if crossing dialects (only needed for the Prusa family).
5. **Produce a report** of everything changed, plus anything that may need a
   human's eyes (unknown keys, missing parents, unmapped G-code vars).

The result is a dict ready to be written with ``profile_io.save_json``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from gcode_translate import translate_gcode
from profile_io import profile_name, resolve_inheritance

# Slicer key -> template dialect family.
FAMILY = {
    "bambu": "orca",
    "orca": "orca",
    "snapmaker": "orca",
    "prusa": "prusa",
    "super": "prusa",
}

# Keys that carry custom start/end G-code (translated when crossing dialects).
GCODE_KEYS = (
    "machine_start_gcode", "machine_end_gcode", "before_layer_change_gcode",
    "layer_change_gcode", "change_filament_gcode", "machine_pause_gcode",
    "start_gcode", "end_gcode",  # prusa-style names
)

# Identity/source-only keys that should be dropped or reset on the converted copy
# so the destination slicer treats it as a fresh user preset.
_DROP_KEYS = (
    "setting_id", "filament_id", "user_id", "base_id", "update_time",
)

# compatibility keys we rewrite to the destination printer.
_COMPAT_KEYS = ("compatible_printers", "compatible_printers_condition")


@dataclass
class ConversionReport:
    """Human-readable record of what happened during a conversion."""

    source_name: str = ""
    target_name: str = ""
    profile_type: str = ""
    src_slicer: str = ""
    dst_slicer: str = ""
    inheritance_chain: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [
            "Slicer Profile Conversion Report",
            "=" * 34,
            f"Profile type : {self.profile_type}",
            f"Source       : {self.source_name}  ({self.src_slicer})",
            f"Target       : {self.target_name}  ({self.dst_slicer})",
            "",
        ]
        if self.inheritance_chain:
            lines.append("Inheritance flattened (parent-first):")
            for p in self.inheritance_chain:
                lines.append(f"  - {p}")
            lines.append("")
        lines.append("Changes made:")
        lines.extend(f"  * {c}" for c in (self.changes or ["(none)"]))
        lines.append("")
        lines.append("Needs review / warnings:")
        if self.warnings:
            lines.extend(f"  ! {w}" for w in self.warnings)
        else:
            lines.append("  (none -- clean conversion)")
        return "\n".join(lines)


def convert_profile(
    data: dict,
    profile_type: str,
    src_slicer: str,
    dst_slicer: str,
    target_printer: str,
    search_dirs: Optional[List[str]] = None,
    name_suffix: Optional[str] = None,
) -> (dict, ConversionReport):
    """Convert one profile dict for use in ``dst_slicer`` on ``target_printer``.

    Parameters
    ----------
    data : dict
        The source profile (already loaded from JSON).
    profile_type : str
        One of ``filament`` / ``machine`` / ``process``.
    src_slicer, dst_slicer : str
        Slicer keys (``bambu`` / ``orca`` / ``snapmaker`` / ``prusa``).
    target_printer : str
        Destination printer name to make the profile compatible with. For
        ``machine`` profiles this is informational (the profile *is* a printer).
    search_dirs : list[str]
        Folders to resolve inheritance parents from (source user + system dirs).
    name_suffix : str
        Suffix appended to the profile name. Defaults to ``(from <src>)``.

    Returns
    -------
    (converted_dict, ConversionReport)
    """
    report = ConversionReport(
        profile_type=profile_type, src_slicer=src_slicer, dst_slicer=dst_slicer,
        source_name=profile_name(data, "(unnamed)"), target_name=target_printer,
    )

    # 1) Flatten inheritance so nothing is lost when moved.
    flat, chain = resolve_inheritance(data, search_dirs or [])
    report.inheritance_chain = chain
    for p in chain:
        if "NOT FOUND" in p:
            report.warnings.append(
                f"Parent profile {p} could not be located; some inherited "
                "settings may be missing. Convert with the source slicer "
                "installed for best results.")
    if chain:
        report.changes.append(
            f"Flattened {len(chain)} inherited profile(s) into a self-contained copy.")

    out = dict(flat)

    # 2) Retarget printer compatibility.
    if profile_type in ("filament", "process"):
        out["compatible_printers"] = [target_printer]
        out["compatible_printers_condition"] = ""
        report.changes.append(
            f"Set compatible_printers -> ['{target_printer}'].")
    elif profile_type == "machine":
        # A machine profile *is* the printer; give it the target's display name.
        if target_printer:
            out["printer_model"] = out.get("printer_model", target_printer)
        report.changes.append(
            "Kept machine geometry/settings; review nozzle & bed size below.")
        for k in ("printable_area", "printable_height", "nozzle_diameter"):
            if k in out:
                report.warnings.append(
                    f"Verify '{k}' matches your real printer: {out[k]!r}")

    # 3) Fix identity fields so it's treated as a fresh user preset.
    suffix = name_suffix if name_suffix is not None else f" (from {src_slicer})"
    base_name = profile_name(out, "Converted profile")
    if suffix and not base_name.endswith(suffix):
        out["name"] = base_name + suffix
        report.changes.append(f"Renamed to '{out['name']}'.")
    out["from"] = "User"
    out["is_custom_defined"] = "1"
    out.pop("inherits", None)
    dropped = [k for k in _DROP_KEYS if k in out]
    for k in dropped:
        out.pop(k, None)
    if dropped:
        report.changes.append(
            f"Removed source-only id field(s): {', '.join(dropped)}.")

    # 4) Translate G-code if the dialect differs.
    src_fam = FAMILY.get(src_slicer, "orca")
    dst_fam = FAMILY.get(dst_slicer, "orca")
    if src_fam != dst_fam:
        for key in GCODE_KEYS:
            if key in out and isinstance(out[key], str):
                new_gc, warns = translate_gcode(out[key], src_fam, dst_fam)
                out[key] = new_gc
                for w in warns:
                    report.warnings.append(
                        f"G-code variable '{w}' in '{key}' had no known "
                        "mapping -- please review it manually.")
        report.changes.append(
            f"Translated G-code template variables ({src_fam} -> {dst_fam}).")

    return out, report


def suggested_filename(converted: dict, profile_type: str) -> str:
    """A safe .json filename for the converted profile."""
    name = profile_name(converted, f"converted_{profile_type}")
    safe = "".join(c if c.isalnum() or c in " -_@." else "_" for c in name).strip()
    return f"{safe}.json"
