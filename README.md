# Lizenz-Generator (Python)

Ein kleines Desktop-Programm zum Erstellen und Prüfen signierter Lizenzdateien – mit optionaler MySQL/MariaDB-Datenbankanbindung.

## Funktionen

- Lizenzschlüssel generieren
- Lizenzdaten eingeben (Kunde, Produkt, Sitze, Datum)
- Lizenz als `.license.json` speichern
- Lizenzdatei mit Secret verifizieren
- Ablaufdatum prüfen
- **Neu:** Ausgestellte Lizenzen automatisch in eine MySQL/MariaDB-Datenbank eintragen

## Starten

Voraussetzung: Python 3.10+ auf Windows.

```powershell
python .\license_manager.py
```

## Datenbankanbindung

### Voraussetzung

```powershell
pip install mysql-connector-python
```

### Einrichtung

1. Reiter **„Datenbank"** öffnen
2. Checkbox **„Datenbank aktivieren"** setzen
3. Host, Port, Benutzer, Passwort und Datenbankname eintragen
4. **„Verbindung testen"** klicken – die Tabelle `licenses` wird automatisch angelegt
5. **„Einstellungen übernehmen"** klicken

Ab sofort wird jede neu ausgestellte Lizenz zusätzlich zur JSON-Datei auch in der Datenbank gespeichert.

### Tabellenstruktur (`licenses`)

| Spalte        | Typ           | Beschreibung                        |
|---------------|---------------|-------------------------------------|
| `id`          | INT (PK)      | Auto-Increment                      |
| `license_key` | VARCHAR(64)   | Eindeutiger Lizenzschlüssel (UNIQUE)|
| `customer`    | VARCHAR(255)  | Kundenname                          |
| `product`     | VARCHAR(255)  | Produktname                         |
| `seats`       | INT           | Anzahl der Sitze                    |
| `issued_at`   | DATE          | Ausstellungsdatum                   |
| `expires_at`  | DATE (NULL)   | Ablaufdatum (optional)              |
| `notes`       | TEXT          | Notizen                             |
| `algorithm`   | VARCHAR(32)   | Signaturalgorithmus                 |
| `signature`   | VARCHAR(512)  | HMAC-SHA256-Signatur                |
| `created_at`  | DATETIME      | Eintragedatum in DB                 |

## Hinweise

- Das **Secret** muss sicher aufbewahrt werden.
- Nur mit demselben Secret kann eine Lizenz korrekt geprüft werden.
- Eine Lizenzdatei enthält:
  - `license`: die eigentlichen Lizenzdaten
  - `signature`: HMAC-SHA256-Signatur
  - `algorithm`: verwendeter Signatur-Algorithmus
- Die Datenbankanbindung ist **optional** – das Tool funktioniert auch ohne sie.
