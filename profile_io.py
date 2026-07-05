"""
profile_io.py
=============

Load, resolve and save slicer profiles in various formats:
- JSON: OrcaSlicer-family (Bambu Studio, OrcaSlicer, Snapmaker Orca)
- .inst.cfg: Cura (INI-like format with sections)

All slicers use an inheritance model where child profiles inherit from parents.
To convert reliably, we flatten the inheritance chain.
"""

from __future__ import annotations

import configparser
import json
import os
from typing import Dict, List, Optional, Tuple


class ProfileError(Exception):
    """Raised when a profile file cannot be read or parsed."""


def load_json(path: str) -> dict:
    """Load a single JSON profile file."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"Could not read profile {path!r}: {exc}") from exc


def save_json(data: dict, path: str) -> None:
    """Write a profile to disk as pretty-printed JSON (UTF-8)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=4, ensure_ascii=False)
        fh.write("\n")


def load_cura_cfg(path: str) -> dict:
    """Load a Cura .inst.cfg file and convert to dict.
    
    Cura profiles are INI-like with sections like [general], [metadata], [values].
    We convert them to a flat dict for easier processing.
    """
    try:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(path, encoding="utf-8")
        
        result = {}
        # Flatten all sections into one dict
        for section in parser.sections():
            for key, value in parser.items(section):
                # Keep section prefix for metadata/general, values go without prefix
                if section == "values":
                    result[key] = value
                else:
                    result[f"{section}_{key}"] = value
        
        # Add file metadata
        result["_cura_file"] = os.path.basename(path)
        result["_cura_format"] = "inst.cfg"
        
        return result
    except Exception as exc:
        raise ProfileError(f"Could not read Cura profile {path!r}: {exc}") from exc


def save_cura_cfg(data: dict, path: str) -> None:
    """Write a dict to a Cura .inst.cfg file.
    
    Reconstructs the INI structure from a flat dict.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    parser = configparser.ConfigParser(interpolation=None)
    
    # Separate keys into sections
    general_keys = {}
    metadata_keys = {}
    value_keys = {}
    
    for key, value in data.items():
        if key.startswith("_cura"):
            continue  # Skip internal metadata
        if key.startswith("general_"):
            general_keys[key.replace("general_", "", 1)] = str(value)
        elif key.startswith("metadata_"):
            metadata_keys[key.replace("metadata_", "", 1)] = str(value)
        else:
            value_keys[key] = str(value)
    
    # Write sections
    if general_keys:
        parser.add_section("general")
        for k, v in general_keys.items():
            parser.set("general", k, v)
    
    if metadata_keys:
        parser.add_section("metadata")
        for k, v in metadata_keys.items():
            parser.set("metadata", k, v)
    
    if value_keys:
        parser.add_section("values")
        for k, v in value_keys.items():
            parser.set("values", k, v)
    
    with open(path, "w", encoding="utf-8") as fh:
        parser.write(fh)


def load_profile(path: str) -> dict:
    """Load a profile file in any supported format (JSON or Cura .inst.cfg).
    
    Automatically detects the format based on file extension.
    """
    if path.endswith(".json"):
        return load_json(path)
    elif path.endswith(".inst.cfg") or path.endswith(".cfg") or path.endswith(".fdm_material"):
        return load_cura_cfg(path)
    else:
        # Try JSON first, fallback to Cura
        try:
            return load_json(path)
        except ProfileError:
            return load_cura_cfg(path)


def save_profile(data: dict, path: str) -> None:
    """Save a profile file in the appropriate format based on extension."""
    if path.endswith(".json"):
        save_json(data, path)
    elif path.endswith(".inst.cfg") or path.endswith(".cfg") or path.endswith(".fdm_material"):
        save_cura_cfg(data, path)
    else:
        # Default to JSON
        save_json(data, path)


def profile_name(data: dict, fallback: str = "") -> str:
    """Best-effort human name for a profile."""
    # Try different name keys: OrcaSlicer uses "name", Cura uses "general_name" or "metadata_name"
    return (data.get("name") or 
            data.get("general_name") or 
            data.get("metadata_name") or 
            data.get("setting_id") or 
            fallback)


def _index_profiles_by_name(search_dirs: List[str]) -> Dict[str, str]:
    """Build a {profile_name: filepath} index across the given directories.

    Later directories do NOT override earlier ones (first match wins), so pass
    user dirs before system dirs if you prefer user copies.
    Handles both JSON and Cura .inst.cfg files.
    """
    index: Dict[str, str] = {}
    valid_extensions = (".json", ".inst.cfg", ".cfg", ".fdm_material")
    
    for d in search_dirs:
        if not d or not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not any(fn.lower().endswith(ext) for ext in valid_extensions):
                continue
            full = os.path.join(d, fn)
            try:
                data = load_profile(full)
            except ProfileError:
                continue
            name = profile_name(data)
            if name and name not in index:
                index[name] = full
    return index


def resolve_inheritance(
    data: dict,
    search_dirs: Optional[List[str]] = None,
    _seen: Optional[set] = None,
    _index: Optional[Dict[str, str]] = None,
) -> Tuple[dict, List[str]]:
    """Flatten a profile by merging its inheritance chain.

    Parameters
    ----------
    data : dict
        The child profile already loaded from JSON.
    search_dirs : list[str]
        Directories to search for parent profiles (user + system folders).

    Returns
    -------
    (flattened, chain)
        ``flattened`` is a new dict with parent keys merged in (child wins).
        ``chain`` is the list of parent names that were resolved, parent-first.
    """
    search_dirs = search_dirs or []
    _seen = _seen if _seen is not None else set()
    if _index is None:
        _index = _index_profiles_by_name(search_dirs)

    parent_name = data.get("inherits", "").strip() if isinstance(
        data.get("inherits"), str) else ""

    if not parent_name or parent_name in _seen:
        # No parent (or cycle guard) -- return a copy without the inherits key.
        result = dict(data)
        result.pop("inherits", None)
        return result, []

    _seen.add(parent_name)
    parent_path = _index.get(parent_name)
    if not parent_path:
        # Parent not found on disk: keep child as-is but record the gap.
        result = dict(data)
        result.pop("inherits", None)
        return result, [f"{parent_name} (NOT FOUND)"]

    parent_data = load_profile(parent_path)  # Changed from load_json to support Cura
    parent_flat, parent_chain = resolve_inheritance(
        parent_data, search_dirs, _seen, _index)

    merged = dict(parent_flat)
    for k, v in data.items():
        if k == "inherits":
            continue
        merged[k] = v  # child overrides parent

    return merged, parent_chain + [parent_name]


if __name__ == "__main__":  # simple smoke test with a synthetic chain
    import tempfile

    tmp = tempfile.mkdtemp()
    base = {"name": "Base PLA", "nozzle_temperature": ["200"],
            "filament_flow_ratio": ["0.98"]}
    child = {"name": "My PLA", "inherits": "Base PLA",
             "nozzle_temperature": ["210"]}
    save_json(base, os.path.join(tmp, "base.json"))

    flat, chain = resolve_inheritance(child, [tmp])
    print("chain:", chain)
    print("flattened nozzle_temperature:", flat.get("nozzle_temperature"))
    print("inherited flow ratio:", flat.get("filament_flow_ratio"))
    assert flat["nozzle_temperature"] == ["210"]
    assert flat["filament_flow_ratio"] == ["0.98"]
    print("OK")
