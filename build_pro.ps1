# Professional License Manager – Build Automation Script
# Automates PyInstaller (EXE) and Inno Setup (Installer)

$AppName = "Lizenz-Generator Pro"
$SpecFile = "LizenzGeneratorPro.spec"
$IssFile = "installer_pro.iss"
$OutputDir = "dist"
$SetupDir = "installer_output"

Write-Host "--- Start Build: $AppName ---" -ForegroundColor Cyan

# 1. PyInstaller
if (Get-Command "pyinstaller" -ErrorAction SilentlyContinue) {
    Write-Host "[1/2] Starte PyInstaller..." -ForegroundColor Yellow
    pyinstaller --noconfirm --clean $SpecFile
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
if (!(Test-Path $ISCC)) {
    $ISCC = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
}

if ($ISCC) {
    Write-Host "[2/2] Starte Inno Setup Compiler..." -ForegroundColor Yellow
    & $ISCC $IssFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Inno Setup Fehler!"
        exit $LASTEXITCODE
    }
    Write-Host "✔ Setup erfolgreich erstellt in $SetupDir" -ForegroundColor Green
} else {
    Write-Warning "Inno Setup Compiler (ISCC.exe) nicht gefunden. Nur die EXE wurde erstellt."
}

Write-Host "--- Build Abgeschlossen ---" -ForegroundColor Cyan
