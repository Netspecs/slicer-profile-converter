"""
profile_io.py
=============

Load, resolve and save OrcaSlicer-family profiles (Bambu Studio, OrcaSlicer,
Snapmaker Orca). All three store profiles as JSON with an inheritance model:
a child profile has an ``"inherits"`` key naming a parent profile, and only
stores the keys that differ from the parent.

To convert a profile reliably we usually want a **flattened** version -- the
full set of effective settings with the inheritance chain merged in. This
module handles that, searching user and system folders for parents.
"""

from __future__ import annotations

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


def profile_name(data: dict, fallback: str = "") -> str:
    """Best-effort human name for a profile."""
    return data.get("name") or data.get("setting_id") or fallback


def _index_profiles_by_name(search_dirs: List[str]) -> Dict[str, str]:
    """Build a {profile_name: filepath} index across the given directories.

    Later directories do NOT override earlier ones (first match wins), so pass
    user dirs before system dirs if you prefer user copies.
    """
    index: Dict[str, str] = {}
    for d in search_dirs:
        if not d or not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(".json"):
                continue
            full = os.path.join(d, fn)
            try:
                data = load_json(full)
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

    parent_data = load_json(parent_path)
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
