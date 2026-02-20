; ============================================================
;  Inno Setup Script – Lizenz-Generator
;  Erstellt: 2026-02-20
; ============================================================

#define AppName      "Lizenz-Generator Pro"
#define AppVersion   "2.0"
#define AppPublisher "Antigravity License Systems"
#define AppExeName   "LizenzGeneratorPro.exe"
#define SourceExe    "dist\LizenzGeneratorPro.exe"

[Setup]
AppId={{8A3F1C2D-B4E5-4F6A-9C1D-E2F3A4B5C6D7}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
ForceOutputDir=yes
OutputBaseFilename=LizenzGeneratorPro_Setup
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Mindest-Windows-Version: Windows 10
MinVersion=10.0
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Aufgaben:"; Flags: checkedonce

[Files]
; Die fertige EXE (Python bereits eingebettet – keine getrennte Python-Installation nötig)
Source: "{#SourceExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{#AppName} jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
