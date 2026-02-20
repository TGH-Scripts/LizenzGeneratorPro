# Professional License Manager – Build Automation Script
# Automates PyInstaller (EXE) and Inno Setup (Installer)

$AppName = "Lizenz-Generator Pro"
$SpecFile = "LizenzGeneratorPro.spec"
$IssFile = "installer_pro.iss"
$OutputDir = "dist"
$SetupDir = "installer_output"

Write-Host "--- Start Build: $AppName ---" -ForegroundColor Cyan

# 1. PyInstaller
$PyI = ".\.venv\Scripts\pyinstaller.exe"
if (!(Test-Path $PyI)) {
    $PyI = Get-Command "pyinstaller" -ErrorAction SilentlyContinue
}

if ($PyI) {
    Write-Host "[1/2] Starte PyInstaller ($PyI)..." -ForegroundColor Yellow
    & $PyI --noconfirm --clean $SpecFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PyInstaller Fehler!"
        exit $LASTEXITCODE
    }
    Write-Host "✔ EXE erfolgreich erstellt in $OutputDir" -ForegroundColor Green
} else {
    Write-Error "PyInstaller wurde nicht gefunden. Bitte 'pip install pyinstaller' ausführen."
    exit 1
}

# 2. Inno Setup (Optional if ISCC is in PATH)
$ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (!(Test-Path "$ISCC")) {
    $ISCC = (Get-Command "iscc.exe" -ErrorAction SilentlyContinue).Source
}

if ($ISCC) {
    Write-Host "[2/2] Starte Inno Setup Compiler ($ISCC)..." -ForegroundColor Yellow
    & "$ISCC" $IssFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Inno Setup Fehler!"
        exit $LASTEXITCODE
    }
    Write-Host "✔ Setup erfolgreich erstellt in $SetupDir" -ForegroundColor Green
} else {
    Write-Warning "Inno Setup Compiler (ISCC.exe) nicht gefunden. Nur die EXE wurde erstellt."
}

Write-Host "--- Build Abgeschlossen ---" -ForegroundColor Cyan
