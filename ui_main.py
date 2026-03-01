"""
ui_main.py - Main vault window shown after successful login.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import clipboard
import storage
from ui_entry_dialog import EntryDialog


BG     = "#1a1a2e"
BG2    = "#16213e"
BG3    = "#0f3460"
ACCENT = "#e94560"
FG     = "#ffffff"
FG2    = "#a0a0b0"
FG3    = "#00ffaa"

# ── Font scale ──────────────────────────────────────────────────────────────
FONT       = ("Segoe UI", 12)
FONT_BOLD  = ("Segoe UI", 12, "bold")
FONT_MONO  = ("Consolas", 12)
FONT_SM    = ("Segoe UI", 10)
FONT_LG    = ("Segoe UI", 14, "bold")
# ────────────────────────────────────────────────────────────────────────────

AUTO_LOCK_MS        = 5 * 60 * 1000   # 5 minutes idle → auto-lock
CLIPBOARD_CLEAR_SECS = 30


class MainWindow(tk.Frame):
    """Primary vault management interface."""

    def __init__(self, master: tk.Tk, vault: storage.Vault, on_logout):
        super().__init__(master, bg=BG)
        self.pack(fill=tk.BOTH, expand=True)
        self._master  = master
        self._vault   = vault
        self._on_logout = on_logout
        self._lock_timer_id = None
        self._entries_cache = []
        self._selected_id   = None
        self._raw_password  = ""
        self._pw_visible    = False

        self._build_ui()
        self._refresh_list()
        self._reset_lock_timer()

        master.bind_all("<Motion>",   self._reset_lock_timer)
        master.bind_all("<KeyPress>", self._reset_lock_timer)

    # ──────────────────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────
        topbar = tk.Frame(self, bg=BG2, pady=14)
        topbar.pack(fill=tk.X)

        tk.Label(
            topbar, text="🔐  SecureVault",
            font=("Segoe UI", 18, "bold"),
            bg=BG2, fg=FG,
        ).pack(side=tk.LEFT, padx=24)

        right_frame = tk.Frame(topbar, bg=BG2)
        right_frame.pack(side=tk.RIGHT, padx=16)

        for text, cmd in [("🔒  Lock", self._lock), ("⚙  Settings", self._open_settings)]:
            tk.Button(
                right_frame, text=text, command=cmd,
                bg="#2a2a45", fg=FG, font=FONT,
                relief=tk.FLAT, cursor="hand2",
                padx=16, pady=8,
                activebackground="#3a3a55", activeforeground=FG,
            ).pack(side=tk.LEFT, padx=6)

        # ── Toolbar ──────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=BG, pady=12)
        toolbar.pack(fill=tk.X, padx=20)

        tk.Button(
            toolbar, text="＋  Add Entry", command=self._add_entry,
            bg=ACCENT, fg=FG, font=FONT_BOLD,
            relief=tk.FLAT, cursor="hand2",
            padx=18, pady=10,
            activebackground="#c73652", activeforeground=FG,
        ).pack(side=tk.LEFT)

        # Search
        search_frame = tk.Frame(toolbar, bg=BG)
        search_frame.pack(side=tk.RIGHT)

        tk.Label(search_frame, text="🔍", bg=BG, fg=FG2,
                 font=("Segoe UI", 14)).pack(side=tk.LEFT, padx=(0, 6))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_list())

        search_entry = tk.Entry(
            search_frame, textvariable=self._search_var,
            bg=BG2, fg=FG, insertbackground=FG,
            font=FONT,
            relief=tk.FLAT,
            highlightthickness=2, highlightcolor=ACCENT, highlightbackground="#333",
            width=30,
        )
        search_entry.pack(side=tk.LEFT, ipady=8)

        tk.Button(
            search_frame, text="✕",
            command=lambda: self._search_var.set(""),
            bg=BG, fg=FG2, font=FONT,
            relief=tk.FLAT, cursor="hand2",
        ).pack(side=tk.LEFT, padx=4)

        # ── Divider ──────────────────────────────────────────────────────
        tk.Frame(self, bg="#2a2a45", height=2).pack(fill=tk.X)

        # ── Split pane ───────────────────────────────────────────────────
        pane = tk.PanedWindow(
            self, orient=tk.HORIZONTAL,
            bg=BG, sashwidth=6, sashrelief=tk.FLAT,
        )
        pane.pack(fill=tk.BOTH, expand=True)

        # Left: entry list
        list_frame = tk.Frame(pane, bg=BG2)
        pane.add(list_frame, minsize=300)

        tk.Label(
            list_frame, text="  ENTRIES",
            bg=BG2, fg=FG2, font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(12, 4))

        self._listbox = tk.Listbox(
            list_frame,
            bg=BG2, fg=FG,
            selectbackground=BG3, selectforeground=FG3,
            font=("Segoe UI", 13),          # larger list text
            relief=tk.FLAT,
            highlightthickness=0,
            activestyle="none",
            selectmode=tk.SINGLE,
            borderwidth=0,
        )
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._listbox.yview)
        self._listbox.config(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox.bind("<Double-Button-1>", lambda e: self._edit_entry())

        # Right: detail panel
        self._detail_frame = tk.Frame(pane, bg=BG)
        pane.add(self._detail_frame, minsize=500)
        self._build_detail_panel()

        # ── Status bar ───────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="  Ready")
        tk.Label(
            self, textvariable=self._status_var,
            bg="#111", fg=FG2, font=FONT_SM, anchor="w",
        ).pack(fill=tk.X, side=tk.BOTTOM, ipady=4)

    # ──────────────────────────────────────────────────────────────────────
    # Detail panel
    # ──────────────────────────────────────────────────────────────────────

    def _build_detail_panel(self):
        for w in self._detail_frame.winfo_children():
            w.destroy()

        self._detail_vars = {}

        rows = [
            ("title",    "Title",    False),
            ("username", "Username", False),
            ("password", "Password", True),
            ("url",      "URL",      False),
            ("notes",    "Notes",    False),
            ("created",  "Created",  False),
            ("modified", "Modified", False),
        ]

        tk.Label(
            self._detail_frame, text="Entry Details",
            font=("Segoe UI", 16, "bold"),
            bg=BG, fg=FG,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=28, pady=(28, 18))

        for r, (key, label, is_pw) in enumerate(rows, start=1):
            # Label column
            tk.Label(
                self._detail_frame,
                text=label + ":",
                bg=BG, fg=FG2,
                font=FONT_BOLD,
                width=11, anchor="w",
            ).grid(row=r, column=0, sticky="nw", padx=(28, 8), pady=8)

            var = tk.StringVar()
            self._detail_vars[key] = var

            if key == "notes":
                txt = tk.Text(
                    self._detail_frame,
                    height=4,
                    bg=BG2, fg=FG,
                    font=FONT,
                    relief=tk.FLAT,
                    highlightthickness=0,
                    state=tk.DISABLED,
                    wrap=tk.WORD,
                )
                txt.grid(row=r, column=1, columnspan=2, sticky="ew", padx=(0, 28), pady=8)
                self._notes_widget = txt

            elif is_pw:
                pw_frame = tk.Frame(self._detail_frame, bg=BG)
                pw_frame.grid(row=r, column=1, sticky="ew", pady=8)

                tk.Label(
                    pw_frame, textvariable=var,
                    bg=BG, fg=FG3,
                    font=("Consolas", 13),
                    anchor="w",
                ).pack(side=tk.LEFT)

                tk.Button(
                    pw_frame, text="👁",
                    bg=BG, fg=FG2,
                    font=("Segoe UI", 12),
                    relief=tk.FLAT, cursor="hand2",
                    command=lambda v=var: self._toggle_detail_pw(v),
                ).pack(side=tk.LEFT, padx=6)

                tk.Button(
                    self._detail_frame,
                    text="📋  Copy Password",
                    command=lambda k=key: self._copy_field(k),
                    bg=BG3, fg=FG,
                    font=FONT,
                    relief=tk.FLAT, cursor="hand2",
                    padx=12, pady=6,
                ).grid(row=r, column=2, padx=(8, 28), pady=8)

            else:
                is_meta = key in ("created", "modified")
                tk.Label(
                    self._detail_frame,
                    textvariable=var,
                    bg=BG,
                    fg=FG2 if is_meta else FG,
                    font=FONT_SM if is_meta else FONT,
                    anchor="w",
                    wraplength=380,
                    justify=tk.LEFT,
                ).grid(row=r, column=1, columnspan=2, sticky="ew", padx=(0, 28), pady=8)

        # ── Action buttons ────────────────────────────────────────────────
        btn_row = len(rows) + 2
        btn_pad = dict(padx=10, pady=10)

        self._edit_btn = tk.Button(
            self._detail_frame, text="✏  Edit",
            command=self._edit_entry,
            bg=BG3, fg=FG, font=FONT_BOLD,
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=10,
            state=tk.DISABLED,
            activebackground="#1a4a80", activeforeground=FG,
        )
        self._edit_btn.grid(row=btn_row, column=0, padx=(28, 8), pady=20, sticky="w")

        self._del_btn = tk.Button(
            self._detail_frame, text="🗑  Delete",
            command=self._delete_entry,
            bg="#3d1a1a", fg="#e74c3c", font=FONT_BOLD,
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=10,
            state=tk.DISABLED,
        )
        self._del_btn.grid(row=btn_row, column=1, padx=8, pady=20, sticky="w")

        tk.Button(
            self._detail_frame, text="📋  Copy Username",
            command=lambda: self._copy_field("username"),
            bg="#2a2a45", fg=FG, font=FONT,
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=10,
        ).grid(row=btn_row, column=2, padx=(8, 28), pady=20, sticky="e")

        self._detail_frame.columnconfigure(1, weight=1)

    # ──────────────────────────────────────────────────────────────────────
    # List helpers
    # ──────────────────────────────────────────────────────────────────────

    def _refresh_list(self, select_id=None):
        q = self._search_var.get().strip()
        if q:
            self._entries_cache = self._vault.search_entries(q)
        else:
            self._entries_cache = self._vault.get_entries()

        self._listbox.delete(0, tk.END)
        for e in self._entries_cache:
            self._listbox.insert(tk.END, f"   {e['title']}")

        target = select_id or self._selected_id
        if target:
            ids = [e["id"] for e in self._entries_cache]
            if target in ids:
                idx = ids.index(target)
                self._listbox.selection_set(idx)
                self._listbox.activate(idx)
                self._show_entry(self._entries_cache[idx])
                return
        self._clear_detail()

    def _on_select(self, _event=None):
        sel = self._listbox.curselection()
        if sel:
            entry = self._entries_cache[sel[0]]
            self._selected_id = entry["id"]
            self._show_entry(entry)
        else:
            self._clear_detail()

    def _show_entry(self, entry: dict):
        self._selected_id  = entry["id"]
        self._raw_password = entry.get("password", "")
        self._pw_visible   = False

        self._detail_vars["title"].set(entry.get("title", ""))
        self._detail_vars["username"].set(entry.get("username", ""))
        self._detail_vars["password"].set("••••••••••••")
        self._detail_vars["url"].set(entry.get("url", ""))
        self._detail_vars["created"].set(self._fmt_date(entry.get("created", "")))
        self._detail_vars["modified"].set(self._fmt_date(entry.get("modified", "")))

        self._notes_widget.config(state=tk.NORMAL)
        self._notes_widget.delete("1.0", tk.END)
        self._notes_widget.insert("1.0", entry.get("notes", ""))
        self._notes_widget.config(state=tk.DISABLED)

        self._edit_btn.config(state=tk.NORMAL)
        self._del_btn.config(state=tk.NORMAL)

    def _clear_detail(self):
        self._selected_id  = None
        self._raw_password = ""
        for var in self._detail_vars.values():
            var.set("")
        self._notes_widget.config(state=tk.NORMAL)
        self._notes_widget.delete("1.0", tk.END)
        self._notes_widget.config(state=tk.DISABLED)
        self._edit_btn.config(state=tk.DISABLED)
        self._del_btn.config(state=tk.DISABLED)

    # ──────────────────────────────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────────────────────────────

    def _add_entry(self):
        def on_save(fields):
            entry = self._vault.add_entry(**fields)
            self._vault.save()
            self._refresh_list(select_id=entry["id"])
            self._set_status(f"Entry '{fields['title']}' added.")
        EntryDialog(self._master, on_save=on_save)

    def _edit_entry(self):
        if not self._selected_id:
            return
        entry = next((e for e in self._entries_cache if e["id"] == self._selected_id), None)
        if not entry:
            return
        real_entry = {**entry, "password": self._raw_password}

        def on_save(fields):
            self._vault.update_entry(self._selected_id, **fields)
            self._vault.save()
            self._refresh_list(select_id=self._selected_id)
            self._set_status(f"Entry '{fields['title']}' updated.")

        EntryDialog(self._master, on_save=on_save, entry=real_entry)

    def _delete_entry(self):
        if not self._selected_id:
            return
        entry = next((e for e in self._entries_cache if e["id"] == self._selected_id), None)
        if not entry:
            return
        if messagebox.askyesno(
            "Delete Entry",
            f"Permanently delete '{entry['title']}'?",
            parent=self._master,
        ):
            self._vault.delete_entry(self._selected_id)
            self._vault.save()
            self._selected_id = None
            self._refresh_list()
            self._set_status(f"Entry '{entry['title']}' deleted.")

    # ──────────────────────────────────────────────────────────────────────
    # Clipboard
    # ──────────────────────────────────────────────────────────────────────

    def _copy_field(self, field: str):
        if not self._selected_id:
            return
        entry = next((e for e in self._entries_cache if e["id"] == self._selected_id), None)
        if not entry:
            return
        value = self._raw_password if field == "password" else entry.get(field, "")
        if value:
            clipboard.copy_to_clipboard(value, clear_after=CLIPBOARD_CLEAR_SECS)
            self._set_status(
                f"{field.capitalize()} copied — clipboard clears in {CLIPBOARD_CLEAR_SECS}s"
            )

    # ──────────────────────────────────────────────────────────────────────
    # Password reveal
    # ──────────────────────────────────────────────────────────────────────

    def _toggle_detail_pw(self, var):
        self._pw_visible = not self._pw_visible
        var.set(self._raw_password if self._pw_visible else "••••••••••••")

    # ──────────────────────────────────────────────────────────────────────
    # Auto-lock
    # ──────────────────────────────────────────────────────────────────────

    def _reset_lock_timer(self, _event=None):
        if self._lock_timer_id:
            self._master.after_cancel(self._lock_timer_id)
        self._lock_timer_id = self._master.after(AUTO_LOCK_MS, self._auto_lock)

    def _auto_lock(self):
        self._set_status("Auto-locked due to inactivity.")
        self._lock()

    def _lock(self):
        clipboard.cancel_pending_clear()
        self._vault.lock()
        self._clear_detail()
        if self._lock_timer_id:
            self._master.after_cancel(self._lock_timer_id)
        self._on_logout()

    # ──────────────────────────────────────────────────────────────────────
    # Settings / helpers
    # ──────────────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsDialog(self._master, self._vault, self._set_status)

    def _set_status(self, msg: str):
        self._status_var.set(f"  {msg}")

    @staticmethod
    def _fmt_date(iso: str) -> str:
        if not iso:
            return ""
        try:
            return datetime.fromisoformat(iso).strftime("%Y-%m-%d  %H:%M  UTC")
        except Exception:
            return iso


# ──────────────────────────────────────────────────────────────────────────────
# Settings Dialog
# ──────────────────────────────────────────────────────────────────────────────

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, vault: storage.Vault, status_cb):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._vault     = vault
        self._status_cb = status_cb
        self._build_ui()
        self.grab_set()
        self.focus_set()

    def _build_ui(self):
        tk.Label(
            self, text="⚙  Settings",
            font=("Segoe UI", 16, "bold"),
            bg=BG, fg=FG,
        ).pack(anchor="w", padx=28, pady=(24, 10))

        tk.Frame(self, bg="#2a2a45", height=2).pack(fill=tk.X, padx=28)

        tk.Label(
            self, text="Change Master Password",
            bg=BG, fg=FG2, font=FONT_BOLD,
        ).pack(anchor="w", padx=28, pady=(18, 6))

        self._old_pw  = self._pw_field("Current Password")
        self._new_pw  = self._pw_field("New Password")
        self._new_pw2 = self._pw_field("Confirm New Password")

        tk.Button(
            self, text="Update Password",
            command=self._change_pw,
            bg=ACCENT, fg=FG, font=FONT_BOLD,
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=10,
        ).pack(anchor="w", padx=28, pady=(12, 28))

    def _pw_field(self, label: str):
        var = tk.StringVar()
        tk.Label(self, text=label, bg=BG, fg=FG2, font=FONT).pack(
            anchor="w", padx=28, pady=(6, 2)
        )
        tk.Entry(
            self, textvariable=var, show="•",
            bg=BG2, fg=FG, insertbackground=FG,
            font=FONT, relief=tk.FLAT,
            highlightthickness=2, highlightcolor=ACCENT, highlightbackground="#333",
            width=34,
        ).pack(padx=28, ipady=8, pady=(0, 4))
        return var

    def _change_pw(self):
        old  = self._old_pw.get()
        new  = self._new_pw.get()
        conf = self._new_pw2.get()
        if not old or not new:
            messagebox.showerror("Error", "All fields are required.", parent=self)
            return
        if new != conf:
            messagebox.showerror("Error", "New passwords do not match.", parent=self)
            return
        if len(new) < 10:
            messagebox.showerror("Error", "Password must be at least 10 characters.", parent=self)
            return
        try:
            from ui_login import VAULT_PATH
            storage.Vault.open(VAULT_PATH, old)   # verify current password
            self._vault.change_master_password(new)
            self._status_cb("Master password changed successfully.")
            messagebox.showinfo("Success", "Master password updated.", parent=self)
            self.destroy()
        except storage.VaultError as e:
            messagebox.showerror("Error", str(e), parent=self)
