<p align="center">
  <img src="docs/icon.png" width="120" alt="Slicer Profile Converter icon">
</p>

<h1 align="center">🔄 Slicer Profile Converter</h1>

<p align="center">
  Move your <b>filament</b>, <b>printer</b> and <b>process</b> profiles between
  <b>Bambu Studio</b>, <b>OrcaSlicer</b>, <b>Snapmaker Orca</b>, <b>Creality Print</b>, 
  <b>Anycubic Slicer</b>, <b>Ultimaker Cura</b>, <b>PrusaSlicer</b> and <b>SuperSlicer</b> —
  read straight from disk, <i>no fiddly export button required</i>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="platforms">
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen.svg" alt="no deps">
</p>

---

## 😖 The problem this solves

If you run **more than one slicer** — say Bambu Studio for your Bambu printers,
PrusaSlicer for your Prusa, and maybe Cura for an older machine — you've probably
hit these walls:

- **Bambu Studio's export is a maze.** The *Export Preset Bundle* dialog only
  lists profiles you saved as "User Presets" **and** that match your currently
  selected printer/nozzle — so the list is often mysteriously **empty**.
- **Copying profiles by hand breaks them.** Profiles *inherit* from a parent;
  move just the child and it **vanishes** in the other slicer because the parent
  is missing.
- **Profiles are "locked" to a printer.** A filament profile tied to a Bambu P1S
  won't show up for your Snapmaker or Prusa.
- **Different slicers use different formats.** OrcaSlicer family uses JSON, 
  PrusaSlicer uses INI, Cura uses its own config format — manually converting
  between them is tedious and error-prone.

**Slicer Profile Converter** fixes all of this. It reads profiles **directly from
where each slicer stores them on disk** (JSON, INI, or Cura configs), flattens the
inheritance chain into a self-contained copy, translates settings between different
slicer formats, re-targets it to the printer you choose, and writes a ready-to-use
profile — with a plain-English report of everything it changed.

---

## ✨ Features

- 🔎 **Auto-detects** Bambu Studio, OrcaSlicer, Snapmaker Orca, Creality Print,
  Anycubic Slicer, Ultimaker Cura, PrusaSlicer and SuperSlicer installs and finds
  their profile folders for you.
- 🗂️ **One combined list** — by default it shows **every profile from every
  slicer you have installed** (grouped and tagged by slicer + type), so you
  don't have to know or pick the source first. Just pick a profile, choose a
  destination slicer, and convert. Filter to a single slicer or type any time.
- 📄 **Multi-format support** — handles JSON (OrcaSlicer family), INI (PrusaSlicer/
  SuperSlicer), and Cura config files seamlessly.
- 💾 **Reads profiles straight from disk** — no need to get Bambu's export to work.
- 🧬 **Flattens inheritance** so a converted profile is self-contained and won't
  disappear in the target slicer.
- 🔄 **Cross-slicer translation** — automatically maps settings between different
  slicer families (e.g., PrusaSlicer ↔ OrcaSlicer ↔ Cura) with ~50+ common
  settings mapped per family pair.
- 🎯 **Re-targets to any printer** — pick the destination printer name and the
  profile becomes compatible with it.
- 📦 **All three profile types** — filament, printer (machine) and process/print.
- 📝 **Conversion report** — see exactly what changed and what (if anything)
  needs your review.
- 🎨 **Filament color extraction** — for filament profiles, the report shows
  the stored color (HEX + RGB), making it easy to re-assign the right color to
  AMS slots or tool-changer positions in the destination slicer.
- 🧰 **Manual mode** — point it at any `.json`, `.ini`, or `.inst.cfg` file
  (from a backup or another PC) even if that slicer isn't installed here.
- 🪶 **Zero dependencies** — pure Python + Tkinter. No pip install headaches.

---

## 📥 Download

Grab a ready-to-run build from the [**Releases**](../../releases) page — no Python needed:

- **Windows** → run the installer `SlicerProfileConverter-Setup.exe` (adds a
  desktop icon + Start Menu shortcut + uninstaller), or grab the portable `.exe`.
- **macOS** → `SlicerProfileConverter-macos`
- **Linux** → `SlicerProfileConverter-linux`

---

## 🚀 Usage

1. **From:** leave it on **All detected slicers** to see every profile from all
   your installed slicers at once (or pick a single slicer to narrow the list).
2. **Profile type:** leave it on **All types**, or filter to Filament, Printer,
   or Process.
3. Pick one or more profiles from the list — they're read from disk
   automatically and each row is tagged with its slicer and type. You can even
   select profiles from **two different slicers** in one go; each is converted
   from its own correct source.
4. **To:** choose the destination slicer (e.g. Snapmaker Orca).
5. **Target printer:** type the exact printer name as it appears in the
   destination slicer (e.g. `Snapmaker Artisan 0.4 nozzle`).
6. Click **Convert** and choose an output folder.
7. Read the report, then import the resulting `.json` into your slicer via
   **File → Import → Import Configs**, or drop it straight into the slicer's
   user folder.

> 💡 **Tip:** For filament/process profiles, the "Target printer" name must match
> a printer that already exists in the destination slicer, or the profile won't
> show up. Copy the name from the printer dropdown in that slicer.

---

## 🧠 How it works

The converter handles three slicer families with different formats:

- **OrcaSlicer family** (Bambu Studio, OrcaSlicer, Snapmaker Orca, Creality Print, 
  Anycubic Slicer) — all forks of the same engine, share JSON schema with `inherits`
- **PrusaSlicer family** (PrusaSlicer, SuperSlicer) — INI format with similar 
  inheritance model
- **Cura** — its own config format with hundreds of specialized settings

Conversion steps vary by source/destination but generally include:

| Step | What happens |
|------|--------------|
| **1. Load** | Parse the source profile (JSON, INI, or Cura config) into a normalized dict. |
| **2. Flatten** | Resolve the `inherits` chain by reading parent profiles from the source's user + system folders, merging them (child settings win). |
| **3. Translate** | If crossing slicer families (e.g., Prusa → Orca), map ~50 common settings using built-in translation tables. Unmapped settings are flagged in the report. |
| **4. Re-target** | `compatible_printers` is rewritten to your chosen printer; the compatibility condition is cleared. |
| **5. Re-identify** | The profile is renamed (`… (from <source>)`), marked as a user preset, and source-only IDs are dropped so it doesn't clash. |
| **6. G-code** | If crossing dialects, template variables are translated (e.g., PrusaSlicer `[var]` ↔ OrcaSlicer `{var[0]}`). |
| **7. Report** | Every change is logged, plus warnings for anything to double-check (missing parents, unmapped settings, machine geometry, unknown G-code vars). |

Where profiles live on disk (the folders the app scans):

| Slicer | Windows | macOS | Linux |
|--------|---------|-------|-------|
| **OrcaSlicer family**<br>(Bambu Studio, OrcaSlicer,<br>Snapmaker Orca, Creality Print,<br>Anycubic Slicer) | `%AppData%\Roaming\<Slicer>\user\<id>\`<br>`{filament,machine,process}\*.json` | `~/Library/Application Support/`<br>`<Slicer>/user/<id>/…` | `~/.config/<Slicer>/`<br>`user/<id>/…` |
| **PrusaSlicer family**<br>(PrusaSlicer, SuperSlicer) | `%AppData%\Roaming\<Slicer>\`<br>`{filament,print,printer}\*.ini` | `~/Library/Application Support/`<br>`<Slicer>/…` | `~/.config/<Slicer>/…` |
| **Cura** | `%AppData%\Roaming\cura\<version>\`<br>`{materials,quality_changes,machine_instances}\*` | `~/Library/Application Support/`<br>`cura/<version>/…` | `~/.config/cura/`<br>`<version>/…` |

---

## 🛠️ Run from source

```bash
git clone https://github.com/Netspecs/slicer-profile-converter.git
cd slicer-profile-converter
python3 app.py
```

Linux users may need Tkinter: `sudo apt install python3-tk`.

### Run the tests

```bash
python3 test_converter.py
```

---

## ⚠️ Notes & limitations

**Conversion fidelity by slicer pair:**

- **Within OrcaSlicer family** (Bambu ↔ Orca ↔ Snapmaker ↔ Creality ↔ Anycubic) — 
  **near-perfect** conversion (same JSON schema).
- **PrusaSlicer ↔ SuperSlicer** — **near-perfect** (same INI format, minimal differences).
- **PrusaSlicer/SuperSlicer ↔ OrcaSlicer family** — **high-fidelity** (~50 common 
  settings mapped: layer heights, temperatures, speeds, infill, support, retraction, 
  cooling, extrusion). Unmapped advanced settings are flagged in the report.
- **Cura ↔ OrcaSlicer family** — **moderate** (~35 common settings mapped). Cura has 
  400+ settings; unmapped settings are flagged. Works well for basic filament/print
  profiles.
- **Cura ↔ PrusaSlicer** — **basic** (not recommended; convert via an intermediate
  OrcaSlicer-family slicer for better results).

**Other notes:**

- **Filament colors travel with the profile** — the stored color (HEX/RGB) is
  preserved and shown in the report. However, **AMS slot assignments and
  tool-changer mappings** are not stored in reusable profiles; those live in
  project files (`.3mf`) and must be set up manually in the destination slicer
  after importing the converted profile.
- **G-code template variables** are translated between PrusaSlicer (`[var]`) and
  OrcaSlicer (`{var[0]}`) dialects. Unknown variables are flagged for manual review.
- Always keep a backup of your original profiles. Converted profiles are written
  to a folder **you** choose — the app never overwrites your originals.

---

## 📄 License

[MIT](LICENSE) © 2026 Netspecs
