import hashlib
import wmi
import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

class SecurityManager:
    """Handles HWID extraction and ECDSA signing/verification."""

    @staticmethod
    def get_hwid() -> str:
        """Generates a unique HWID based on CPU and HDD serials."""
        try:
            c = wmi.WMI()
            cpu_id = ""
            for cpu in c.Win32_Processor():
                cpu_id = cpu.ProcessorId.strip()
                break
            
            disk_id = ""
            for disk in c.Win32_DiskDrive():
                disk_id = disk.SerialNumber.strip()
                break
            
            raw_id = f"{cpu_id}-{disk_id}"
            digest = hashlib.sha256(raw_id.encode()).hexdigest().upper()
            return str(digest[:24])
        except Exception:
            # Fallback if WMI fails
            import platform
            node = platform.node()
            digest = hashlib.sha256(node.encode()).hexdigest().upper()
            return str(digest[:24])

    @staticmethod
    def generate_key_pair():
        """Generates a new ECDSA key pair."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        
        # Serialize private key (PEM)
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key (PEM)
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return priv_pem.decode(), pub_pem.decode()

    @staticmethod
    def sign_data(data: str, private_key_pem: str) -> str:
        """Signs data using a private key."""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )
        signature = private_key.sign(
            data.encode(),
            ec.ECDSA(hashes.SHA256())
        )
        return base64.urlsafe_b64encode(signature).decode().rstrip("=")

    @staticmethod
    def verify_signature(data: str, signature: str, public_key_pem: str) -> bool:
        """Verifies a signature using a public key."""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode()
            )
            sig_bytes = base64.urlsafe_b64decode(signature + "===")
            public_key.verify(
                sig_bytes,
                data.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except Exception:
            return False

if __name__ == "__main__":
    # Test
    hwid = SecurityManager.get_hwid()
    print(f"HWID: {hwid}")
    priv, pub = SecurityManager.generate_key_pair()
    data = "test data"
    sig = SecurityManager.sign_data(data, priv)
    print(f"Signature: {sig}")
    valid = SecurityManager.verify_signature(data, sig, pub)
    print(f"Valid: {valid}")
