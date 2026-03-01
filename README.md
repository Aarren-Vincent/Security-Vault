# 🔐 SecureVault — Python Password Manager

A local, encrypted password manager built with **Python**, **Tkinter**, and the **`cryptography`** library.

---

## Features

| Feature | Details |
|---|---|
| **Master password login** | PBKDF2-HMAC-SHA256 (480 000 iterations) key derivation |
| **Encrypted vault** | Fernet (AES-128-CBC + HMAC-SHA256) with a unique random salt |
| **Password generation** | CSPRNG (`secrets` module), length 8–64, configurable charset |
| **Strength meter** | Shannon entropy estimate with colour-coded label |
| **Search / filter** | Live fuzzy search across title, username, URL, and notes |
| **Clipboard** | One-click copy with configurable auto-clear (default 30 s) |
| **Auto-lock** | Vault locks after 5 min of inactivity |
| **Memory hardening** | Sensitive strings stored in `bytearray` and wiped with zeros on lock |
| **File permissions** | Vault written with mode 600 (POSIX) and via atomic rename |
| **Change master password** | Re-derives key + new salt, re-encrypts in place |

---

## File Layout

```
password_manager/
├── main.py               # Entry point — creates Tk window, routes login ↔ main
├── crypto.py             # Key derivation, encrypt/decrypt, bytearray wipe
├── storage.py            # Vault file I/O (binary: salt + Fernet ciphertext)
├── generator.py          # Secure password generation & entropy estimation
├── clipboard.py          # Clipboard copy + auto-clear timer
├── ui_login.py           # Login / create-vault screen
├── ui_main.py            # Main vault window (list + detail + toolbar)
├── ui_entry_dialog.py    # Add/Edit entry dialog + Password Generator dialog
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install cryptography
```

*(Tkinter ships with the standard Python installer on Windows.)*

### 2. Run

```bash
python main.py
```

### First run
You will be prompted to create a **master password** (minimum 10 characters). The vault file is stored at:

```
%USERPROFILE%\.pm_vault\vault.dat   # Windows
~/.pm_vault/vault.dat               # Linux / macOS
```

---

## Vault File Format

```
[32 bytes random salt][variable-length Fernet ciphertext]
```

The Fernet ciphertext decrypts to a UTF-8 JSON document:

```json
{
  "version": 1,
  "password_hash": "<sha256-hex of derived key>",
  "entries": [
    {
      "id": "<uuid4>",
      "title": "GitHub",
      "username": "alice@example.com",
      "password": "super-secret",
      "url": "https://github.com",
      "notes": "",
      "created": "2025-01-01T12:00:00+00:00",
      "modified": "2025-01-02T08:30:00+00:00"
    }
  ]
}
```

---

## Security Notes

- **No plaintext storage** — the vault is always encrypted at rest.
- **PBKDF2 with 480 000 iterations** slows brute-force attacks significantly.
- **Fernet authenticated encryption** prevents silent data tampering.
- **Master password is never stored** — only a hash of the *derived key* is saved for verification.
- **Memory hygiene** — encryption keys are kept in `bytearray` and zeroed when the vault is locked.
- **Clipboard auto-clear** — copied passwords are wiped from the clipboard after 30 seconds by default.
- **Auto-lock** — idle timeout (5 min) locks the vault and wipes the in-memory key.

---

## Customisation

| Constant | File | Default | Purpose |
|---|---|---|---|
| `AUTO_LOCK_MS` | `ui_main.py` | `300000` (5 min) | Idle auto-lock timeout |
| `CLIPBOARD_CLEAR_SECS` | `ui_main.py` | `30` | Clipboard wipe delay |
| `ITERATIONS` | `crypto.py` | `480000` | PBKDF2 iteration count |
| `VAULT_PATH` | `ui_login.py` | `~/.pm_vault/vault.dat` | Vault file location |
