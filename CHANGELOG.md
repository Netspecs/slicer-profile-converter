# Changelog

All notable changes to Slicer Profile Converter will be documented in this file.

## [2.0.0] - 2026-07-05

### 🎉 Major Release: Universal Slicer Support

This release expands support from 3 slicers to **8 slicers** covering all major 3D printing slicer applications!

### Added

#### New Slicer Support (5 additional slicers)
- **Creality Print** — Full JSON profile support (OrcaSlicer fork)
- **Anycubic Slicer** — Full JSON profile support (OrcaSlicer fork)
- **Ultimaker Cura** — Full `.inst.cfg` / `.cfg` / `.fdm_material` support with ~35 setting mappings
- **PrusaSlicer** — Full `.ini` profile support with ~50 setting mappings
- **SuperSlicer** — Full `.ini` profile support (PrusaSlicer fork)

#### Multi-Format Profile Support
- **JSON profiles** — OrcaSlicer family (Bambu Studio, OrcaSlicer, Snapmaker Orca, Creality Print, Anycubic Slicer)
- **INI profiles** — PrusaSlicer family (PrusaSlicer, SuperSlicer)
- **Cura configs** — Ultimaker Cura (`.inst.cfg`, `.cfg`, `.fdm_material`)

#### Cross-Slicer Translation
- **PrusaSlicer ↔ OrcaSlicer** translation with ~50 common settings mapped:
  - Layer heights, perimeters/walls, infill patterns
  - Temperatures (nozzle, bed, first layer)
  - Speeds (perimeter, infill, travel, bridge, first layer)
  - Support material settings
  - Retraction settings
  - Cooling/fan control
  - Extrusion width and multiplier
  - Skirt/brim settings
  
- **Cura ↔ OrcaSlicer** translation with ~35 common settings mapped:
  - Layer heights and shell settings
  - Infill density and patterns
  - Temperatures and speed profiles
  - Support and retraction
  - Cooling and adhesion

- **G-code template variable translation** between PrusaSlicer (`[var]`) and OrcaSlicer (`{var[0]}`) dialects
- Unmapped settings are flagged in conversion reports for manual review

#### Enhanced Detection
- Auto-detects all 8 slicers across Windows, macOS, and Linux
- Handles version-specific folders (e.g., Cura 5.x)
- Supports different profile folder structures per slicer family

#### UI Improvements
- All 8 slicers available in source/destination dropdowns
- Multi-format file picker (`.json`, `.ini`, `.inst.cfg`, `.cfg`)
- Updated header text to reflect all supported slicers
- Enhanced path inference for manual file selection

### Changed

- **Conversion fidelity tiers** now documented in README:
  - Near-perfect: within OrcaSlicer family, PrusaSlicer ↔ SuperSlicer
  - High-fidelity: PrusaSlicer ↔ OrcaSlicer family
  - Moderate: Cura ↔ OrcaSlicer family
  - Basic: Cura ↔ PrusaSlicer (use intermediate conversion)

- **Profile I/O** now supports all three formats with automatic detection
- **Conversion reports** now show which settings were mapped/unmapped for cross-family conversions
- **Suggested filenames** now use correct extension (`.json`, `.ini`, or `.inst.cfg`) based on destination slicer

### Technical Details

#### Backend Enhancements
- `slicer_paths.py`: Added detection for 5 new slicers with format-specific handling
- `profile_io.py`: Full INI and Cura config parser/writer implementations
- `converter.py`: Comprehensive key mapping tables for all slicer family pairs
- `app.py`: Multi-format support in UI, enhanced path inference

#### File Format Support
- **PrusaSlicer INI**: Custom parser handles sections, comments, key-value pairs
- **Cura configs**: ConfigParser-based reader/writer with section flattening
- **Inheritance resolution**: Works across all three format families

---

## [1.0.0] - 2026-07-04

### Initial Release

#### Features
- Support for Bambu Studio, OrcaSlicer, and Snapmaker Orca
- Auto-detection of slicer installations
- Profile inheritance flattening
- Printer re-targeting
- Filament color extraction
- Conversion reports
- Manual file mode
- Zero dependencies (pure Python + Tkinter)
