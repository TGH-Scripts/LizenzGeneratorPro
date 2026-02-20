import tkinter as tk
import customtkinter as ctk
import json
import os
import secrets
import string
import requests
import threading
import subprocess
from datetime import datetime
from tkinter import filedialog, messagebox

from security_manager import SecurityManager
from database_manager import DatabaseManager, LicenseData

# App Config
APP_VERSION = "2.1.0"
GITHUB_REPO = "TGH-Scripts/LizenzGeneratorPro"
DATE_FORMAT = "%Y-%m-%d"

def get_data_dir():
    """Returns a safe directory to store persistent data."""
    base_dir = os.getenv('APPDATA') or os.path.expanduser('~')
    data_dir = os.path.join(base_dir, "TGH-Scripts", "LizenzGeneratorPro")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Lizenz-Generator Professional")
        self.geometry("1100x700")

        # Managers
        self.db = DatabaseManager()
        self.security = SecurityManager()

        # State
        self.priv_key = ""
        self.pub_key = ""
        self.data_dir = get_data_dir()
        self._CONFIG_FILE = os.path.join(self.data_dir, ".db_config.json")
        self._load_generator_keys()
        self._load_db_config()

        # Grid layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Lizenz-Pro", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.gen_btn = ctk.CTkButton(self.sidebar_frame, text="Generator", command=self.show_generator, corner_radius=0, height=40, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.gen_btn.grid(row=1, column=0, sticky="ew")

        self.db_btn = ctk.CTkButton(self.sidebar_frame, text="Datenbank", command=self.show_database, corner_radius=0, height=40, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.db_btn.grid(row=2, column=0, sticky="ew")

        self.settings_btn = ctk.CTkButton(self.sidebar_frame, text="Einstellungen", command=self.show_settings, corner_radius=0, height=40, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.settings_btn.grid(row=3, column=0, sticky="ew")

        self.verify_btn = ctk.CTkButton(self.sidebar_frame, text="Verifizieren", command=self.show_verify, corner_radius=0, height=40, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.verify_btn.grid(row=4, column=0, sticky="ew")

        self.update_btn = ctk.CTkButton(self.sidebar_frame, text="Update suchen", command=self.check_updates_thread, corner_radius=0, height=40, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.update_btn.grid(row=5, column=0, sticky="ew")

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Erscheinungsbild:", anchor="w")
        self.appearance_mode_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"], command=self.change_appearance_mode)
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 20))

        # --- Frames ---
        self.gen_frame = self._build_generator_frame()
        self.db_view_frame = self._build_database_frame()
        self.verify_frame = self._build_verify_frame()
        self.settings_frame = self._build_settings_frame()

        # Init view
        self.show_generator()

        # Startup update check (silent)
        threading.Thread(target=lambda: self._check_for_updates(manual=False), daemon=True).start()

    def _load_generator_keys(self):
        """Loads or generates the ECC keys for the generator."""
        key_file = os.path.join(self.data_dir, "generator_keys.json")
        if os.path.exists(key_file):
            try:
                with open(key_file, "r") as f:
                    data = json.load(f)
                    self.priv_key = data.get("private_key", "")
                    self.pub_key = data.get("public_key", "")
            except Exception:
                pass
        
        if not self.priv_key:
            self.priv_key, self.pub_key = self.security.generate_key_pair()
            try:
                with open(key_file, "w") as f:
                    json.dump({"private_key": self.priv_key, "public_key": self.pub_key}, f)
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Key-Datei nicht speichern:\n{e}")

    def _load_db_config(self):
        """Loads DB configuration from file if it exists."""
        if os.path.exists(self._CONFIG_FILE):
            try:
                with open(self._CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                
                # Update UI entries if they exist yet (they will be built after this in __init__)
                # Actually, __init__ calls frames after _load_generator_keys but before frames are fully populated.
                # Let's just store it and apply in the frame builders.
                self.saved_db_cfg = cfg
                
                # Apply to manager
                self.db.configure(
                    host=cfg.get("host", "localhost"),
                    user=cfg.get("user", "root"),
                    password=cfg.get("password", ""),
                    database=cfg.get("database", "licenses"),
                    port=int(cfg.get("port", 3306))
                )
            except Exception as e:
                print(f"Error loading DB config: {e}")
        else:
            self.saved_db_cfg = {}

    def _apply_saved_db_cfg(self):
        """Applies saved config to the UI entries."""
        if hasattr(self, "saved_db_cfg"):
            self.db_host.delete(0, tk.END)
            self.db_host.insert(0, self.saved_db_cfg.get("host", "localhost"))
            self.db_user.delete(0, tk.END)
            self.db_user.insert(0, self.saved_db_cfg.get("user", "root"))
            self.db_pass.delete(0, tk.END)
            self.db_pass.insert(0, self.saved_db_cfg.get("password", ""))
            self.db_name.delete(0, tk.END)
            self.db_name.insert(0, self.saved_db_cfg.get("database", "licenses"))

    # --- View Switching ---
    def select_frame_by_name(self, name):
        # Set button colors
        self.gen_btn.configure(fg_color=("gray75", "gray25") if name == "gen" else "transparent")
        self.db_btn.configure(fg_color=("gray75", "gray25") if name == "db" else "transparent")
        self.verify_btn.configure(fg_color=("gray75", "gray25") if name == "verify" else "transparent")
        self.settings_btn.configure(fg_color=("gray75", "gray25") if name == "settings" else "transparent")

        # Show selected frame
        if name == "gen":
            self.gen_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        else:
            self.gen_frame.grid_forget()
        
        if name == "db":
            self.db_view_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            self._refresh_db_list()
        else:
            self.db_view_frame.grid_forget()

        if name == "verify":
            self.verify_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        else:
            self.verify_frame.grid_forget()

        if name == "settings":
            self.settings_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        else:
            self.settings_frame.grid_forget()

    def show_generator(self): self.select_frame_by_name("gen")
    def show_database(self): self.select_frame_by_name("db")
    def show_verify(self): self.select_frame_by_name("verify")
    def show_settings(self): self.select_frame_by_name("settings")

    def change_appearance_mode(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    # --- Update Logic ---
    def check_updates_thread(self):
        self.update_btn.configure(text="Suche...", state="disabled")
        threading.Thread(target=lambda: self._check_for_updates(manual=True), daemon=True).start()

    def _check_for_updates(self, manual=True):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").replace("v", "")
                
                if self._is_newer(latest_version, APP_VERSION):
                    assets = data.get("assets", [])
                    download_url = ""
                    for asset in assets:
                        if "setup" in asset.get("name", "").lower() and asset.get("name", "").endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break
                    
                    if download_url:
                        self.after(0, lambda u=download_url, v=latest_version: self._ask_to_update(u, v))
                    else:
                        self.after(0, lambda: messagebox.showinfo("Update", f"Neue Version {latest_version} verfügbar, aber keine Setup-Datei gefunden."))
                elif manual:
                    self.after(0, lambda: messagebox.showinfo("Update", f"Du nutzt bereits die aktuellste Version ({APP_VERSION})."))
            elif manual:
                if response.status_code == 404:
                    self.after(0, lambda: messagebox.showinfo("Update", "Bisher wurden noch keine Updates auf GitHub veröffentlicht."))
                else:
                    self.after(0, lambda: messagebox.showerror("Update", f"Fehler beim Suchen nach Updates: {response.status_code}"))
        except Exception as e:
            if manual:
                self.after(0, lambda ex=e: messagebox.showerror("Update", f"Fehler: {ex}"))
        finally:
            if manual:
                self.after(0, lambda: self.update_btn.configure(text="Update suchen", state="normal"))

    def _is_newer(self, latest, current):
        try:
            l_parts = [int(p) for p in latest.split(".")]
            c_parts = [int(p) for p in current.split(".")]
            return l_parts > c_parts
        except Exception:
            return latest > current

    def _ask_to_update(self, url, version):
        if messagebox.askyesno("Update verfügbar", f"Version {version} ist verfügbar! Möchtest du das Update jetzt herunterladen und installieren?"):
            self._download_and_install(url)

    def _download_and_install(self, url):
        try:
            temp_file = os.path.join(os.environ["TEMP"], "LizenzGeneratorPro_Update.exe")
            response = requests.get(url, stream=True)
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            messagebox.showinfo("Update", "Update heruntergeladen. Der Installer wird nun gestartet und die App beendet.")
            subprocess.Popen([temp_file], shell=True)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Update-Fehler", f"Fehler beim Download: {e}")

    # --- Frame Builders ---
    def _build_generator_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid_columnconfigure(1, weight=1)
        
        # Title
        label = ctk.CTkLabel(frame, text="Lizenz erstellen", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")

        # Inputs
        self.customer_entry = self._add_input(frame, "Kunde:", 1)
        self.product_entry = self._add_input(frame, "Produkt:", 2)
        self.seats_entry = self._add_input(frame, "Sitze:", 3, default="1")
        self.hwid_entry = self._add_input(frame, "Hardware ID (HWID):", 4, tooltip="Optional: Bindet die Lizenz an einen PC")
        
        self.issued_entry = self._add_input(frame, "Ausgestellt am:", 5, default=datetime.now().strftime(DATE_FORMAT))
        self.expires_entry = self._add_input(frame, "Läuft ab am:", 6, tooltip="Optional (YYYY-MM-DD)")

        self.notes_label = ctk.CTkLabel(frame, text="Notizen:")
        self.notes_label.grid(row=7, column=0, padx=20, pady=10, sticky="nw")
        self.notes_text = ctk.CTkTextbox(frame, height=100)
        self.notes_text.grid(row=7, column=1, padx=20, pady=10, sticky="ew")

        # Action Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        btn_frame.grid_columnconfigure((0,1), weight=1)

        self.create_btn = ctk.CTkButton(btn_frame, text="Lizenz Generieren & Speichern", command=self.generate_license, height=40)
        self.create_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.clear_btn = ctk.CTkButton(btn_frame, text="Formular leeren", command=self.clear_form, height=40, fg_color="gray")
        self.clear_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        return frame

    def _add_input(self, frame, label_text, row, default="", tooltip=""):
        lbl = ctk.CTkLabel(frame, text=label_text)
        lbl.grid(row=row, column=0, padx=20, pady=10, sticky="w")
        entry = ctk.CTkEntry(frame, placeholder_text=tooltip)
        entry.insert(0, default)
        entry.grid(row=row, column=1, padx=20, pady=10, sticky="ew")
        return entry

    def _build_database_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        label = ctk.CTkLabel(frame, text="Datenbank-Übersicht", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Scrollable list or Table (simplified here for brevity)
        self.db_list_frame = ctk.CTkScrollableFrame(frame)
        self.db_list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.refresh_btn = ctk.CTkButton(frame, text="Aktualisieren", command=self._refresh_db_list)
        self.refresh_btn.grid(row=2, column=0, padx=20, pady=20)

        return frame

    def _build_verify_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid_columnconfigure(0, weight=1)
        
        label = ctk.CTkLabel(frame, text="Lizenz verifizieren", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        btn_select = ctk.CTkButton(frame, text="Lizenzdatei auswählen", command=self.verify_license_ui)
        btn_select.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.verify_output = ctk.CTkTextbox(frame, height=300)
        self.verify_output.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        frame.grid_rowconfigure(2, weight=1)

        return frame

    def _build_settings_frame(self):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid_columnconfigure(1, weight=1)

        label = ctk.CTkLabel(frame, text="Einstellungen", font=ctk.CTkFont(size=20, weight="bold"))
        label.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")

        # DB Settings
        self.db_host = self._add_input(frame, "DB Host:", 1, default="localhost")
        self.db_user = self._add_input(frame, "DB User:", 2, default="root")
        self.db_pass = self._add_input(frame, "DB Passwort:", 3)
        self.db_name = self._add_input(frame, "DB Name:", 4, default="licenses")
        
        self._apply_saved_db_cfg()

        self.save_settings_btn = ctk.CTkButton(frame, text="DB Verbindung speichern & testen", command=self.save_db_settings)
        self.save_settings_btn.grid(row=5, column=0, columnspan=2, padx=20, pady=(20, 10))

        self.show_pubkey_btn = ctk.CTkButton(frame, text="Öffentlichen Schlüssel (Public Key) anzeigen", 
                                             command=self.show_public_key, fg_color="transparent", border_width=1)
        self.show_pubkey_btn.grid(row=6, column=0, columnspan=2, padx=20, pady=10)

        return frame

    # --- Logic ---
    def generate_license(self):
        cust = self.customer_entry.get().strip()
        prod = self.product_entry.get().strip()
        if not cust or not prod:
            messagebox.showerror("Fehler", "Kunde und Produkt werden benötigt.")
            return

        key = "-".join([secrets.token_hex(2).upper() for _ in range(4)])
        ld = LicenseData(
            version=1,
            key=key,
            customer=cust,
            product=prod,
            seats=int(self.seats_entry.get() or 1),
            hwid=self.hwid_entry.get().strip(),
            issued_at=self.issued_entry.get().strip(),
            expires_at=self.expires_entry.get().strip(),
            notes=self.notes_text.get("1.0", tk.END).strip()
        )

        payload = ld.canonical_payload()
        sig = SecurityManager.sign_data(payload, self.priv_key)
        
        full_license = {
            "license": json.loads(payload),
            "signature": sig,
            "public_key": self.pub_key, # Include public key for verification
            "algorithm": "ECDSA-P256"
        }

        path = filedialog.asksaveasfilename(defaultextension=".license.json", initialfile=f"{cust}_{prod}.license.json")
        if path:
            with open(path, "w") as f:
                json.dump(full_license, f, indent=4)
            messagebox.showinfo("Erfolg", f"Lizenz gespeichert!\nSchlüssel: {key}")
            
            # Try to save to DB
            try:
                self.db.insert_license(ld, sig)
            except Exception as e:
                messagebox.showwarning("Datenbankwarnung", f"Lizenz wurde als Datei gespeichert, aber der DB-Eintrag schlug fehl:\n\n{e}")

    def verify_license_ui(self):
        path = filedialog.askopenfilename(filetypes=[("Lizenzdateien", "*.license.json")])
        if not path:
            return

        self.verify_output.delete("1.0", tk.END)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 1. Signature Check
            lic_data = data.get("license", {})
            sig = data.get("signature", "")
            pub_key = data.get("public_key", self.pub_key) # Fallback to own pub key if not in file
            
            # Reconstruct payload for verification
            payload = json.dumps(lic_data, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
            
            is_valid = self.security.verify_signature(payload, sig, pub_key)
            
            res_text = "=== VERIFIZIERUNG ===\n\n"
            res_text += f"Datei: {os.path.basename(path)}\n"
            res_text += f"Status: {'✅ GÜLTIG' if is_valid else '❌ UNGÜLTIG'}\n\n"
            
            if is_valid:
                res_text += f"Kunde:    {lic_data.get('customer')}\n"
                res_text += f"Produkt:  {lic_data.get('product')}\n"
                res_text += f"Sitze:    {lic_data.get('seats')}\n"
                res_text += f"HWID:     {lic_data.get('hwid') or '-'}\n"
                
                # Expiry Check
                expires_at = lic_data.get("expires_at")
                if expires_at:
                    try:
                        exp_date = datetime.strptime(expires_at, DATE_FORMAT).date()
                        if exp_date < datetime.now().date():
                            res_text += f"Ablauf:   {expires_at} (⚠️ ABGELAUFEN)\n"
                        else:
                            res_text += f"Ablauf:   {expires_at} (Aktiv)\n"
                    except:
                        res_text += f"Ablauf:   {expires_at} (Ungültiges Format)\n"
                else:
                    res_text += "Ablauf:   Kein Ablaufdatum\n"

                # HWID check of current PC
                current_hwid = self.security.get_hwid()
                lic_hwid = lic_data.get("hwid")
                if lic_hwid:
                    if lic_hwid == current_hwid:
                        res_text += "HWID-Check: ✅ Dieser PC ist berechtigt.\n"
                    else:
                        res_text += f"HWID-Check: ❌ PC mismatch (Aktuell: {current_hwid}, Lizenz: {lic_hwid})\n"

            self.verify_output.insert("1.0", res_text)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Verifizieren:\n{e}")

    def show_public_key(self):
        msg = f"Dein öffentlicher Schlüssel (Public Key):\n\n{self.pub_key}\n\n"
        msg += "Diesen Schlüssel benötigst du in deiner Software, um die Signaturen zu prüfen."
        messagebox.showinfo("Public Key", msg)

    def clear_form(self):
        self.customer_entry.delete(0, tk.END)
        self.product_entry.delete(0, tk.END)
        self.hwid_entry.delete(0, tk.END)
        self.notes_text.delete("1.0", tk.END)

    def save_db_settings(self):
        cfg = {
            "host": self.db_host.get(),
            "user": self.db_user.get(),
            "password": self.db_pass.get(),
            "database": self.db_name.get(),
            "port": 3306
        }
        
        try:
            self.db.configure(**cfg)
            # Test connection
            version = self.db.test_connection()
            
            # Save to file
            with open(self._CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
                
            messagebox.showinfo("Erfolg", f"Verbindung erfolgreich!\nServer: {version}\nEinstellungen wurden gespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Verbindung fehlgeschlagen:\n{e}")

    def _refresh_db_list(self):
        for widget in self.db_list_frame.winfo_children():
            widget.destroy()
        
        try:
            licenses = self.db.get_all_licenses()
            for i, l in enumerate(licenses):
                row = ctk.CTkFrame(self.db_list_frame)
                row.pack(fill="x", padx=5, pady=5)
                
                exp_status = ""
                if l['expires_at']:
                    try:
                        if datetime.strptime(str(l['expires_at']), "%Y-%m-%d").date() < datetime.now().date():
                            exp_status = " (⌛ ABGELAUFEN)"
                    except: pass

                info = f"{l['customer']} | {l['product']} | {l['license_key']}\n"
                info += f"Sitze: {l['seats']} | HWID: {l['hwid'] or '-'} | Ablauf: {l['expires_at'] or 'Kein'}{exp_status}"
                
                ctk.CTkLabel(row, text=info, anchor="w", justify="left").pack(side="left", padx=10, pady=5, fill="x", expand=True)
                
                status_color = "red" if l['is_revoked'] else "green"
                status_text = "Gesperrt" if l['is_revoked'] else "Aktiv"
                
                ctk.CTkLabel(row, text=status_text, text_color=status_color).pack(side="left", padx=10)
                
                btn_text = "Entsperren" if l['is_revoked'] else "Sperren"
                btn_color = "gray" if l['is_revoked'] else "#D32F2F"
                
                ctk.CTkButton(row, text=btn_text, width=80, height=24, fg_color=btn_color,
                             command=lambda k=l['license_key'], r=not l['is_revoked']: self._toggle_revoke(k, r)).pack(side="right", padx=10)
        except Exception as e:
            ctk.CTkLabel(self.db_list_frame, text=f"Fehler beim Laden: {e}").pack()

    def _toggle_revoke(self, key, state):
        try:
            self.db.revoke_license(key, state)
            self._refresh_db_list()
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

if __name__ == "__main__":
    app = App()
    app.mainloop()
