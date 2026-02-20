import base64
import hashlib
import hmac
import json
import os
import secrets
import string
import tkinter as tk
from dataclasses import dataclass, asdict
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# Optionaler MySQL-Import – kein Pflichtpaket
try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


LICENSE_VERSION = 1
DATE_FORMAT = "%Y-%m-%d"

# SQL-Tabelle, die beim ersten Verbindungstest automatisch angelegt wird
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS licenses (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    license_key   VARCHAR(64)   NOT NULL UNIQUE,
    customer      VARCHAR(255)  NOT NULL,
    product       VARCHAR(255)  NOT NULL,
    seats         INT           NOT NULL DEFAULT 1,
    issued_at     DATE          NOT NULL,
    expires_at    DATE          NULL,
    notes         TEXT,
    algorithm     VARCHAR(32)   NOT NULL,
    signature     VARCHAR(512)  NOT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def create_license_key(groups: int = 4, chars_per_group: int = 5) -> str:
    alphabet = string.ascii_uppercase + string.digits
    chunks = []
    for _ in range(groups):
        chunks.append("".join(secrets.choice(alphabet) for _ in range(chars_per_group)))
    return "-".join(chunks)


def iso_date_or_empty(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    datetime.strptime(value, DATE_FORMAT)
    return value


def b64_signature(data: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


# ---------------------------------------------------------------------------
# Datenklasse
# ---------------------------------------------------------------------------

@dataclass
class LicenseData:
    version: int
    key: str
    customer: str
    product: str
    seats: int
    issued_at: str
    expires_at: str
    notes: str

    def canonical_payload(self) -> str:
        payload = asdict(self)
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


# ---------------------------------------------------------------------------
# Datenbankhelfer
# ---------------------------------------------------------------------------

class DatabaseManager:
    """Verwaltet die MySQL/MariaDB-Verbindung und das Speichern von Lizenzen."""

    def __init__(self):
        self._cfg: dict | None = None

    def configure(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        connect_timeout: int = 10,
        use_ssl: bool = False,
        ssl_ca: str = "",
    ):
        self._cfg = dict(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=connect_timeout,   # korrekter Parametername
        )
        if use_ssl:
            # SSL via dediziertes dict übergeben
            ssl_dict: dict = {"verify_cert": True}
            if ssl_ca:
                ssl_dict["ca"] = ssl_ca
            self._cfg["ssl"] = ssl_dict
        # kein ssl_disabled – Parameter wird nur ignoriert oder wirft Fehler

    def _connect(self):
        if not MYSQL_AVAILABLE:
            raise RuntimeError(
                "mysql-connector-python ist nicht installiert.\n"
                "Bitte führe aus:\n  pip install mysql-connector-python"
            )
        if not self._cfg:
            raise RuntimeError("Keine Datenbankverbindung konfiguriert.")
        return mysql.connector.connect(**self._cfg)

    def test_connection(self) -> str:
        """Verbindet zur DB, legt Tabelle an falls nötig und gibt Serverversion zurück."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(CREATE_TABLE_SQL)
            conn.commit()
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
            cur.close()
            return version
        finally:
            conn.close()

    def insert_license(self, license_data: LicenseData, signature: str, algorithm: str = "HMAC-SHA256"):
        """Speichert eine Lizenz in der Datenbank. Gibt True zurück bei Erfolg."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = """
                INSERT INTO licenses
                    (license_key, customer, product, seats, issued_at, expires_at, notes, algorithm, signature)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    customer   = VALUES(customer),
                    product    = VALUES(product),
                    seats      = VALUES(seats),
                    issued_at  = VALUES(issued_at),
                    expires_at = VALUES(expires_at),
                    notes      = VALUES(notes),
                    algorithm  = VALUES(algorithm),
                    signature  = VALUES(signature)
            """
            cur.execute(sql, (
                license_data.key,
                license_data.customer,
                license_data.product,
                license_data.seats,
                license_data.issued_at or None,
                license_data.expires_at or None,
                license_data.notes,
                algorithm,
                signature,
            ))
            conn.commit()
            cur.close()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Haupt-App
# ---------------------------------------------------------------------------

class LicenseManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Lizenz-Generator")
        self.root.geometry("860x720")
        self.root.minsize(800, 640)

        self.db = DatabaseManager()

        # --- Formular-Variablen ---
        self.secret_var = tk.StringVar()
        self.key_var = tk.StringVar(value=create_license_key())
        self.customer_var = tk.StringVar()
        self.product_var = tk.StringVar()
        self.seats_var = tk.StringVar(value="1")
        self.issued_at_var = tk.StringVar(value=datetime.now().strftime(DATE_FORMAT))
        self.expires_at_var = tk.StringVar()

        # --- DB-Variablen ---
        self.db_enabled_var = tk.BooleanVar(value=False)
        self.db_host_var = tk.StringVar(value="localhost")
        self.db_port_var = tk.StringVar(value="3306")
        self.db_user_var = tk.StringVar(value="root")
        self.db_pass_var = tk.StringVar()
        self.db_name_var = tk.StringVar(value="licenses")
        self.db_timeout_var = tk.StringVar(value="10")
        self.db_ssl_var = tk.BooleanVar(value=False)
        self.db_ssl_ca_var = tk.StringVar()

        self._build_ui()

    # -----------------------------------------------------------------------
    # UI-Aufbau
    # -----------------------------------------------------------------------

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Lizenz
        self.tab_license = ttk.Frame(notebook, padding=16)
        notebook.add(self.tab_license, text="  Lizenz  ")
        self._build_license_tab(self.tab_license)

        # Tab 2: Datenbank
        self.tab_db = ttk.Frame(notebook, padding=16)
        notebook.add(self.tab_db, text="  Datenbank  ")
        self._build_db_tab(self.tab_db)

    def _build_license_tab(self, frame: ttk.Frame):
        title = ttk.Label(frame, text="Lizenz erstellen und prüfen", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Signatur-Secret (wichtig):").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.secret_var, width=60, show="*").grid(row=1, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(frame, text="Secret erzeugen", command=self.generate_secret).grid(row=1, column=2, sticky="ew")

        ttk.Label(frame, text="Lizenzschlüssel:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.key_var, width=60).grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        ttk.Button(frame, text="Neu erzeugen", command=self.generate_key).grid(row=2, column=2, sticky="ew", pady=(10, 0))

        ttk.Label(frame, text="Kunde:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.customer_var).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(10, 0))

        ttk.Label(frame, text="Produkt:").grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.product_var).grid(row=4, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(10, 0))

        ttk.Label(frame, text="Sitze (Anzahl):").grid(row=5, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.seats_var).grid(row=5, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))

        ttk.Label(frame, text=f"Ausgestellt am ({DATE_FORMAT}):").grid(row=6, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.issued_at_var).grid(row=6, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))

        ttk.Label(frame, text=f"Läuft ab am ({DATE_FORMAT}, optional):").grid(row=7, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.expires_at_var).grid(row=7, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))

        ttk.Label(frame, text="Notizen (optional):").grid(row=8, column=0, sticky="nw", pady=(10, 0))
        self.notes_text = tk.Text(frame, height=5, wrap=tk.WORD)
        self.notes_text.grid(row=8, column=1, columnspan=2, sticky="nsew", padx=(8, 0), pady=(10, 0))

        button_row = ttk.Frame(frame)
        button_row.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(14, 10))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        ttk.Button(button_row, text="Lizenz erzeugen & speichern", command=self.save_license).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(button_row, text="Lizenzdatei prüfen", command=self.verify_license_file).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(button_row, text="Formular leeren", command=self.clear_form).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        ttk.Label(frame, text="Ausgabe:").grid(row=10, column=0, sticky="nw")
        self.output = tk.Text(frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.output.grid(row=10, column=1, columnspan=2, sticky="nsew", padx=(8, 0))

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(8, weight=1)
        frame.rowconfigure(10, weight=1)

    def _build_db_tab(self, frame: ttk.Frame):
        title = ttk.Label(frame, text="Datenbankverbindung", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # Aktivierung
        ttk.Checkbutton(
            frame,
            text="Datenbank aktivieren – Lizenzen werden beim Speichern automatisch eingetragen",
            variable=self.db_enabled_var,
            command=self._toggle_db_fields,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Separator(frame, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        # ── Verbindungsfelder ──────────────────────────────────────────────
        self._db_entries = []

        def _entry_row(row, label, var, show="", tooltip=""):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            e = ttk.Entry(frame, textvariable=var, show=show, width=48)
            e.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)
            self._db_entries.append(e)
            return e

        _entry_row(3,  "Host / IP:",       self.db_host_var)
        _entry_row(4,  "Port:",            self.db_port_var)
        _entry_row(5,  "Benutzer:",        self.db_user_var)
        _entry_row(6,  "Passwort:",        self.db_pass_var, show="*")
        _entry_row(7,  "Datenbank:",       self.db_name_var)
        _entry_row(8,  "Timeout (s):",     self.db_timeout_var)

        # ── SSL / TLS ──────────────────────────────────────────────────────
        ttk.Separator(frame, orient="horizontal").grid(row=9, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        ttk.Label(frame, text="Sicherheit", font=("Segoe UI", 10, "bold")).grid(
            row=10, column=0, sticky="w", pady=(0, 4))

        self._ssl_cb = ttk.Checkbutton(
            frame,
            text="SSL/TLS aktivieren (empfohlen für externe Server)",
            variable=self.db_ssl_var,
            command=self._toggle_ssl_fields,
        )
        self._ssl_cb.grid(row=11, column=0, columnspan=3, sticky="w")

        ttk.Label(frame, text="CA-Zertifikat (optional):").grid(row=12, column=0, sticky="w", pady=4)
        self._ssl_ca_entry = ttk.Entry(frame, textvariable=self.db_ssl_ca_var, width=38)
        self._ssl_ca_entry.grid(row=12, column=1, sticky="ew", padx=(8, 4), pady=4)
        self._ssl_ca_btn = ttk.Button(frame, text="Durchsuchen…", command=self._browse_ssl_ca)
        self._ssl_ca_btn.grid(row=12, column=2, sticky="ew", pady=4)
        self._db_entries += [self._ssl_ca_entry]

        # ── Hinweis ────────────────────────────────────────────────────────
        ttk.Separator(frame, orient="horizontal").grid(row=13, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        hint = ttk.Label(
            frame,
            text=(
                "Tipp: Für externe Server den öffentlichen Hostname oder die IP eintragen.\n"
                "SSL aktivieren und ggf. das CA-Zertifikat des Servers hinterlegen.\n"
                "Die Tabelle 'licenses' wird beim Verbindungstest automatisch angelegt."
            ),
            foreground="gray",
            font=("Segoe UI", 9),
            justify="left",
        )
        hint.grid(row=14, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # ── Schaltflächen ──────────────────────────────────────────────────
        btn_row = ttk.Frame(frame)
        btn_row.grid(row=15, column=0, columnspan=3, sticky="ew", pady=(4, 2))
        for c in range(4):
            btn_row.columnconfigure(c, weight=1)

        ttk.Button(btn_row, text="Verbindung testen",      command=self.test_db_connection).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(btn_row, text="Einstellungen speichern", command=self.save_db_config).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btn_row, text="Einstellungen laden",    command=self.load_db_config).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btn_row, text="Übernehmen",             command=self.apply_db_settings).grid(row=0, column=3, sticky="ew", padx=(4, 0))

        self.db_status_var = tk.StringVar(value="Keine Verbindung konfiguriert.")
        ttk.Label(frame, textvariable=self.db_status_var, foreground="gray",
                  font=("Segoe UI", 9, "italic")).grid(row=16, column=0, columnspan=3, sticky="w", pady=(4, 0))

        frame.columnconfigure(1, weight=1)
        self._toggle_db_fields()
        self._toggle_ssl_fields()

    # -----------------------------------------------------------------------
    # Datenbank-Aktionen
    # -----------------------------------------------------------------------

    def _toggle_db_fields(self):
        state = tk.NORMAL if self.db_enabled_var.get() else tk.DISABLED
        for e in self._db_entries:
            e.configure(state=state)
        ssl_state = tk.NORMAL if (self.db_enabled_var.get() and self.db_ssl_var.get()) else tk.DISABLED
        self._ssl_ca_entry.configure(state=ssl_state)
        self._ssl_ca_btn.configure(state=ssl_state)
        self._ssl_cb.configure(state=state)

    def _toggle_ssl_fields(self):
        ssl_state = tk.NORMAL if (self.db_enabled_var.get() and self.db_ssl_var.get()) else tk.DISABLED
        self._ssl_ca_entry.configure(state=ssl_state)
        self._ssl_ca_btn.configure(state=ssl_state)

    def _browse_ssl_ca(self):
        path = filedialog.askopenfilename(
            title="CA-Zertifikat auswählen",
            filetypes=[("PEM-Zertifikat", "*.pem *.crt *.cer"), ("Alle Dateien", "*.*")],
        )
        if path:
            self.db_ssl_ca_var.set(path)

    def apply_db_settings(self):
        if not self.db_enabled_var.get():
            self.db_status_var.set("Datenbank ist deaktiviert.")
            return
        try:
            port = int(self.db_port_var.get().strip())
        except ValueError:
            messagebox.showerror("Fehler", "Port muss eine Zahl sein.")
            return
        try:
            timeout = int(self.db_timeout_var.get().strip())
        except ValueError:
            timeout = 10
        self.db.configure(
            host=self.db_host_var.get().strip(),
            port=port,
            user=self.db_user_var.get().strip(),
            password=self.db_pass_var.get(),
            database=self.db_name_var.get().strip(),
            connect_timeout=timeout,
            use_ssl=self.db_ssl_var.get(),
            ssl_ca=self.db_ssl_ca_var.get().strip(),
        )
        self.db_status_var.set("Einstellungen übernommen – noch nicht getestet.")

    def test_db_connection(self):
        self.apply_db_settings()
        if not self.db_enabled_var.get():
            return
        try:
            version = self.db.test_connection()
            ssl_info = " (SSL aktiv)" if self.db_ssl_var.get() else ""
            self.db_status_var.set(f"✔ Verbunden{ssl_info} – Version: {version}")
            messagebox.showinfo(
                "Datenbankverbindung",
                f"Verbindung erfolgreich{ssl_info}!\nServerversion: {version}\n\nTabelle 'licenses' ist bereit."
            )
        except Exception as exc:
            self.db_status_var.set(f"✘ Fehler: {exc}")
            messagebox.showerror("Datenbankfehler", str(exc))

    # ---- Einstellungen speichern / laden ----------------------------------

    _CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".db_config.json")

    def save_db_config(self):
        cfg = {
            "enabled":  self.db_enabled_var.get(),
            "host":     self.db_host_var.get(),
            "port":     self.db_port_var.get(),
            "user":     self.db_user_var.get(),
            "password": self.db_pass_var.get(),
            "database": self.db_name_var.get(),
            "timeout":  self.db_timeout_var.get(),
            "ssl":      self.db_ssl_var.get(),
            "ssl_ca":   self.db_ssl_ca_var.get(),
        }
        try:
            with open(self._CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            messagebox.showinfo("Gespeichert", f"Einstellungen gespeichert:\n{self._CONFIG_FILE}")
        except Exception as exc:
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{exc}")

    def load_db_config(self):
        path = filedialog.askopenfilename(
            title="DB-Konfiguration laden",
            initialfile=".db_config.json",
            initialdir=os.path.dirname(self._CONFIG_FILE),
            filetypes=[("JSON-Konfiguration", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.db_enabled_var.set(cfg.get("enabled", False))
            self.db_host_var.set(cfg.get("host", "localhost"))
            self.db_port_var.set(str(cfg.get("port", "3306")))
            self.db_user_var.set(cfg.get("user", ""))
            self.db_pass_var.set(cfg.get("password", ""))
            self.db_name_var.set(cfg.get("database", ""))
            self.db_timeout_var.set(str(cfg.get("timeout", "10")))
            self.db_ssl_var.set(cfg.get("ssl", False))
            self.db_ssl_ca_var.set(cfg.get("ssl_ca", ""))
            self._toggle_db_fields()
            self._toggle_ssl_fields()
            self.db_status_var.set("Konfiguration geladen – bitte Verbindung testen.")
            messagebox.showinfo("Geladen", "Datenbankeinstellungen erfolgreich geladen.")
        except Exception as exc:
            messagebox.showerror("Fehler", f"Laden fehlgeschlagen:\n{exc}")

    def _save_to_db(self, license_data: LicenseData, signature: str) -> bool:
        """Versucht, die Lizenz in der DB zu speichern. Gibt True bei Erfolg zurück."""
        if not self.db_enabled_var.get():
            return False
        try:
            self.db.insert_license(license_data, signature)
            return True
        except Exception as exc:
            messagebox.showwarning(
                "Datenbankwarnung",
                f"Lizenz wurde als Datei gespeichert, aber der DB-Eintrag schlug fehl:\n\n{exc}"
            )
            return False

    # -----------------------------------------------------------------------
    # Lizenz-Aktionen
    # -----------------------------------------------------------------------

    def log(self, message: str):
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, message + "\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def generate_secret(self):
        self.secret_var.set(secrets.token_urlsafe(32))
        self.log("Neues Secret erzeugt.")

    def generate_key(self):
        self.key_var.set(create_license_key())
        self.log("Neuer Lizenzschlüssel erzeugt.")

    def clear_form(self):
        self.key_var.set(create_license_key())
        self.customer_var.set("")
        self.product_var.set("")
        self.seats_var.set("1")
        self.issued_at_var.set(datetime.now().strftime(DATE_FORMAT))
        self.expires_at_var.set("")
        self.notes_text.delete("1.0", tk.END)
        self.log("Formular geleert.")

    def _collect_license_data(self) -> LicenseData:
        key = self.key_var.get().strip().upper()
        customer = self.customer_var.get().strip()
        product = self.product_var.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not key:
            raise ValueError("Lizenzschlüssel darf nicht leer sein.")
        if not customer:
            raise ValueError("Kunde darf nicht leer sein.")
        if not product:
            raise ValueError("Produkt darf nicht leer sein.")

        try:
            seats = int(self.seats_var.get().strip())
            if seats < 1:
                raise ValueError
        except ValueError:
            raise ValueError("Sitze muss eine ganze Zahl >= 1 sein.")

        try:
            issued_at = iso_date_or_empty(self.issued_at_var.get())
            expires_at = iso_date_or_empty(self.expires_at_var.get())
        except ValueError:
            raise ValueError(f"Datum muss im Format {DATE_FORMAT} sein.")

        if not issued_at:
            raise ValueError("Ausstellungsdatum darf nicht leer sein.")

        if expires_at and issued_at > expires_at:
            raise ValueError("Ablaufdatum muss nach dem Ausstellungsdatum liegen.")

        return LicenseData(
            version=LICENSE_VERSION,
            key=key,
            customer=customer,
            product=product,
            seats=seats,
            issued_at=issued_at,
            expires_at=expires_at,
            notes=notes,
        )

    def _log_license_summary(self, ld: LicenseData):
        """Schreibt eine lesbare Zusammenfassung der Lizenz ins Ausgabefeld."""
        sep = "─" * 52
        self.log(sep)
        self.log("  LIZENZ-ZUSAMMENFASSUNG")
        self.log(sep)
        self.log(f"  Ausgestellt für : {ld.customer}")
        self.log(f"  Produkt         : {ld.product}")
        self.log(f"  Lizenzschlüssel : {ld.key}")
        self.log(f"  Sitze           : {ld.seats}")
        self.log(f"  Ausgestellt am  : {ld.issued_at}")

        if ld.expires_at:
            try:
                d0 = datetime.strptime(ld.issued_at, DATE_FORMAT).date()
                d1 = datetime.strptime(ld.expires_at, DATE_FORMAT).date()
                delta = d1 - d0
                years, rem = divmod(delta.days, 365)
                months = rem // 30
                if years and months:
                    dauer = f"{years} Jahr(e) und {months} Monat(e)"
                elif years:
                    dauer = f"{years} Jahr(e)"
                elif months:
                    dauer = f"{months} Monat(e)"
                else:
                    dauer = f"{delta.days} Tag(e)"
                self.log(f"  Läuft ab am     : {ld.expires_at}")
                self.log(f"  Gültigkeitsdauer: {dauer}")
            except ValueError:
                self.log(f"  Läuft ab am     : {ld.expires_at}")
        else:
            self.log(f"  Läuft ab am     : –")
            self.log(f"  Gültigkeitsdauer: Unbegrenzt")

        self.log(sep)
        self.log("")

    def save_license(self):
        secret = self.secret_var.get().strip()
        if not secret:
            messagebox.showerror("Fehler", "Bitte zuerst ein Secret eingeben oder erzeugen.")
            return

        try:
            license_data = self._collect_license_data()
        except ValueError as exc:
            messagebox.showerror("Eingabefehler", str(exc))
            return

        payload = license_data.canonical_payload()
        signature = b64_signature(payload, secret)
        full_license = {"license": json.loads(payload), "signature": signature, "algorithm": "HMAC-SHA256"}

        target = filedialog.asksaveasfilename(
            title="Lizenz speichern",
            defaultextension=".license.json",
            filetypes=[("Lizenzdatei", "*.license.json"), ("JSON", "*.json"), ("Alle Dateien", "*.*")],
            initialfile=f"{license_data.customer}_{license_data.product}.license.json".replace(" ", "_"),
        )
        if not target:
            return

        with open(target, "w", encoding="utf-8") as f:
            json.dump(full_license, f, ensure_ascii=False, indent=2)

        self.log(f"Gespeichert: {target}")
        self.log(f"Signatur:    {signature}")
        self.log("")
        self._log_license_summary(license_data)

        # DB-Speicherung
        if self.db_enabled_var.get():
            db_ok = self._save_to_db(license_data, signature)
            if db_ok:
                self.log("✔ Lizenz in Datenbank eingetragen.")
                messagebox.showinfo("Erfolg", "Lizenz wurde erfolgreich erstellt, gespeichert und in der Datenbank eingetragen.")
            else:
                messagebox.showinfo("Gespeichert", "Lizenz wurde als Datei gespeichert (DB-Eintrag fehlgeschlagen – siehe Meldung).")
        else:
            messagebox.showinfo("Erfolg", "Lizenz wurde erfolgreich erstellt und gespeichert.")

    def verify_license_file(self):
        secret = self.secret_var.get().strip()
        if not secret:
            messagebox.showerror("Fehler", "Zum Prüfen wird das Secret benötigt.")
            return

        source = filedialog.askopenfilename(
            title="Lizenzdatei auswählen",
            filetypes=[("Lizenzdatei", "*.license.json"), ("JSON", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not source:
            return

        try:
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Fehler", f"Datei konnte nicht gelesen werden:\n{exc}")
            return

        if "license" not in data or "signature" not in data:
            messagebox.showerror("Fehler", "Ungültige Lizenzdatei (license/signature fehlt).")
            return

        payload = json.dumps(data["license"], ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        expected = b64_signature(payload, secret)
        is_valid = hmac.compare_digest(expected, data["signature"])

        expiry_text = data["license"].get("expires_at", "")
        if expiry_text:
            try:
                expired = datetime.strptime(expiry_text, DATE_FORMAT).date() < datetime.now().date()
            except ValueError:
                expired = False
        else:
            expired = False

        self.log(f"Prüfung: {source}")
        self.log(f"Signatur gültig: {'JA' if is_valid else 'NEIN'}")
        self.log(f"Abgelaufen: {'JA' if expired else 'NEIN'}")

        if is_valid:
            if expired:
                messagebox.showwarning("Lizenzprüfung", "Signatur ist gültig, aber Lizenz ist abgelaufen.")
            else:
                messagebox.showinfo("Lizenzprüfung", "Lizenz ist gültig.")
        else:
            messagebox.showerror("Lizenzprüfung", "Signatur ist ungültig.")


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")
    app = LicenseManagerApp(root)
    app.log("App gestartet. Secret erzeugen und Lizenzdaten eintragen.")
    if not MYSQL_AVAILABLE:
        app.log("⚠ mysql-connector-python nicht gefunden – DB-Funktion inaktiv.")
        app.log("  Installation: pip install mysql-connector-python")
    root.mainloop()


if __name__ == "__main__":
    main()
