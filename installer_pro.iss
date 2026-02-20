; ============================================================
;  Inno Setup Script – Lizenz-Generator PROFESSIONAL
;  Erstellt: 2026-02-20
; ============================================================

#define AppName      "Lizenz-Generator Pro"
#define AppVersion   "2.1.0"
#define AppPublisher "TGH-Scripts"
#define AppExeName   "LizenzGeneratorPro.exe"
#define SourceExe    "dist\LizenzGeneratorPro.exe"

[Setup]
; Eindeutige AppId für die Pro-Version
AppId={{9B4F1C2D-C5F6-5A7B-0D2E-F1A2B3C4D5E6}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
; Speicherort für das fertige Setup
OutputDir=installer_output
OutputBaseFilename=LizenzGeneratorPro_Setup
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
; Die Pro-EXE (enthält alle Abhängigkeiten)
Source: "{#SourceExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{#AppName} jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
