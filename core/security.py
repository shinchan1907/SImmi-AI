import os
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional

class SecurityManager:
    def __init__(self, key_path: str = "config/.key"):
        self.key_path = Path(key_path)
        self.key = self._load_or_generate_key()
        self.cipher_suite = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes()
        
        key = Fernet.generate_key()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(key)
        return key

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.cipher_suite.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        if not encrypted_data:
            return ""
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception:
            # If decryption fails, it might be plain text (for migration or invalid keys)
            return encrypted_data

# Singleton instance
security_manager = SecurityManager()

def encrypt_key(key: str) -> str:
    return security_manager.encrypt(key)

def decrypt_key(key: str) -> str:
    return security_manager.decrypt(key)
