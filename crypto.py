"""
crypto.py - Cryptographic operations for the Password Manager.
Uses PBKDF2HMAC for key derivation and Fernet (AES-128-CBC + HMAC-SHA256) for encryption.
"""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken


SALT_SIZE = 32          # bytes
ITERATIONS = 480_000    # OWASP 2023 recommendation for PBKDF2-SHA256


def generate_salt() -> bytes:
    """Return a cryptographically secure random salt."""
    return os.urandom(SALT_SIZE)


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 32-byte key from *password* and *salt* using PBKDF2-HMAC-SHA256.
    Returns a URL-safe base64-encoded key suitable for Fernet.
    """
    password_bytes = password.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    raw_key = kdf.derive(password_bytes)
    # Securely wipe password bytes from memory
    password_ba = bytearray(password_bytes)
    for i in range(len(password_ba)):
        password_ba[i] = 0
    return base64.urlsafe_b64encode(raw_key)


def hash_master_password(password: str, salt: bytes) -> str:
    """
    Return a hex-encoded SHA-256 hash of the derived key, used to verify
    the master password on subsequent logins without storing the password itself.
    """
    key = derive_key(password, salt)
    digest = hashlib.sha256(key).hexdigest()
    # Wipe key bytes
    key_ba = bytearray(key)
    for i in range(len(key_ba)):
        key_ba[i] = 0
    return digest


def encrypt_data(data: bytes, key: bytes) -> bytes:
    """Encrypt *data* with the Fernet *key*. Returns ciphertext bytes."""
    f = Fernet(key)
    return f.encrypt(data)


def decrypt_data(token: bytes, key: bytes) -> bytes:
    """
    Decrypt Fernet *token* with *key*.
    Raises InvalidToken if decryption fails (wrong key or tampered data).
    """
    f = Fernet(key)
    return f.decrypt(token)


def wipe_bytearray(ba: bytearray) -> None:
    """Zero-fill a bytearray in place to remove sensitive data from memory."""
    for i in range(len(ba)):
        ba[i] = 0
