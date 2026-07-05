"""
slicer_paths.py
================

Locates where each supported slicer stores its **user** profiles on disk,
across Windows, macOS and Linux.

Why this matters: Bambu Studio's "Export" UI is notoriously hard to use --
it only lists profiles you've explicitly saved as *User Presets* that also
match the currently selected printer/nozzle, so the export list is often
empty. But every slicer in the OrcaSlicer family (Bambu Studio, OrcaSlicer,
Snapmaker Orca) actually stores each profile as a plain ``.json`` file inside
a per-user folder. This module finds those folders so we can read the
profiles directly -- no export button required.

Profile family layout (all three slicers share it)::

    <config-root>/user/<user-id>/filament/*.json     # filament presets
    <config-root>/user/<user-id>/machine/*.json      # printer presets
    <config-root>/user/<user-id>/process/*.json      # process/print presets

``<user-id>`` is a numeric folder (your Bambu/cloud account id) or ``default``.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Profile "types" as the OrcaSlicer family names them on disk.
PROFILE_TYPES = ("filament", "machine", "process")

# Friendly labels for the UI.
TYPE_LABELS = {
    "filament": "Filament",
    "machine": "Printer",
    "process": "Process / Print",
}


@dataclass
class SlicerInstall:
    """A single detected slicer installation on this computer."""

    key: str                       # short id, e.g. "bambu"
    name: str                      # display name, e.g. "Bambu Studio"
    config_root: str               # .../BambuStudio
    user_root: str                 # .../BambuStudio/user
    user_ids: List[str] = field(default_factory=list)  # subfolders under user/

    @property
    def exists(self) -> bool:
        return bool(self.user_root) and os.path.isdir(self.user_root)


def _config_base_dirs() -> List[str]:
    """Return the OS-specific base directories that hold slicer config roots."""
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        # %AppData% == C:\Users\<user>\AppData\Roaming
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        return [appdata]
    if sys.platform == "darwin":
        return [os.path.join(home, "Library", "Application Support")]
    # Linux and everything else
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
    return [xdg, home]


# Folder name(s) each slicer uses for its config root, per slicer key.
_SLICER_DIRNAMES = {
    "bambu": (["BambuStudio"], "Bambu Studio"),
    "orca": (["OrcaSlicer"], "OrcaSlicer"),
    "snapmaker": (["SnapmakerOrca", "Snapmaker Orca", "SnapmakerOrcaSlicer"],
                  "Snapmaker Orca"),
}


def _find_config_root(dirnames: List[str]) -> Optional[str]:
    """Search the OS base dirs for the first existing config root."""
    for base in _config_base_dirs():
        for dn in dirnames:
            candidate = os.path.join(base, dn)
            if os.path.isdir(candidate):
                return candidate
    return None


def _list_user_ids(user_root: str) -> List[str]:
    """Return subfolders under user/ (numeric account ids and/or 'default')."""
    if not os.path.isdir(user_root):
        return []
    ids = []
    for entry in sorted(os.listdir(user_root)):
        full = os.path.join(user_root, entry)
        if os.path.isdir(full):
            ids.append(entry)
    return ids


def detect_slicers() -> Dict[str, SlicerInstall]:
    """Detect all supported slicers installed for the current user.

    Returns a dict keyed by slicer key (``bambu``, ``orca``, ``snapmaker``).
    Only slicers whose config root exists on disk are included.
    """
    found: Dict[str, SlicerInstall] = {}
    for key, (dirnames, name) in _SLICER_DIRNAMES.items():
        root = _find_config_root(dirnames)
        if not root:
            continue
        user_root = os.path.join(root, "user")
        found[key] = SlicerInstall(
            key=key,
            name=name,
            config_root=root,
            user_root=user_root,
            user_ids=_list_user_ids(user_root),
        )
    return found


def list_profiles(install: SlicerInstall, profile_type: str,
                  user_id: Optional[str] = None) -> List[str]:
    """List absolute paths of ``.json`` profiles of ``profile_type``.

    If ``user_id`` is given, only that user folder is scanned; otherwise all
    user folders are scanned. Files whose names start with '.' are skipped.
    """
    if profile_type not in PROFILE_TYPES:
        raise ValueError(f"Unknown profile type: {profile_type!r}")

    user_ids = [user_id] if user_id else (install.user_ids or [])
    results: List[str] = []
    for uid in user_ids:
        folder = os.path.join(install.user_root, uid, profile_type)
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if fn.lower().endswith(".json") and not fn.startswith("."):
                results.append(os.path.join(folder, fn))
    return results


def system_profile_dirs(install: SlicerInstall, profile_type: str) -> List[str]:
    """Return existing 'system' (vendor) profile dirs for inheritance lookups.

    Custom user profiles usually ``inherit`` from a vendor/system base profile.
    To flatten a profile we may need to read those bases, so we expose their
    likely locations here. Layout: ``<config-root>/system/<Vendor>/<type>/``.
    """
    sys_root = os.path.join(install.config_root, "system")
    dirs: List[str] = []
    if os.path.isdir(sys_root):
        for vendor in sorted(os.listdir(sys_root)):
            vdir = os.path.join(sys_root, vendor, profile_type)
            if os.path.isdir(vdir):
                dirs.append(vdir)
        # Some builds keep type folders directly under system/.
        direct = os.path.join(sys_root, profile_type)
        if os.path.isdir(direct):
            dirs.append(direct)
    return dirs


if __name__ == "__main__":  # quick manual check
    installs = detect_slicers()
    if not installs:
        print("No supported slicers detected on this machine.")
    for k, inst in installs.items():
        print(f"[{k}] {inst.name}")
        print(f"    config_root: {inst.config_root}")
        print(f"    user ids:    {inst.user_ids}")
        for t in PROFILE_TYPES:
            n = len(list_profiles(inst, t))
            print(f"    {TYPE_LABELS[t]:16s}: {n} profile(s)")
