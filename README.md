# Lizenz-Generator (Python)

Ein professionelles Desktop-Programm zum Erstellen und Prüfen signierter Lizenzdateien – jetzt in der **Professional-Version** mit ECDSA-Verschlüsselung, Hardware-Bindung (HWID) und automatisierter Build-Pipeline.

## Versionen

### Standard (`license_manager.py`)
- **Signatur**: HMAC-SHA256 (Shared Secret)
- **Datenbank**: MySQL/MariaDB (optional)
- **UI**: Klassisches Tkinter/ttk

### Professional (`license_manager_pro.py`) [AKTUELL]
- **Signatur**: **ECDSA (P-256)** (Asymmetrische Verschlüsselung)
- **HWID-Schutz**: Bindet Lizenzen an die Hardware (CPU/HDD) des Kunden.
- **Modernes UI**: Basierend auf `customtkinter` (Dark/Light Mode).
- **Auto-Update**: Sucht Updates direkt über die GitHub-API.
- **Verifizierung**: Integriertes Tool zum Prüfen von Lizenzdateien inkl. HWID-Check.

## Installation & Start

1. **Abhängigkeiten installieren**:
   ```powershell
   pip install customtkinter requests cryptography wmi mysql-connector-python
   ```

2. **Programm starten**:
   ```powershell
   # Pro-Version (Empfohlen)
   python .\license_manager_pro.py

   # Standard-Version
   python .\license_manager.py
   ```

## Funktionen (Pro-Version)

- **Generator**: Erstellt kryptografisch signierte `.license.json` Dateien.
- **Datenbank**: Alle Lizenzen werden (wenn aktiviert) in einer MySQL-Datenbank archiviert.
- **Verifizierung**: Prüft Signaturen, Ablaufdaten und Hardware-Berechtigungen.
- **Sicherheit**: Verwendet asymmetrische Kryptografie. Der Private Key bleibt beim Generator, der Public Key wird in die Lizenz eingebettet.

## Build-Automatisierung

Für die Verteilung steht ein PowerShell-Skript bereit:
```powershell
.\build_pro.ps1
```
Dies automatisiert:
1. Erstellung der EXE via PyInstaller.
2. Kompilierung des Installers (`installer_pro.iss`) via Inno Setup.

## Datenbankanbindung

1. Reiter **„Einstellungen"** öffnen.
2. Host, User, Passwort und Datenbank eintragen.
3. **„Speichern & Testen"** klicken. Die Tabelle `licenses` wird automatisch angelegt.

Ab sofort wird jede neu ausgestellte Lizenz in der Datenbank gespeichert und kann in der **„Datenbank-Übersicht"** verwaltet (z.B. gesperrt) werden.

## Technik & Sicherheit

- **Asymmetrische Signatur**: ECDSA mit dem Kurven-Typ P-256.
- **HWID**: Besteht aus einem SHA256-Hash der Prozessor-ID und der Festplatten-Seriennummer.
- **Lizenzformat**: JSON-Datei mit eingebettetem Public Key zur einfachen Verifizierung im Zielprogramm.

---
Entwickelt von **TGH-Scripts**.
