"""Global hotkey with push-to-talk (hold) and toggle (press/press) modes.

pynput's GlobalHotKeys only fires on activation, so we track press/release edges
ourselves to support hold-to-record. The edge logic lives in _StateMachine (pure,
no pynput) so it stays testable; HotkeyHandler just wires it to the OS listener.
"""


class _StateMachine:
    """Turns key press/release edges into start/stop callbacks. Keys are any
    hashable (canonical pynput keys in production, strings in the self-check)."""

    def __init__(self, keys, mode, on_start, on_stop):
        self.keys = set(keys)
        self.mode = mode
        self.on_start = on_start
        self.on_stop = on_stop
        self._pressed = set()
        self._combo_down = False
        self._recording = False

    def press(self, k):
        if k in self.keys:
            self._pressed.add(k)
            self._update()

    def release(self, k):
        if k in self._pressed:
            self._pressed.discard(k)
            self._update()

    def _update(self):
        down = self.keys <= self._pressed
        if down and not self._combo_down:
            self._combo_down = True
            self._edge_down()
        elif not down and self._combo_down:
            self._combo_down = False
            self._edge_up()

    def _edge_down(self):
        if self.mode == "toggle":
            self._recording = not self._recording
            (self.on_start if self._recording else self.on_stop)()
        elif not self._recording:  # push-to-talk
            self._recording = True
            self.on_start()

    def _edge_up(self):
        if self.mode == "push-to-talk" and self._recording:
            self._recording = False
            self.on_stop()


class HotkeyHandler:
    def __init__(self, combo, mode, on_start, on_stop):
        from pynput import keyboard  # imported here so the self-check runs without pynput
        self._keyboard = keyboard
        keys = keyboard.HotKey.parse(combo)  # canonical key objects
        self._sm = _StateMachine(keys, mode, on_start, on_stop)
        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)

    def _press(self, key):
        self._sm.press(self._listener.canonical(key))

    def _release(self, key):
        self._sm.release(self._listener.canonical(key))

    def start(self):
        self._listener.start()

    def join(self):
        self._listener.join()


if __name__ == "__main__":
    # self-check: drive the pure state machine (no pynput / no OS listener needed)
    ev = []
    ptt = _StateMachine({"ctrl", "space"}, "push-to-talk",
                        lambda: ev.append("start"), lambda: ev.append("stop"))
    ptt.press("ctrl")
    ptt.press("space")
    assert ev == ["start"], ev
    ptt.release("space")            # combo broken -> stop
    assert ev == ["start", "stop"], ev
    ptt.release("ctrl")            # already stopped, no extra event
    assert ev == ["start", "stop"], ev

    ev.clear()
    tog = _StateMachine({"ctrl", "space"}, "toggle",
                        lambda: ev.append("start"), lambda: ev.append("stop"))
    tog.press("ctrl"); tog.press("space")          # first activation -> start
    tog.release("space"); tog.release("ctrl")
    assert ev == ["start"], ev
    tog.press("ctrl"); tog.press("space")          # second activation -> stop
    tog.release("space"); tog.release("ctrl")
    assert ev == ["start", "stop"], ev
    print("hotkey ok")
