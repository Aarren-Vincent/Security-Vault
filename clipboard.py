"""
clipboard.py - Clipboard utilities with auto-clear support.

Copies sensitive data to the system clipboard and schedules
an automatic clear after a configurable timeout.
"""

import threading
import tkinter as tk
from typing import Optional

_clear_timer: Optional[threading.Timer] = None
_root_ref: Optional[tk.Tk] = None   # set by the main app


def set_root(root: tk.Tk) -> None:
    """Register the Tk root window so we can access the clipboard."""
    global _root_ref
    _root_ref = root


def copy_to_clipboard(text: str, clear_after: int = 30) -> None:
    """
    Copy *text* to the system clipboard.

    Parameters
    ----------
    text        : the sensitive string to copy
    clear_after : seconds until the clipboard is automatically cleared (0 = never)
    """
    global _clear_timer

    if _root_ref is None:
        raise RuntimeError("call set_root() before using the clipboard helper")

    # Cancel any pending clear
    if _clear_timer is not None and _clear_timer.is_alive():
        _clear_timer.cancel()
        _clear_timer = None

    _root_ref.clipboard_clear()
    _root_ref.clipboard_append(text)
    _root_ref.update()   # flush to OS

    if clear_after > 0:
        _clear_timer = threading.Timer(clear_after, _clear_clipboard_if_unchanged, args=[text])
        _clear_timer.daemon = True
        _clear_timer.start()


def _clear_clipboard_if_unchanged(original: str) -> None:
    """Clear the clipboard only if it still contains *original* (avoid nuking user's own copy)."""
    if _root_ref is None:
        return
    try:
        current = _root_ref.clipboard_get()
        if current == original:
            _root_ref.clipboard_clear()
            _root_ref.update()
    except tk.TclError:
        pass  # clipboard empty or unavailable


def cancel_pending_clear() -> None:
    """Cancel any scheduled clipboard-clear timer."""
    global _clear_timer
    if _clear_timer is not None:
        _clear_timer.cancel()
        _clear_timer = None
