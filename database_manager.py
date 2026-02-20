import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional, List

# Optionaler MySQL-Import – kein Pflichtpaket
try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS licenses (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    license_key   VARCHAR(64)   NOT NULL UNIQUE,
    customer      VARCHAR(255)  NOT NULL,
    product       VARCHAR(255)  NOT NULL,
    seats         INT           NOT NULL DEFAULT 1,
    hwid          VARCHAR(64)   DEFAULT NULL,
    issued_at     DATE          NOT NULL,
    expires_at    DATE          NULL,
    notes         TEXT,
    algorithm     VARCHAR(32)   NOT NULL,
    signature     VARCHAR(512)  NOT NULL,
    is_revoked    BOOLEAN       DEFAULT FALSE,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

@dataclass
class LicenseData:
    version: int
    key: str
    customer: str
    product: str
    seats: int
    hwid: str 
    issued_at: str
    expires_at: str
    notes: str

    def canonical_payload(self) -> str:
        payload = asdict(self) # type: ignore
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

class DatabaseManager:
    """Verwaltet die MySQL/MariaDB-Verbindung und das Speichern von Lizenzen."""

    def __init__(self):
        self._cfg: Optional[Dict[str, Any]] = None

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
        cfg: Dict[str, Any] = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "connect_timeout": connect_timeout,
        }
        if use_ssl:
            ssl_dict: Dict[str, Any] = {"verify_cert": True}
            if ssl_ca:
                ssl_dict["ca"] = ssl_ca
            cfg["ssl"] = ssl_dict
        self._cfg = cfg

    def _connect(self):
        if not MYSQL_AVAILABLE:
            raise RuntimeError("mysql-connector-python ist nicht installiert.")
        if not self._cfg:
            raise RuntimeError("Keine Datenbankverbindung konfiguriert.")
        return mysql.connector.connect(**self._cfg)

    def test_connection(self) -> str:
        conn = self._connect()
        version = "Unknown"
        try:
            cur = conn.cursor()
            cur.execute(CREATE_TABLE_SQL)
            conn.commit()
            
            # Schema Migration: Add missing columns if they don't exist
            self._migrate_schema(cur)
            conn.commit()

            cur.execute("SELECT VERSION()")
            row = cur.fetchone()
            if row:
                version = str(row[0])
            cur.close()
            return version
        finally:
            conn.close()

    def _migrate_schema(self, cursor):
        """Adds missing columns to the licenses table if they are not present."""
        columns_to_add = {
            "customer": "VARCHAR(255) NOT NULL AFTER license_key",
            "product": "VARCHAR(255) NOT NULL AFTER customer",
            "seats": "INT NOT NULL DEFAULT 1 AFTER product",
            "hwid": "VARCHAR(64) DEFAULT NULL AFTER seats",
            "issued_at": "DATE NOT NULL AFTER hwid",
            "expires_at": "DATE DEFAULT NULL AFTER issued_at",
            "notes": "TEXT AFTER expires_at",
            "algorithm": "VARCHAR(32) NOT NULL AFTER notes",
            "signature": "VARCHAR(512) NOT NULL AFTER algorithm",
            "is_revoked": "BOOLEAN DEFAULT FALSE AFTER signature"
        }
        
        cursor.execute("DESCRIBE licenses")
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        for col, definition in columns_to_add.items():
            if col not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE licenses ADD COLUMN {col} {definition}")
                except Exception as e:
                    print(f"Migration error for {col}: {e}")

    def insert_license(self, license_data: LicenseData, signature: str, algorithm: str = "ECDSA-P256"):
        conn = self._connect()
        try:
            cur = conn.cursor()
            sql = """
                INSERT INTO licenses
                    (license_key, customer, product, seats, hwid, issued_at, expires_at, notes, algorithm, signature)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    customer   = VALUES(customer),
                    product    = VALUES(product),
                    seats      = VALUES(seats),
                    hwid       = VALUES(hwid),
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
                license_data.hwid,
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

    def get_all_licenses(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM licenses ORDER BY created_at DESC")
            rows = cur.fetchall()
            cur.close()
            return rows # type: ignore
        finally:
            conn.close()

    def get_license(self, license_key: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM licenses WHERE license_key = %s", (license_key,))
            row = cur.fetchone()
            cur.close()
            return row # type: ignore
        finally:
            conn.close()

    def revoke_license(self, license_key: str, revoked: bool = True):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE licenses SET is_revoked = %s WHERE license_key = %s", (revoked, license_key))
            conn.commit()
            cur.close()
        finally:
            conn.close()
