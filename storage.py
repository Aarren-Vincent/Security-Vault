"""
storage.py - Encrypted JSON vault storage for the Password Manager.

Vault file layout (binary):
  [32 bytes salt][N bytes Fernet ciphertext]

The JSON payload structure:
{
  "version": 1,
  "password_hash": "<hex>",
  "entries": [
    {
      "id": "<uuid>",
      "title": "...",
      "username": "...",
      "password": "...",
      "url": "...",
      "notes": "...",
      "created": "<iso8601>",
      "modified": "<iso8601>"
    },
    ...
  ]
}
"""

import json
import os
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.fernet import InvalidToken

import crypto


VAULT_VERSION = 1
SALT_SIZE = crypto.SALT_SIZE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _set_restrictive_permissions(path: Path) -> None:
    """On Windows this is best-effort; on POSIX set 600."""
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Vault class
# ---------------------------------------------------------------------------

class VaultError(Exception):
    """Raised for vault-related errors (wrong password, corrupted file, etc.)."""


class Vault:
    """
    Represents a decrypted in-memory vault.

    Usage:
        vault = Vault.create(path, master_password)   # new vault
        vault = Vault.open(path, master_password)     # existing vault
        vault.add_entry(...)
        vault.save()
    """

    def __init__(self, path: Path, key: bytes, data: dict):
        self._path = path
        self._key = bytearray(key)   # mutable so we can wipe it
        self._data = data

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, path: Path, master_password: str) -> "Vault":
        """Create a brand-new encrypted vault at *path*."""
        salt = crypto.generate_salt()
        key = crypto.derive_key(master_password, salt)
        password_hash = crypto.hash_master_password(master_password, salt)

        data = {
            "version": VAULT_VERSION,
            "password_hash": password_hash,
            "entries": [],
        }

        vault = cls(path, key, data)
        vault._salt = salt
        vault.save()
        return vault

    @classmethod
    def open(cls, path: Path, master_password: str) -> "Vault":
        """Open and decrypt an existing vault. Raises VaultError on failure."""
        if not path.exists():
            raise VaultError(f"Vault file not found: {path}")

        raw = path.read_bytes()
        if len(raw) <= SALT_SIZE:
            raise VaultError("Vault file is too small or corrupted.")

        salt = raw[:SALT_SIZE]
        ciphertext = raw[SALT_SIZE:]

        key = crypto.derive_key(master_password, salt)

        try:
            plaintext = crypto.decrypt_data(ciphertext, key)
        except InvalidToken:
            raise VaultError("Incorrect master password or corrupted vault.")

        data = json.loads(plaintext.decode("utf-8"))

        # Verify stored password hash
        expected_hash = crypto.hash_master_password(master_password, salt)
        if data.get("password_hash") != expected_hash:
            raise VaultError("Master password hash mismatch.")

        vault = cls(path, key, data)
        vault._salt = salt
        return vault

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Encrypt and write the vault to disk."""
        plaintext = json.dumps(self._data, ensure_ascii=False).encode("utf-8")
        ciphertext = crypto.encrypt_data(plaintext, bytes(self._key))
        payload = self._salt + ciphertext

        # Write atomically via temp file
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_bytes(payload)
        _set_restrictive_permissions(tmp_path)
        tmp_path.replace(self._path)
        _set_restrictive_permissions(self._path)

    # ------------------------------------------------------------------
    # Entry CRUD
    # ------------------------------------------------------------------

    def get_entries(self) -> list:
        return list(self._data["entries"])

    def search_entries(self, query: str) -> list:
        q = query.lower()
        return [
            e for e in self._data["entries"]
            if q in e.get("title", "").lower()
            or q in e.get("username", "").lower()
            or q in e.get("url", "").lower()
            or q in e.get("notes", "").lower()
        ]

    def add_entry(
        self,
        title: str,
        username: str,
        password: str,
        url: str = "",
        notes: str = "",
    ) -> dict:
        entry = {
            "id": str(uuid.uuid4()),
            "title": title,
            "username": username,
            "password": password,
            "url": url,
            "notes": notes,
            "created": _now_iso(),
            "modified": _now_iso(),
        }
        self._data["entries"].append(entry)
        return entry

    def update_entry(self, entry_id: str, **fields) -> bool:
        for entry in self._data["entries"]:
            if entry["id"] == entry_id:
                for k, v in fields.items():
                    if k in entry:
                        entry[k] = v
                entry["modified"] = _now_iso()
                return True
        return False

    def delete_entry(self, entry_id: str) -> bool:
        before = len(self._data["entries"])
        self._data["entries"] = [
            e for e in self._data["entries"] if e["id"] != entry_id
        ]
        return len(self._data["entries"]) < before

    # ------------------------------------------------------------------
    # Security helpers
    # ------------------------------------------------------------------

    def lock(self) -> None:
        """Wipe the in-memory key so the vault is locked without closing."""
        crypto.wipe_bytearray(self._key)

    def is_locked(self) -> bool:
        return all(b == 0 for b in self._key)

    def change_master_password(self, new_password: str) -> None:
        """Re-derive a new key and re-save the vault under a new password."""
        new_salt = crypto.generate_salt()
        new_key = crypto.derive_key(new_password, new_salt)
        new_hash = crypto.hash_master_password(new_password, new_salt)

        crypto.wipe_bytearray(self._key)
        self._key = bytearray(new_key)
        self._salt = new_salt
        self._data["password_hash"] = new_hash
        self.save()


# ---------------------------------------------------------------------------
# Convenience: check if a vault file exists
# ---------------------------------------------------------------------------

def vault_exists(path: Path) -> bool:
    return path.exists() and path.stat().st_size > SALT_SIZE
