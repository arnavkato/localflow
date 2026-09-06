"""Paste text at the current cursor via clipboard + Ctrl+V, then restore the clipboard.

More reliable than char-by-char typing across browsers, VS Code, Slack, etc.
"""
import time

import pyperclip
from pynput.keyboard import Controller, Key

_kbd = Controller()


def paste(text):
    if not text:
        return
    try:
        prev = pyperclip.paste()
    except Exception:
        prev = None

    pyperclip.copy(text)
    time.sleep(0.05)  # let the OS register the new clipboard contents

    with _kbd.pressed(Key.ctrl):
        _kbd.press("v")
        _kbd.release("v")

    # ponytail: fixed 0.15s wait for the target app to read the clipboard before we
    # restore it. Good enough; bump it if a slow app pastes the old contents instead.
    if prev is not None:
        time.sleep(0.15)
        pyperclip.copy(prev)
