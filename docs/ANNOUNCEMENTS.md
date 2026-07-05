# v2.0.0 Announcement Posts

Ready-to-paste copy for announcing **Slicer Profile Converter v2.0.0 – Universal Slicer Support**.

Repo: https://github.com/Netspecs/slicer-profile-converter
Release: https://github.com/Netspecs/slicer-profile-converter/releases/tag/v2.0.0

---

## 1. Reddit — r/3Dprinting, r/BambuLab, r/prusa3d, r/Cura

**Title:**
> I built a free, open-source tool that converts print profiles between 8 slicers (Bambu, Orca, Prusa, Cura, SuperSlicer, Creality, Anycubic)

**Body:**

Hey everyone! I got tired of re-dialing in the same profile every time I switched slicers or printers, so I built **Slicer Profile Converter** — a free, open-source desktop app that translates print/filament/printer profiles between the major slicers.

**v2.0.0 just dropped and now supports 8 slicers:**

- Bambu Studio
- OrcaSlicer
- PrusaSlicer
- SuperSlicer
- Ultimaker Cura
- Creality Print
- Anycubic Slicer Next
- (plus other OrcaSlicer forks)

**What it does:**
- Reads JSON (Orca family), INI (Prusa family), and Cura `.inst.cfg` profiles
- Maps ~50 settings for PrusaSlicer ↔ OrcaSlicer and ~35 for Cura ↔ OrcaSlicer
- Translates G-code template variables between dialects (`[var]` ↔ `{var[0]}`)
- Generates a conversion report so you can see exactly what mapped and what didn't
- Auto-detects your slicer installs on Windows / macOS / Linux

**It's 100% free, open source, no dependencies for end users** (standalone executables for all three OSes on the Releases page).

Download / source: https://github.com/Netspecs/slicer-profile-converter/releases/tag/v2.0.0

Would love feedback, bug reports, and PRs — especially additional setting mappings if you spot something missing. Happy printing!

*Note: cross-family conversions aren't 100% lossless (different slicers expose different settings). The tool flags anything it can't map so you can review it. Fidelity matrix is in the README.*

---

## 2. Hacker News (Show HN)

**Title:**
> Show HN: Slicer Profile Converter – translate 3D print profiles across 8 slicers

**Body:**

I built a small, dependency-free desktop app (Python + Tkinter) that converts 3D-printing profiles between 8 slicers: Bambu Studio, OrcaSlicer, PrusaSlicer, SuperSlicer, Cura, Creality Print, and Anycubic Slicer Next.

The interesting part is that these slicers use three different config formats (JSON, INI, and Cura's `.inst.cfg`) and different key names for the same physical setting. v2.0.0 adds cross-family key-mapping tables (~50 keys Prusa↔Orca, ~35 Cura↔Orca), G-code template variable translation between dialects, and a conversion report that flags anything it couldn't map.

It's MIT-licensed, zero runtime dependencies for end users (standalone binaries for Win/macOS/Linux built in CI), and pure-Python source.

Repo: https://github.com/Netspecs/slicer-profile-converter
Release: https://github.com/Netspecs/slicer-profile-converter/releases/tag/v2.0.0

Feedback and additional mapping contributions very welcome.

---

## 3. X / Twitter (thread)

**Tweet 1:**
🚀 Slicer Profile Converter v2.0.0 is out!

Convert your 3D print profiles between 8 slicers — free & open source:
Bambu Studio · OrcaSlicer · PrusaSlicer · SuperSlicer · Cura · Creality Print · Anycubic Slicer Next

🧵👇
https://github.com/Netspecs/slicer-profile-converter/releases/tag/v2.0.0

**Tweet 2:**
No more re-dialing settings when you switch slicers or printers.

✅ JSON, INI & Cura formats
✅ ~50 Prusa↔Orca + ~35 Cura↔Orca settings mapped
✅ G-code variable translation
✅ Conversion report shows what mapped

**Tweet 3:**
100% free, MIT-licensed, zero dependencies for end users.

Standalone builds for Windows, macOS & Linux on the Releases page. Source is pure Python.

PRs & feedback welcome — especially new setting mappings! #3Dprinting #BambuLab #PrusaSlicer #OrcaSlicer

---

## 4. Facebook / Discord groups (short)

🎉 **Slicer Profile Converter v2.0.0** is here!

A free, open-source tool that converts your 3D print profiles between **8 slicers**: Bambu Studio, OrcaSlicer, PrusaSlicer, SuperSlicer, Cura, Creality Print & Anycubic Slicer Next.

Stop re-tuning profiles every time you switch slicers. It maps settings across formats (JSON/INI/Cura), translates G-code variables, and gives you a report of exactly what changed.

Standalone apps for Windows, macOS & Linux — no install of Python needed.

👉 https://github.com/Netspecs/slicer-profile-converter/releases/tag/v2.0.0

---

## 5. GitHub Release social preview blurb (one-liner)

> Slicer Profile Converter v2.0.0 — now translates 3D print profiles across 8 slicers (Bambu, Orca, Prusa, SuperSlicer, Cura, Creality, Anycubic) with cross-format mapping and G-code dialect translation.
