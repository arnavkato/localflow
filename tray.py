"""Tray icon + console cue for state. Degrades to console-only if pystray/Pillow
are missing or tray is disabled in config."""
import threading

_COLORS = {
    "idle": (90, 90, 90),
    "recording": (200, 40, 40),
    "processing": (220, 160, 20),
}


class Status:
    def __init__(self, enabled):
        self.enabled = enabled
        self.icon = None
        if enabled:
            try:
                import pystray
                from PIL import Image
                self._pystray, self._Image = pystray, Image
                self.icon = pystray.Icon("localflow", self._img("idle"), "LocalFlow")
            except Exception as e:
                print(f"[tray] disabled ({e}); using console cues only")
                self.enabled = False

    def _img(self, state):
        return self._Image.new("RGB", (64, 64), _COLORS.get(state, _COLORS["idle"]))

    def set(self, state):
        print(f"[state] {state}")
        if self.enabled and self.icon:
            self.icon.icon = self._img(state)
            self.icon.title = f"LocalFlow — {state}"

    def run(self):
        """Block the main thread: run the tray loop, or wait forever if no tray."""
        if self.enabled and self.icon:
            self.icon.run()
        else:
            threading.Event().wait()
