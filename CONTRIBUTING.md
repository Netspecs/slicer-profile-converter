# Contributing to Slicer Profile Converter

Thanks for your interest in improving the project! 🎉

## Ways to help

- 🐛 **Report bugs** — open an issue with the slicer versions involved, the
  profile type, and (if possible) a sanitized copy of the profile that failed.
- 🔀 **Add key mappings** — help expand the PrusaSlicer `.ini` ↔ Orca-family
  key/G-code mappings in `gcode_translate.py` and `converter.py`.
- 🧪 **Add test profiles** — drop anonymized real-world profiles in `samples/`
  and add a case to `test_converter.py`.
- 📖 **Docs** — clarify anything confusing in the README.

## Dev setup

```bash
git clone https://github.com/Netspecs/slicer-profile-converter.git
cd slicer-profile-converter
python3 app.py           # run the GUI
python3 test_converter.py  # run the tests
```

No third-party dependencies are required to run or test the core.

## Guidelines

- Keep the **core engine dependency-free** (standard library only). Optional
  extras (Pillow, PyInstaller) are fine but must not be required to run the app.
- Every conversion behavior change should come with a test in
  `test_converter.py`.
- Match the existing code style (clear names, docstrings, comments explaining
  *why*).
- Open a PR against `main`. Please describe what you changed and why.

## Code of conduct

Be kind and constructive. We're all here to make multi-slicer life easier. 🙂
