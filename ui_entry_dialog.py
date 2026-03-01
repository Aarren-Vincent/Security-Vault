"""
ui_entry_dialog.py - Add / Edit password entry dialog.
"""

import tkinter as tk
from tkinter import messagebox

import generator
import clipboard


BG       = "#1a1a2e"
BG2      = "#16213e"
ACCENT   = "#e94560"
FG       = "#ffffff"
FG2      = "#a0a0b0"
FONT     = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 12, "bold")
FONT_SM  = ("Segoe UI", 10)


def _entry_widget(parent, var, show=""):
    """Reusable styled Entry."""
    return tk.Entry(
        parent, textvariable=var, show=show,
        bg=BG2, fg=FG, insertbackground=FG,
        font=FONT, relief=tk.FLAT,
        highlightthickness=2, highlightcolor=ACCENT, highlightbackground="#333",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Add / Edit Entry Dialog
# ──────────────────────────────────────────────────────────────────────────────

class EntryDialog(tk.Toplevel):
    """
    Modal dialog for creating or editing a password entry.
    *entry* is None for a new entry, or an existing entry dict for editing.
    On save, calls *on_save(fields_dict)*.
    """

    def __init__(self, parent, on_save, entry=None):
        super().__init__(parent)
        self.title("Add Entry" if entry is None else "Edit Entry")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._on_save   = on_save
        self._entry     = entry
        self._show_pw   = False
        self._build_ui()
        self._center(parent)
        self.grab_set()
        self.focus_set()

    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        H_PAD = dict(padx=28, pady=8)

        # Header
        tk.Label(
            self,
            text="Add Password Entry" if self._entry is None else "Edit Password Entry",
            font=("Segoe UI", 15, "bold"),
            bg=BG, fg=FG,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=28, pady=(24, 16))

        tk.Frame(self, bg="#2a2a45", height=2).grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=28, pady=(0, 12)
        )

        fields = [
            ("title",    "Title *",    False),
            ("username", "Username *", False),
            ("password", "Password *", True),
            ("url",      "URL",        False),
        ]

        self._vars = {}
        pw_row = None

        for r, (key, label, is_pw) in enumerate(fields, start=2):
            tk.Label(
                self, text=label,
                bg=BG, fg=FG2, font=FONT,
                width=13, anchor="w",
            ).grid(row=r, column=0, sticky="w", padx=(28, 0), pady=8)

            var = tk.StringVar(value=self._entry.get(key, "") if self._entry else "")
            self._vars[key] = var

            if is_pw:
                pw_row = r
                self._pw_entry = _entry_widget(self, var, show="•")
                self._pw_entry.grid(row=r, column=1, sticky="ew", ipady=8, padx=(8, 0), pady=8)

                # Eye toggle
                self._eye_btn = tk.Button(
                    self, text="👁",
                    bg=BG2, fg=FG2, font=("Segoe UI", 12),
                    relief=tk.FLAT, cursor="hand2",
                    command=self._toggle_pw,
                )
                self._eye_btn.grid(row=r, column=2, padx=(6, 28))
            else:
                e = _entry_widget(self, var)
                e.grid(row=r, column=1, columnspan=2, sticky="ew", ipady=8,
                       padx=(8, 28), pady=8)
                if r == 2:
                    e.focus_set()

        # Generate + strength row (below password field)
        gen_row = pw_row + 1
        gen_frame = tk.Frame(self, bg=BG)
        gen_frame.grid(row=gen_row, column=1, sticky="w", padx=(8, 0), pady=(0, 8))

        tk.Button(
            gen_frame, text="⚙  Generate Password",
            command=self._open_generator,
            bg=ACCENT, fg=FG, font=FONT_BOLD,
            relief=tk.FLAT, cursor="hand2",
            padx=14, pady=7,
        ).pack(side=tk.LEFT)

        self._strength_lbl = tk.Label(
            gen_frame, text="",
            bg=BG, fg=FG2, font=FONT_SM,
        )
        self._strength_lbl.pack(side=tk.LEFT, padx=12)
        self._vars["password"].trace_add("write", self._update_strength)

        # Notes
        notes_row = gen_row + 1
        tk.Label(
            self, text="Notes",
            bg=BG, fg=FG2, font=FONT, width=13, anchor="w",
        ).grid(row=notes_row, column=0, sticky="nw", padx=(28, 0), pady=8)

        self._notes = tk.Text(
            self, height=5,
            bg=BG2, fg=FG, insertbackground=FG,
            font=FONT, relief=tk.FLAT, wrap=tk.WORD,
            highlightthickness=2, highlightcolor=ACCENT, highlightbackground="#333",
        )
        self._notes.grid(row=notes_row, column=1, columnspan=2, sticky="ew",
                         padx=(8, 28), pady=8)
        if self._entry:
            self._notes.insert("1.0", self._entry.get("notes", ""))

        # Buttons
        btn_row = notes_row + 1
        tk.Frame(self, bg="#2a2a45", height=2).grid(
            row=btn_row, column=0, columnspan=3, sticky="ew", padx=28, pady=(8, 0)
        )

        btns = tk.Frame(self, bg=BG)
        btns.grid(row=btn_row + 1, column=0, columnspan=3, sticky="e", padx=28, pady=16)

        tk.Button(
            btns, text="Cancel", command=self.destroy,
            bg="#2a2a45", fg=FG, font=FONT,
            relief=tk.FLAT, cursor="hand2", padx=18, pady=10,
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btns, text="Save Entry", command=self._save,
            bg=ACCENT, fg=FG, font=FONT_BOLD,
            relief=tk.FLAT, cursor="hand2", padx=18, pady=10,
            activebackground="#c73652", activeforeground=FG,
        ).pack(side=tk.LEFT)

        self.columnconfigure(1, weight=1)
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())

    # ──────────────────────────────────────────────────────────────────────

    def _toggle_pw(self):
        self._show_pw = not self._show_pw
        self._pw_entry.config(show="" if self._show_pw else "•")

    def _update_strength(self, *_):
        pw = self._vars["password"].get()
        entropy = generator.estimate_entropy(pw)
        label, color = generator.strength_label(entropy)
        self._strength_lbl.config(text=label, fg=color)

    def _open_generator(self):
        PasswordGeneratorDialog(self, on_accept=lambda pw: self._vars["password"].set(pw))

    def _save(self):
        title    = self._vars["title"].get().strip()
        username = self._vars["username"].get().strip()
        password = self._vars["password"].get()

        if not title:
            messagebox.showerror("Validation", "Title is required.", parent=self)
            return
        if not username:
            messagebox.showerror("Validation", "Username is required.", parent=self)
            return
        if not password:
            messagebox.showerror("Validation", "Password is required.", parent=self)
            return

        self._on_save({
            "title":    title,
            "username": username,
            "password": password,
            "url":      self._vars["url"].get().strip(),
            "notes":    self._notes.get("1.0", tk.END).strip(),
        })
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w  = self.winfo_reqwidth()
        h  = self.winfo_reqheight()
        self.geometry(f"+{px + (pw - w)//2}+{py + (ph - h)//2}")


# ──────────────────────────────────────────────────────────────────────────────
# Password Generator Dialog
# ──────────────────────────────────────────────────────────────────────────────

class PasswordGeneratorDialog(tk.Toplevel):
    """Inline password generator with charset options."""

    def __init__(self, parent, on_accept):
        super().__init__(parent)
        self.title("Password Generator")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._on_accept = on_accept
        self._generated = tk.StringVar()
        self._build_ui()
        self.grab_set()
        self.focus_set()
        self._generate()

    def _build_ui(self):
        tk.Label(
            self, text="⚙  Password Generator",
            font=("Segoe UI", 15, "bold"),
            bg=BG, fg=FG,
        ).pack(anchor="w", padx=28, pady=(22, 10))

        tk.Frame(self, bg="#2a2a45", height=2).pack(fill=tk.X, padx=28, pady=(0, 14))

        # Length slider
        len_frame = tk.Frame(self, bg=BG)
        len_frame.pack(fill=tk.X, padx=28, pady=6)
        tk.Label(len_frame, text="Length:", bg=BG, fg=FG2, font=FONT).pack(side=tk.LEFT)
        self._length_var = tk.IntVar(value=20)
        tk.Scale(
            len_frame, variable=self._length_var, from_=8, to=64,
            orient=tk.HORIZONTAL,
            bg=BG, fg=FG, highlightthickness=0,
            troughcolor="#2a2a45", activebackground=ACCENT,
            command=lambda _: self._generate(),
            length=260,
        ).pack(side=tk.LEFT, padx=8)
        tk.Label(len_frame, textvariable=self._length_var,
                 bg=BG, fg=FG, font=FONT_BOLD, width=3).pack(side=tk.LEFT)

        # Checkboxes
        self._lower   = self._checkbox("Lowercase  (a–z)",              True)
        self._upper   = self._checkbox("Uppercase  (A–Z)",              True)
        self._digits  = self._checkbox("Digits  (0–9)",                 True)
        self._symbols = self._checkbox("Symbols  (!@#$…)",              True)
        self._no_amb  = self._checkbox("Exclude ambiguous  (0/O, 1/l)", False)

        # Generated password display
        display = tk.Frame(self, bg="#0d1b2a", pady=14)
        display.pack(fill=tk.X, padx=28, pady=14)
        tk.Label(
            display, textvariable=self._generated,
            bg="#0d1b2a", fg=FG3,
            font=("Consolas", 14, "bold"),
            wraplength=380, justify=tk.CENTER,
        ).pack(padx=14)

        # Entropy label
        self._entropy_lbl = tk.Label(self, text="", bg=BG, fg=FG2, font=FONT_SM)
        self._entropy_lbl.pack()

        # Buttons
        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=(12, 24), padx=28, anchor="e")

        tk.Button(
            btns, text="🔄  Regenerate",
            command=self._generate,
            bg="#2a2a45", fg=FG, font=FONT,
            relief=tk.FLAT, cursor="hand2",
            padx=14, pady=9,
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btns, text="Use this Password",
            command=self._accept,
            bg=ACCENT, fg=FG, font=FONT_BOLD,
            relief=tk.FLAT, cursor="hand2",
            padx=14, pady=9,
            activebackground="#c73652", activeforeground=FG,
        ).pack(side=tk.LEFT)

    def _checkbox(self, text: str, default: bool) -> tk.BooleanVar:
        var = tk.BooleanVar(value=default)
        tk.Checkbutton(
            self, text=text, variable=var,
            bg=BG, fg=FG2, font=FONT,
            selectcolor=BG2,
            activebackground=BG, activeforeground=FG,
            command=self._generate,
        ).pack(anchor="w", padx=28, pady=2)
        return var

    def _generate(self):
        try:
            pw = generator.generate_password(
                length=self._length_var.get(),
                use_lowercase=self._lower.get(),
                use_uppercase=self._upper.get(),
                use_digits=self._digits.get(),
                use_symbols=self._symbols.get(),
                exclude_ambiguous=self._no_amb.get(),
            )
            self._generated.set(pw)
            entropy = generator.estimate_entropy(pw)
            label, color = generator.strength_label(entropy)
            self._entropy_lbl.config(
                text=f"Entropy: {entropy:.0f} bits  —  {label}", fg=color
            )
        except ValueError as exc:
            self._generated.set("")
            self._entropy_lbl.config(text=str(exc), fg="#e74c3c")

    def _accept(self):
        pw = self._generated.get()
        if pw:
            self._on_accept(pw)
            self.destroy()
