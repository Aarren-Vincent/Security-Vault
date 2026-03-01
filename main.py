"""
main.py - Entry point for SecureVault Password Manager.

Run with:
    python main.py

Requirements:
    pip install cryptography
"""

import tkinter as tk
import clipboard
from ui_login import LoginScreen
from ui_main import MainWindow


APP_TITLE  = "SecureVault — Password Manager"
MIN_WIDTH  = 1100
MIN_HEIGHT = 700


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")
        self.configure(bg="#1a1a2e")

        # DPI awareness on Windows (makes text crisp on high-DPI screens)
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass

        clipboard.set_root(self)
        self._show_login()

    def _show_login(self):
        for w in self.winfo_children():
            w.destroy()
        LoginScreen(self, on_success=self._show_main)

    def _show_main(self, vault):
        for w in self.winfo_children():
            w.destroy()
        MainWindow(self, vault=vault, on_logout=self._show_login)

    def destroy(self):
        clipboard.cancel_pending_clear()
        super().destroy()


def main():
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()


if __name__ == "__main__":
    main()
