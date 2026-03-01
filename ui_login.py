"""
ui_login.py - Login and first-run setup dialogs.
"""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path

import storage
import generator


VAULT_PATH = Path.home() / ".pm_vault" / "vault.dat"


class LoginScreen(tk.Frame):
    """
    Shown at startup. Handles both:
      - First-run: create a new vault with a master password
      - Subsequent runs: unlock an existing vault
    """

    def __init__(self, master: tk.Tk, on_success):
        super().__init__(master, bg="#1a1a2e")
        self._master = master
        self._on_success = on_success
        self._is_new_vault = not storage.vault_exists(VAULT_PATH)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # ---- Header ----
        header = tk.Frame(self, bg="#16213e", pady=40)
        header.pack(fill=tk.X)

        tk.Label(
            header, text="🔐",
            font=("Segoe UI", 56),
            bg="#16213e", fg="#e94560",
        ).pack()

        tk.Label(
            header, text="SecureVault",
            font=("Segoe UI", 28, "bold"),
            bg="#16213e", fg="#ffffff",
        ).pack()

        subtitle = "Create your vault" if self._is_new_vault else "Unlock your vault"
        tk.Label(
            header, text=subtitle,
            font=("Segoe UI", 14),
            bg="#16213e", fg="#a0a0b0",
        ).pack(pady=(6, 0))

        # ---- Card ----
        card = tk.Frame(self, bg="#16213e", padx=60, pady=44)
        card.place(relx=0.5, rely=0.55, anchor="center", width=520)

        self._pw_var  = tk.StringVar()
        self._pw2_var = tk.StringVar()

        self._add_field(card, "Master Password", self._pw_var, show="•", row=0)

        if self._is_new_vault:
            self._add_field(card, "Confirm Password", self._pw2_var, show="•", row=1)

            # Strength bar
            strength_frame = tk.Frame(card, bg="#16213e")
            strength_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 18))

            self._strength_bar = tk.Canvas(
                strength_frame, height=8, bg="#2a2a40", highlightthickness=0
            )
            self._strength_bar.pack(fill=tk.X)

            self._strength_var = tk.StringVar(value="")
            self._strength_lbl = tk.Label(
                strength_frame, textvariable=self._strength_var,
                bg="#16213e", fg="#a0a0b0", font=("Segoe UI", 10),
            )
            self._strength_lbl.pack(anchor="e", pady=(3, 0))
            self._pw_var.trace_add("write", self._update_strength)

        # ---- Submit button ----
        btn_text = "Create Vault" if self._is_new_vault else "Unlock"
        tk.Button(
            card, text=btn_text,
            command=self._submit,
            bg="#e94560", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=24, pady=12,
            activebackground="#c73652", activeforeground="white",
        ).grid(row=10, column=0, columnspan=2, pady=(8, 0))

        self._master.bind("<Return>", lambda e: self._submit())

    def _add_field(self, parent, label, var, show="", row=0):
        tk.Label(
            parent, text=label,
            bg="#16213e", fg="#a0a0b0",
            font=("Segoe UI", 12), anchor="w",
        ).grid(row=row, column=0, sticky="ew", pady=(0, 5))

        entry = tk.Entry(
            parent, textvariable=var, show=show,
            bg="#1a1a2e", fg="white", insertbackground="white",
            font=("Segoe UI", 13),
            relief=tk.FLAT,
            highlightthickness=2,
            highlightcolor="#e94560",
            highlightbackground="#333",
        )
        entry.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=(0, 18), ipady=8)
        parent.columnconfigure(1, weight=1)

        if row == 0:
            entry.focus_set()
        return entry

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _update_strength(self, *_):
        pw = self._pw_var.get()
        entropy = generator.estimate_entropy(pw)
        label, color = generator.strength_label(entropy)
        self._strength_var.set(f"Strength: {label}  ({entropy:.0f} bits)")
        self._strength_lbl.config(fg=color)

        w = self._strength_bar.winfo_width() or 400
        pct = min(entropy / 128, 1.0)
        self._strength_bar.delete("all")
        self._strength_bar.create_rectangle(0, 0, int(w * pct), 8, fill=color, outline="")

    def _submit(self):
        pw = self._pw_var.get()
        if not pw:
            messagebox.showerror("Error", "Please enter a master password.", parent=self._master)
            return

        VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)

        if self._is_new_vault:
            pw2 = self._pw2_var.get()
            if pw != pw2:
                messagebox.showerror("Error", "Passwords do not match.", parent=self._master)
                return
            if len(pw) < 10:
                messagebox.showerror(
                    "Weak Password",
                    "Master password must be at least 10 characters.",
                    parent=self._master,
                )
                return
            try:
                vault = storage.Vault.create(VAULT_PATH, pw)
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=self._master)
                return
        else:
            try:
                vault = storage.Vault.open(VAULT_PATH, pw)
            except storage.VaultError as exc:
                messagebox.showerror("Incorrect Password", str(exc), parent=self._master)
                return
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=self._master)
                return

        # Wipe password from memory
        pw_ba = bytearray(pw.encode())
        for i in range(len(pw_ba)):
            pw_ba[i] = 0

        self.destroy()
        self._on_success(vault)
