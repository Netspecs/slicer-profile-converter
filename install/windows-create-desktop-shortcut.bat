@echo off
REM =====================================================================
REM  Slicer Profile Converter - create a Desktop shortcut (Windows)
REM
REM  HOW TO USE:
REM   1. Put this .bat in the SAME folder as
REM      SlicerProfileConverter-windows.exe
REM   2. Double-click this .bat file.
REM   3. A shortcut (with the app icon) appears on your Desktop.
REM =====================================================================

setlocal
set "EXE=%~dp0SlicerProfileConverter-windows.exe"

if not exist "%EXE%" (
    echo Could not find SlicerProfileConverter-windows.exe next to this file.
    echo Please keep this .bat in the same folder as the .exe and try again.
    pause
    exit /b 1
)

set "SHORTCUT=%USERPROFILE%\Desktop\Slicer Profile Converter.lnk"

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath='%EXE%';" ^
  "$s.WorkingDirectory=Split-Path '%EXE%';" ^
  "$s.IconLocation='%EXE%,0';" ^
  "$s.Description='Convert 3D printing slicer profiles between Bambu Studio, OrcaSlicer and Snapmaker Orca';" ^
  "$s.Save()"

echo.
echo Done! A "Slicer Profile Converter" icon is now on your Desktop.
pause
