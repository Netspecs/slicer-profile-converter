"""
Focused tests for the conversion engine. Run:  python3 test_converter.py
"""
import os
import sys

from converter import convert_profile, suggested_filename
from profile_io import load_json

SAMPLES = os.path.join(os.path.dirname(__file__), "samples")


def test_bambu_to_orca_filament():
    child = load_json(os.path.join(SAMPLES, "bambu_my_pla.json"))
    converted, report = convert_profile(
        data=child,
        profile_type="filament",
        src_slicer="bambu",
        dst_slicer="orca",
        target_printer="Snapmaker Artisan 0.4 nozzle",
        search_dirs=[SAMPLES],
        name_suffix=" (from Bambu)",
    )

    # 1) inheritance flattened -> inherited key present, child override wins
    assert converted["nozzle_temperature"] == ["215"], "child override lost"
    assert converted["nozzle_temperature_initial_layer"] == ["220"], "inherited key lost"
    assert converted["filament_flow_ratio"] == ["0.95"], "child override lost"

    # 2) retargeted to destination printer
    assert converted["compatible_printers"] == ["Snapmaker Artisan 0.4 nozzle"]
    assert converted["compatible_printers_condition"] == ""

    # 3) identity fixed / source ids dropped
    assert converted["name"].endswith("(from Bambu)")
    assert "setting_id" not in converted
    assert "filament_id" not in converted
    assert "inherits" not in converted
    assert converted["from"] == "User"

    # 4) same-family (orca) G-code untouched
    assert "{nozzle_temperature_initial_layer[0]}" in converted["machine_start_gcode"]

    # report sanity
    assert report.inheritance_chain == ["Generic PLA @base"]
    assert any("compatible_printers" in c for c in report.changes)
    print("test_bambu_to_orca_filament: OK")
    print("  ->", suggested_filename(converted, "filament"))


def test_missing_parent_warns():
    orphan = {
        "type": "filament", "name": "Orphan PLA",
        "inherits": "Nonexistent Base", "nozzle_temperature": ["210"],
    }
    converted, report = convert_profile(
        orphan, "filament", "bambu", "orca",
        target_printer="Bambu Lab A1 0.4 nozzle", search_dirs=[SAMPLES],
    )
    assert any("NOT FOUND" in w or "could not be located" in w
               for w in report.warnings), "missing parent not reported"
    assert converted["nozzle_temperature"] == ["210"]
    print("test_missing_parent_warns: OK")


def test_gcode_dialect_translation():
    prof = {
        "type": "process", "name": "Prusa Fine",
        "start_gcode": "M104 S[first_layer_temperature]\nM140 S[first_layer_bed_temperature]",
    }
    converted, report = convert_profile(
        prof, "process", "prusa", "orca",
        target_printer="OrcaMachine 0.4", search_dirs=[],
    )
    gc = converted["start_gcode"]
    assert "{nozzle_temperature_initial_layer[0]}" in gc, gc
    assert "{bed_temperature_initial_layer[0]}" in gc, gc
    print("test_gcode_dialect_translation: OK")


if __name__ == "__main__":
    test_bambu_to_orca_filament()
    test_missing_parent_warns()
    test_gcode_dialect_translation()
    print("\nAll tests passed.")
    sys.exit(0)
