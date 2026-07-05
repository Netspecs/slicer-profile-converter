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
    "creality": "orca",
    "anycubic": "orca",
    "prusa": "prusa",
    "super": "prusa",
    "cura": "cura",
}

# Key mappings between different slicer families
# These cover the most common settings - full coverage would need hundreds of keys

# PrusaSlicer ↔ OrcaSlicer/Bambu mappings
PRUSA_TO_ORCA_MAP = {
    # Layer & Perimeters
    "layer_height": "layer_height",
    "first_layer_height": "first_layer_height",
    "perimeters": "wall_loops",
    "top_solid_layers": "top_shell_layers",
    "bottom_solid_layers": "bottom_shell_layers",
    "extra_perimeters": "extra_perimeters",
    
    # Infill
    "fill_density": "sparse_infill_density",
    "fill_pattern": "sparse_infill_pattern",
    "top_fill_pattern": "top_surface_pattern",
    "bottom_fill_pattern": "bottom_surface_pattern",
    
    # Speed
    "perimeter_speed": "outer_wall_speed",
    "external_perimeter_speed": "outer_wall_speed",
    "infill_speed": "sparse_infill_speed",
    "solid_infill_speed": "internal_solid_infill_speed",
    "top_solid_infill_speed": "top_surface_speed",
    "travel_speed": "travel_speed",
    "first_layer_speed": "initial_layer_speed",
    "bridge_speed": "bridge_speed",
    
    # Temperature
    "temperature": "nozzle_temperature",
    "first_layer_temperature": "nozzle_temperature_initial_layer",
    "bed_temperature": "bed_temperature",
    "first_layer_bed_temperature": "bed_temperature_initial_layer_single",
    
    # Support
    "support_material": "enable_support",
    "support_material_pattern": "support_base_pattern",
    "support_material_spacing": "support_base_pattern_spacing",
    "support_material_threshold": "support_threshold_angle",
    
    # Retraction
    "retract_length": "retraction_length",
    "retract_speed": "retraction_speed",
    "retract_before_travel": "retract_before_wipe",
    
    # Cooling
    "fan_always_on": "fan_cooling_layer_time",
    "min_fan_speed": "slow_down_min_speed",
    "max_fan_speed": "fan_max_speed",
    "bridge_fan_speed": "overhang_fan_speed",
    
    # Extrusion
    "extrusion_width": "line_width",
    "extrusion_multiplier": "filament_flow_ratio",
    "nozzle_diameter": "nozzle_diameter",
    
    # Skirt/Brim
    "skirts": "skirt_loops",
    "skirt_distance": "skirt_distance",
    "brim_width": "brim_width",
}

ORCA_TO_PRUSA_MAP = {v: k for k, v in PRUSA_TO_ORCA_MAP.items() if v != k}

# Cura → OrcaSlicer/Bambu mappings (most common settings)
CURA_TO_ORCA_MAP = {
    # Layer & Shell
    "layer_height": "layer_height",
    "initial_layer_height": "first_layer_height",
    "wall_thickness": "wall_loops",
    "wall_line_count": "wall_loops",
    "top_layers": "top_shell_layers",
    "bottom_layers": "bottom_shell_layers",
    
    # Infill
    "infill_sparse_density": "sparse_infill_density",
    "infill_pattern": "sparse_infill_pattern",
    
    # Temperature
    "material_print_temperature": "nozzle_temperature",
    "material_print_temperature_layer_0": "nozzle_temperature_initial_layer",
    "material_bed_temperature": "bed_temperature",
    "material_bed_temperature_layer_0": "bed_temperature_initial_layer_single",
    
    # Speed
    "speed_print": "outer_wall_speed",
    "speed_infill": "sparse_infill_speed",
    "speed_wall": "outer_wall_speed",
    "speed_wall_0": "outer_wall_speed",
    "speed_wall_x": "inner_wall_speed",
    "speed_topbottom": "top_surface_speed",
    "speed_travel": "travel_speed",
    
    # Support
    "support_enable": "enable_support",
    "support_type": "support_type",
    "support_infill_rate": "support_base_pattern_spacing",
    
    # Retraction
    "retraction_enable": "enable_retraction",
    "retraction_amount": "retraction_length",
    "retraction_speed": "retraction_speed",
    
    # Cooling
    "cool_fan_enabled": "cooling_fan_enable",
    "cool_fan_speed": "fan_cooling_layer_time",
    
    # Adhesion
    "adhesion_type": "brim_type",
}

ORCA_TO_CURA_MAP = {v: k for k, v in CURA_TO_ORCA_MAP.items() if v != k}

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
    filament_color: Optional[str] = None  # HEX color for filament profiles
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
        ]
        if self.filament_color:
            lines.append(f"Color        : {self.filament_color} {self._color_preview(self.filament_color)}")
        lines.append("")
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

    @staticmethod
    def _color_preview(hex_color: str) -> str:
        """Generate a simple ASCII color preview (RGB values)."""
        # Strip # if present
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return f"[RGB {r}, {g}, {b}]"
            except ValueError:
                return ""
        return ""


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

    # Extract filament color if present (for filament profiles)
    if profile_type == "filament":
        color = data.get("filament_colour") or data.get("default_filament_colour")
        if color and isinstance(color, str):
            # Handle array format (some slicers store as ["#RRGGBB"])
            if color.startswith("[") and color.endswith("]"):
                try:
                    import json as json_mod
                    parsed = json_mod.loads(color)
                    if isinstance(parsed, list) and parsed:
                        color = parsed[0]
                except Exception:
                    pass
            report.filament_color = color

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

    # 4) Map keys if converting between different slicer families
    src_fam = FAMILY.get(src_slicer, "orca")
    dst_fam = FAMILY.get(dst_slicer, "orca")
    
    if src_fam != dst_fam:
        # PrusaSlicer → Orca/Bambu
        if src_fam == "prusa" and dst_fam == "orca":
            mapped = {}
            unmapped = []
            for key, value in out.items():
                if key in PRUSA_TO_ORCA_MAP:
                    new_key = PRUSA_TO_ORCA_MAP[key]
                    mapped[new_key] = value
                elif key.startswith("_prusa"):
                    continue  # Skip metadata
                else:
                    mapped[key] = value
                    if not key.startswith("_"):
                        unmapped.append(key)
            
            out = mapped
            report.changes.append(
                f"Mapped {len(PRUSA_TO_ORCA_MAP)} PrusaSlicer settings to OrcaSlicer/Bambu format.")
            if unmapped:
                report.warnings.append(
                    f"Some PrusaSlicer settings had no mapping: {', '.join(unmapped[:5])}{'...' if len(unmapped) > 5 else ''}")
        
        # Orca/Bambu → PrusaSlicer
        elif src_fam == "orca" and dst_fam == "prusa":
            mapped = {}
            unmapped = []
            for key, value in out.items():
                if key in ORCA_TO_PRUSA_MAP:
                    new_key = ORCA_TO_PRUSA_MAP[key]
                    mapped[new_key] = value
                else:
                    mapped[key] = value
                    if not key.startswith("_") and key not in ("name", "type", "from", "is_custom_defined"):
                        unmapped.append(key)
            
            out = mapped
            report.changes.append(
                f"Mapped {len(ORCA_TO_PRUSA_MAP)} OrcaSlicer/Bambu settings to PrusaSlicer format.")
            if unmapped:
                report.warnings.append(
                    f"Some OrcaSlicer settings had no PrusaSlicer mapping: {', '.join(unmapped[:5])}{'...' if len(unmapped) > 5 else ''}")
        
        # Cura → Orca/Bambu
        elif src_fam == "cura" and dst_fam == "orca":
            mapped = {}
            unmapped = []
            for key, value in out.items():
                if key in CURA_TO_ORCA_MAP:
                    new_key = CURA_TO_ORCA_MAP[key]
                    mapped[new_key] = value
                elif key.startswith("_cura") or key.startswith("general_") or key.startswith("metadata_"):
                    continue  # Skip Cura metadata
                else:
                    mapped[key] = value
                    if not key.startswith("_"):
                        unmapped.append(key)
            
            out = mapped
            report.changes.append(
                f"Mapped {len(CURA_TO_ORCA_MAP)} Cura settings to OrcaSlicer/Bambu format.")
            if unmapped:
                report.warnings.append(
                    f"Some Cura settings had no mapping: {', '.join(unmapped[:5])}{'...' if len(unmapped) > 5 else ''}")
        
        # Orca/Bambu → Cura
        elif src_fam == "orca" and dst_fam == "cura":
            mapped = {}
            unmapped = []
            for key, value in out.items():
                if key in ORCA_TO_CURA_MAP:
                    new_key = ORCA_TO_CURA_MAP[key]
                    mapped[new_key] = value
                else:
                    mapped[key] = value
                    if not key.startswith("_") and key not in ("name", "type", "from", "is_custom_defined"):
                        unmapped.append(key)
            
            # Add Cura metadata section
            mapped["general_version"] = "4"
            mapped["general_definition"] = "fdmprinter"
            mapped["metadata_type"] = "quality_changes" if profile_type == "process" else "material"
            mapped["metadata_setting_version"] = "22"
            
            out = mapped
            report.changes.append(
                f"Mapped {len(ORCA_TO_CURA_MAP)} OrcaSlicer/Bambu settings to Cura format.")
            if unmapped:
                report.warnings.append(
                    f"Some OrcaSlicer settings had no Cura mapping: {', '.join(unmapped[:5])}{'...' if len(unmapped) > 5 else ''}")

    # 5) Translate G-code if the dialect differs.
    if src_fam != dst_fam and src_fam != "cura" and dst_fam != "cura":
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


def suggested_filename(converted: dict, profile_type: str, dst_slicer: str = "orca") -> str:
    """A safe filename for the converted profile (with appropriate extension)."""
    name = profile_name(converted, f"converted_{profile_type}")
    safe = "".join(c if c.isalnum() or c in " -_@." else "_" for c in name).strip()
    
    # Different file extensions for different slicer families
    family = FAMILY.get(dst_slicer, "orca")
    if family == "cura":
        return f"{safe}.inst.cfg"
    elif family == "prusa":
        return f"{safe}.ini"
    else:
        return f"{safe}.json"
