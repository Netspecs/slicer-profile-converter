; =====================================================================
;  Slicer Profile Converter - Windows Installer (Inno Setup script)
;
;  Produces an installer that:
;    * Installs the app (per-user, no admin rights needed)
;    * Creates a Desktop shortcut (with the custom icon)
;    * Creates a Start Menu shortcut
;    * Registers an Uninstaller in "Apps & features" / "Programs and Features"
;
;  Compiled automatically by GitHub Actions (see .github/workflows/build.yml),
;  or locally with Inno Setup 6:
;    1. pyinstaller build.spec --noconfirm
;    2. Open this file in Inno Setup and Compile (or run ISCC.exe).
; =====================================================================

#define MyAppName "Slicer Profile Converter"
#define MyAppVersion "1.0"
#define MyAppPublisher "Netspecs"
#define MyAppURL "https://github.com/Netspecs/slicer-profile-converter"
#define MyAppExeName "SlicerProfileConverter.exe"

[Setup]
; Keep this GUID stable across versions so updates replace the same entry.
AppId={{F16E957A-A852-499F-A0D8-CB462476258E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; OutputDir is relative to this script's folder (installer/).
OutputDir=..\installer_output
OutputBaseFilename=SlicerProfileConverter-Setup
SetupIconFile=..\docs\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
MinVersion=6.1sp1

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
