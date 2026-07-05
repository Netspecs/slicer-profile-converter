"""
Slicer Profile Converter -- desktop GUI
=======================================

Convert 3D-printing slicer profiles between Bambu Studio, OrcaSlicer and
Snapmaker Orca -- reading them straight from disk so you don't have to fight
Bambu Studio's hidden/finicky export button.

Workflow in the UI:
    1. Pick the SOURCE slicer  (auto-detected on your machine)
    2. Pick a profile type + one or more profiles to convert
    3. Pick the DESTINATION slicer + the target printer name
    4. Convert -> profiles are written into the destination slicer's user
       folder (or a folder you choose), with a conversion report per profile.

Pure standard-library Tkinter -- no heavy dependencies.
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from converter import convert_profile, suggested_filename
from profile_io import load_json, profile_name, save_json, ProfileError
from slicer_paths import (
    PROFILE_TYPES, TYPE_LABELS, detect_slicers, list_profiles,
    system_profile_dirs,
)

APP_TITLE = "Slicer Profile Converter"
APP_VERSION = "2.0.0"

# --- dark theme palette (matches the Color Palette Matcher look) ------------
BG = "#1e1e2e"
BG_CARD = "#282838"
FG = "#e8e8f0"
FG_MUTED = "#a0a0b8"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9575ff"
OK = "#4caf82"
WARN = "#e0a54a"


def _resource_path(rel: str) -> str:
    """Resolve a bundled resource path (works under PyInstaller too)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


class ConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("980x720")
        self.root.minsize(860, 620)
        self.root.configure(bg=BG)

        self.installs = detect_slicers()
        # Each entry: {path, src_key, ptype, name, manual}
        self.profile_entries: list[dict] = []

        self._set_window_icon()
        self._build_style()
        self._build_header()
        self._build_controls()
        self._build_body()
        self._build_statusbar()

        self._refresh_profile_list()

    # ----- window chrome ---------------------------------------------------
    def _set_window_icon(self):
        for name in ("icon.png",):
            p = _resource_path(os.path.join("docs", name))
            if os.path.exists(p):
                try:
                    img = tk.PhotoImage(file=p)
                    self.root.iconphoto(True, img)
                    self._icon_ref = img  # keep a reference
                    break
                except Exception:
                    pass

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=BG_CARD, background=BG_CARD,
                        foreground=FG, arrowcolor=FG)
        style.map("TCombobox", fieldbackground=[("readonly", BG_CARD)],
                  foreground=[("readonly", FG)])

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(header, text="\U0001f504  Slicer Profile Converter", bg=BG,
                 fg=FG, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(header,
                 text="Move filament, printer & process profiles between "
                      "Bambu Studio, OrcaSlicer, Snapmaker Orca, Creality Print, "
                      "Anycubic Slicer, Ultimaker Cura, PrusaSlicer and SuperSlicer \u2014 "
                      "read straight from disk, no export button needed.",
                 bg=BG, fg=FG_MUTED, font=("Segoe UI", 10),
                 wraplength=920, justify="left").pack(anchor="w", pady=(2, 0))

    # ----- controls --------------------------------------------------------
    # Display names for slicer keys.
    _SLICER_DISPLAY = {
        "bambu": "Bambu Studio",
        "orca": "OrcaSlicer",
        "snapmaker": "Snapmaker Orca",
        "creality": "Creality Print",
        "anycubic": "Anycubic Slicer",
        "cura": "Ultimaker Cura",
        "prusa": "PrusaSlicer",
        "super": "SuperSlicer",
    }

    def _build_controls(self):
        wrap = tk.Frame(self.root, bg=BG_CARD)
        wrap.pack(fill="x", padx=20, pady=8)
        inner = tk.Frame(wrap, bg=BG_CARD)
        inner.pack(fill="x", padx=14, pady=12)

        real_keys = ["bambu", "orca", "snapmaker", "creality", "anycubic", "cura", "prusa", "super"]
        # "all" is a virtual key that aggregates every detected slicer.
        self._src_keys = ["all"] + real_keys
        self._dst_keys = real_keys
        # "all" type shows filament + printer + process together.
        self._type_keys = ["all"] + list(PROFILE_TYPES)

        def src_label(k):
            if k == "all":
                n = len(self.installs)
                return f"All detected slicers ({n})" if n else "All slicers"
            base = self._SLICER_DISPLAY[k]
            return base + ("" if k in self.installs else "  (not detected)")

        def dst_label(k):
            base = self._SLICER_DISPLAY[k]
            return base + ("" if k in self.installs else "  (not detected)")

        def type_label(t):
            return "All types" if t == "all" else TYPE_LABELS[t]

        # Row 1: source slicer + profile type
        row1 = tk.Frame(inner, bg=BG_CARD)
        row1.pack(fill="x", pady=(0, 8))

        tk.Label(row1, text="From:", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.src_var = tk.StringVar()
        self.src_menu = ttk.Combobox(
            row1, textvariable=self.src_var, state="readonly", width=26,
            values=[src_label(k) for k in self._src_keys])
        self.src_menu.current(0)  # default: show everything
        self.src_menu.pack(side="left", padx=(6, 18))
        self.src_menu.bind("<<ComboboxSelected>>",
                           lambda e: self._refresh_profile_list())

        tk.Label(row1, text="Profile type:", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.type_var = tk.StringVar()
        self.type_menu = ttk.Combobox(
            row1, textvariable=self.type_var, state="readonly", width=18,
            values=[type_label(t) for t in self._type_keys])
        self.type_menu.current(0)  # default: all types
        self.type_menu.pack(side="left", padx=(6, 0))
        self.type_menu.bind("<<ComboboxSelected>>",
                            lambda e: self._refresh_profile_list())

        # Row 2: destination slicer + target printer
        row2 = tk.Frame(inner, bg=BG_CARD)
        row2.pack(fill="x")

        tk.Label(row2, text="To:", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.dst_var = tk.StringVar()
        self.dst_menu = ttk.Combobox(
            row2, textvariable=self.dst_var, state="readonly", width=26,
            values=[dst_label(k) for k in self._dst_keys])
        self.dst_menu.current(1)
        self.dst_menu.pack(side="left", padx=(6, 18))

        tk.Label(row2, text="Target printer:", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.printer_var = tk.StringVar()
        self.printer_entry = tk.Entry(
            row2, textvariable=self.printer_var, width=34, bg=BG, fg=FG,
            insertbackground=FG, relief="flat")
        self.printer_entry.pack(side="left", padx=(6, 0), ipady=3)
        self.printer_var.set("Snapmaker Artisan 0.4 nozzle")

    def _selected_src_key(self) -> str:
        """Return the selected source key ('all' or a specific slicer)."""
        idx = self.src_menu.current()
        if idx < 0 or idx >= len(self._src_keys):
            return "all"
        return self._src_keys[idx]

    def _selected_dst_key(self) -> str:
        idx = self.dst_menu.current()
        if idx < 0 or idx >= len(self._dst_keys):
            return self._dst_keys[0]
        return self._dst_keys[idx]

    def _infer_from_path(self, path):
        """Best-effort (src_key, profile_type) inference from a file path."""
        low = path.lower()
        ptype = PROFILE_TYPES[0]
        parts = os.path.normpath(path).lower().split(os.sep)
        
        # Infer profile type from folder name
        for t in PROFILE_TYPES:
            if t in parts:
                ptype = t
                break
        # PrusaSlicer uses "print" instead of "process"
        if "print" in parts and ptype == PROFILE_TYPES[0]:
            ptype = "process"
        
        # Infer source slicer from path
        src = None
        if "snapmaker" in low:
            src = "snapmaker"
        elif "bambustudio" in low or "bambu studio" in low:
            src = "bambu"
        elif "orcaslicer" in low:
            src = "orca"
        elif "crealityprint" in low or "creality print" in low:
            src = "creality"
        elif "anycubic" in low:
            src = "anycubic"
        elif "cura" in low:
            src = "cura"
        elif "prusaslicer" in low:
            src = "prusa"
        elif "superslicer" in low or "super slicer" in low:
            src = "super"
        
        return src, ptype

    # ----- body: profile list + report ------------------------------------
    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=8)

        # Left: profile list
        left = tk.Frame(body, bg=BG_CARD)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(left, text="Profiles found on disk", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.hint_label = tk.Label(left, text="", bg=BG_CARD, fg=FG_MUTED,
                                    font=("Segoe UI", 9), wraplength=380,
                                    justify="left")
        self.hint_label.pack(anchor="w", padx=12)

        list_wrap = tk.Frame(left, bg=BG_CARD)
        list_wrap.pack(fill="both", expand=True, padx=12, pady=8)
        scroll = tk.Scrollbar(list_wrap)
        scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(
            list_wrap, selectmode="extended", bg=BG, fg=FG,
            selectbackground=ACCENT, selectforeground="white",
            relief="flat", highlightthickness=0, yscrollcommand=scroll.set,
            font=("Segoe UI", 10), activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.listbox.yview)

        btns = tk.Frame(left, bg=BG_CARD)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        self._make_button(btns, "\U0001f5c1  Add file\u2026", self._add_file_manual,
                          side="left")
        self._make_button(btns, "Select all", self._select_all, side="left",
                          primary=False)

        # Right: report
        right = tk.Frame(body, bg=BG_CARD)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        tk.Label(right, text="Conversion report", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.report_text = tk.Text(right, bg=BG, fg=FG, relief="flat",
                                   wrap="word", font=("Consolas", 9),
                                   insertbackground=FG)
        self.report_text.pack(fill="both", expand=True, padx=12, pady=8)
        self.report_text.insert("1.0", "Select profiles on the left and click "
                                        "Convert.\n")
        self.report_text.config(state="disabled")

        # Convert bar
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=20, pady=(0, 8))
        self.convert_btn = self._make_button(
            bar, "\u2699  Convert selected profiles", self._convert_clicked,
            side="right")

    def _make_button(self, parent, text, cmd, side="left", primary=True):
        color = ACCENT if primary else BG_CARD
        b = tk.Button(parent, text=text, command=cmd, bg=color, fg="white",
                      activebackground=ACCENT_HOVER, activeforeground="white",
                      relief="flat", font=("Segoe UI", 10, "bold"),
                      padx=14, pady=8, cursor="hand2", bd=0,
                      highlightthickness=0)
        b.pack(side=side, padx=4)
        return b

    def _build_statusbar(self):
        self.status = tk.Label(self.root, text="Ready", bg="#15151f",
                                fg=FG_MUTED, anchor="w", font=("Segoe UI", 9))
        self.status.pack(fill="x", side="bottom", ipady=4)

    # ----- data / actions --------------------------------------------------
    def _current_type(self) -> str:
        """Return the selected profile type ('all' or a specific type)."""
        idx = self.type_menu.current()
        if idx < 0 or idx >= len(self._type_keys):
            return "all"
        return self._type_keys[idx]

    def _profile_label(self, entry, aggregate):
        """Build the listbox row text for a profile entry."""
        if entry.get("manual"):
            tag = self._SLICER_DISPLAY.get(entry["src_key"], entry["src_key"])
            return f"  [{tag} \u00b7 {TYPE_LABELS[entry['ptype']]}]  {entry['name']}  [manual]"
        if aggregate:
            tag = self._SLICER_DISPLAY.get(entry["src_key"], entry["src_key"])
            return f"  [{tag} \u00b7 {TYPE_LABELS[entry['ptype']]}]  {entry['name']}"
        return f"  {entry['name']}"

    def _refresh_profile_list(self):
        self.listbox.delete(0, "end")
        self.profile_entries = []
        src_key = self._selected_src_key()
        ptype = self._current_type()

        src_keys = list(self.installs.keys()) if src_key == "all" else [src_key]
        types = list(PROFILE_TYPES) if ptype == "all" else [ptype]
        aggregate = (src_key == "all" or ptype == "all")

        any_detected = False
        for sk in src_keys:
            install = self.installs.get(sk)
            if not install:
                continue
            any_detected = True
            for t in types:
                for p in list_profiles(install, t):
                    try:
                        from profile_io import load_profile
                        nm = profile_name(load_profile(p), os.path.basename(p))
                    except ProfileError:
                        nm = os.path.basename(p)
                    entry = {"path": p, "src_key": sk, "ptype": t,
                             "name": nm, "manual": False}
                    self.profile_entries.append(entry)
                    self.listbox.insert("end",
                                        self._profile_label(entry, aggregate))

        if any_detected and self.profile_entries:
            if src_key == "all":
                names = ", ".join(self.installs[k].name
                                  for k in self.installs)
                self.hint_label.config(
                    text=f"Showing profiles from all detected slicers "
                         f"({names}) \u2014 read straight from disk.")
            else:
                self.hint_label.config(
                    text=f"Reading from: {self.installs[src_key].user_root}")
        elif any_detected:
            self.hint_label.config(
                text="No matching profiles found. Try a different type, or use "
                     "'Add file\u2026' to pick one manually.")
        else:
            self.hint_label.config(
                text="No supported slicer was auto-detected on this computer. "
                     "Use 'Add file\u2026' to select profile .json files "
                     "manually (e.g. from a backup or another PC).")
        self._set_status(f"{len(self.profile_entries)} profile(s) listed.")

    def _add_file_manual(self):
        files = filedialog.askopenfilenames(
            title="Select profile file(s)",
            filetypes=[
                ("All profile formats", "*.json *.ini *.cfg *.inst.cfg"),
                ("JSON profiles", "*.json"),
                ("INI profiles", "*.ini"),
                ("Cura profiles", "*.inst.cfg *.cfg"),
                ("All files", "*.*")
            ])
        existing = {e["path"] for e in self.profile_entries}
        # If a specific source slicer is chosen, prefer it; otherwise infer.
        chosen_src = self._selected_src_key()
        chosen_type = self._current_type()
        for f in files:
            if f in existing:
                continue
            try:
                from profile_io import load_profile
                nm = profile_name(load_profile(f), os.path.basename(f))
            except ProfileError:
                nm = os.path.basename(f)
            inf_src, inf_type = self._infer_from_path(f)
            src_key = chosen_src if chosen_src != "all" else (inf_src or "bambu")
            ptype = chosen_type if chosen_type != "all" else inf_type
            entry = {"path": f, "src_key": src_key, "ptype": ptype,
                     "name": nm, "manual": True}
            self.profile_entries.append(entry)
            self.listbox.insert("end", self._profile_label(entry, True))
        self._set_status(f"{len(self.profile_entries)} profile(s) listed.")

    def _select_all(self):
        self.listbox.select_set(0, "end")

    def _convert_clicked(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Select one or more profiles first.")
            return
        target_printer = self.printer_var.get().strip()
        if not target_printer:
            messagebox.showinfo(APP_TITLE, "Enter the target printer name.")
            return

        out_dir = filedialog.askdirectory(
            title="Choose output folder for converted profiles")
        if not out_dir:
            return

        chosen = [self.profile_entries[i] for i in sel]
        self.convert_btn.config(state="disabled")
        self._set_status("Converting\u2026")
        threading.Thread(
            target=self._do_convert,
            args=(chosen, target_printer, out_dir), daemon=True).start()

    def _search_dirs_for(self, src_key, ptype):
        """Inheritance search dirs: source user folders + system folders."""
        search_dirs = []
        install = self.installs.get(src_key)
        if install:
            for uid in (install.user_ids or []):
                search_dirs.append(os.path.join(install.user_root, uid, ptype))
            search_dirs.extend(system_profile_dirs(install, ptype))
        return search_dirs

    def _do_convert(self, entries, target_printer, out_dir):
        dst_key = self._selected_dst_key()

        reports = []
        errors = []
        for entry in entries:
            path = entry["path"]
            src_key = entry["src_key"]
            ptype = entry["ptype"]
            install = self.installs.get(src_key)
            src_name = install.name if install else \
                self._SLICER_DISPLAY.get(src_key, src_key)
            try:
                from profile_io import load_profile, save_profile
                data = load_profile(path)
                # include the profile's own folder for parent lookups
                dirs = [os.path.dirname(path)] + \
                    self._search_dirs_for(src_key, ptype)
                converted, report = convert_profile(
                    data=data, profile_type=ptype, src_slicer=src_key,
                    dst_slicer=dst_key, target_printer=target_printer,
                    search_dirs=dirs,
                    name_suffix=f" (from {src_name})",
                )
                out_name = suggested_filename(converted, ptype, dst_key)
                save_profile(converted, os.path.join(out_dir, out_name))
                reports.append(report)
            except Exception as exc:  # noqa: BLE001 - surface any failure
                errors.append(f"{os.path.basename(path)}: {exc}")

        self.root.after(0, self._show_reports, reports, errors, out_dir)

    def _show_reports(self, reports, errors, out_dir):
        self.convert_btn.config(state="normal")
        self.report_text.config(state="normal")
        self.report_text.delete("1.0", "end")

        if reports:
            self.report_text.insert(
                "end", f"\u2705 Converted {len(reports)} profile(s) into:\n{out_dir}\n\n")
        for r in reports:
            self.report_text.insert("end", r.as_text() + "\n\n" + ("-" * 60) + "\n\n")
        for e in errors:
            self.report_text.insert("end", f"\u274c {e}\n")

        self.report_text.config(state="disabled")
        n_warn = sum(len(r.warnings) for r in reports)
        msg = f"Done. {len(reports)} converted"
        if errors:
            msg += f", {len(errors)} failed"
        if n_warn:
            msg += f", {n_warn} warning(s) to review"
        self._set_status(msg + ".")

    def _set_status(self, text):
        self.status.config(text=text)


def main():
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
