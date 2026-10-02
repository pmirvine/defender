"""User-definable keyboard bindings, persisted to ~/.defender_controls.json, plus the remap menu."""
import json
from pathlib import Path

import pygame

import font

PATH = Path.home() / ".defender_controls.json"

# (action, label) in menu order.
ACTIONS = [
    ("up", "MOVE UP"),
    ("down", "MOVE DOWN"),
    ("thrust", "THRUST"),
    ("reverse", "REVERSE"),
    ("fire", "FIRE"),
    ("smart_bomb", "SMART BOMB"),
    ("hyperspace", "HYPERSPACE"),
]

DEFAULTS = {
    "up": pygame.K_a,
    "down": pygame.K_z,
    "thrust": pygame.K_LSHIFT,
    "reverse": pygame.K_CAPSLOCK,
    "fire": pygame.K_RETURN,
    "smart_bomb": pygame.K_SPACE,
    "hyperspace": pygame.K_h,
}

# Binding a left-hand modifier also accepts its right-hand twin.
TWINS = {
    pygame.K_LSHIFT: pygame.K_RSHIFT, pygame.K_RSHIFT: pygame.K_LSHIFT,
    pygame.K_LCTRL: pygame.K_RCTRL, pygame.K_RCTRL: pygame.K_LCTRL,
    pygame.K_LALT: pygame.K_RALT, pygame.K_RALT: pygame.K_LALT,
}

# Latching keys report "pressed" while toggled on, so they act as one-shot pulses instead.
TOGGLE_KEYS = {pygame.K_CAPSLOCK, pygame.K_NUMLOCK, pygame.K_SCROLLOCK}

RESERVED = {pygame.K_ESCAPE}


def keys_for(key):
    """All physical keys that trigger a binding to `key`."""
    return (key, TWINS[key]) if key in TWINS else (key,)


def key_label(key):
    return pygame.key.name(key).upper() or "KEY %d" % key


def load(path=PATH):
    """Return {action: keycode}; missing/invalid entries fall back to defaults."""
    binds = dict(DEFAULTS)
    try:
        data = json.loads(Path(path).read_text())
        for action in DEFAULTS:
            name = data.get(action)
            if isinstance(name, str):
                code = pygame.key.key_code(name)
                if code not in RESERVED:
                    binds[action] = code
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return binds


def save(binds, path=PATH):
    try:
        Path(path).write_text(json.dumps({a: pygame.key.name(k) for a, k in binds.items()}, indent=1))
    except OSError:
        pass


def rebind(binds, action, key):
    """Bind `key` to `action`; if another action already uses it, the two swap keys."""
    if key in RESERVED:
        return False
    for other, k in binds.items():
        if other != action and (k == key or TWINS.get(k) == key):
            binds[other] = binds[action]
            break
    binds[action] = key
    return True


class ControlsMenu:
    """Arrow keys select, Enter rebinds, R resets all, Esc returns."""

    def __init__(self, binds):
        self.binds = binds
        self.sel = 0
        self.waiting = False

    def handle_event(self, ev):
        """Feed KEYDOWN events. Returns True when the menu should close."""
        if ev.type != pygame.KEYDOWN:
            return False
        if self.waiting:
            if ev.key != pygame.K_ESCAPE:
                rebind(self.binds, ACTIONS[self.sel][0], ev.key)
                save(self.binds)
            self.waiting = False
            return False
        if ev.key == pygame.K_ESCAPE:
            return True
        if ev.key == pygame.K_UP:
            self.sel = (self.sel - 1) % len(ACTIONS)
        elif ev.key == pygame.K_DOWN:
            self.sel = (self.sel + 1) % len(ACTIONS)
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.waiting = True
        elif ev.key == pygame.K_r:
            self.binds.clear()
            self.binds.update(DEFAULTS)
            save(self.binds)
        return False

    def draw(self, surf, tick=0):
        surf.fill((0, 0, 0))
        w = surf.get_width()
        font.draw_text(surf, "CONTROLS", (w // 2, 24), (255, 255, 255), center=True, scale=2)
        for i, (action, label) in enumerate(ACTIONS):
            y = 62 + i * 18
            on = i == self.sel
            col = (255, 230, 0) if on else (0, 182, 0)
            font.draw_text(surf, label, (50, y), col)
            if on and self.waiting:
                if (tick // 20) % 2 == 0:
                    font.draw_text(surf, "PRESS A KEY", (170, y), (255, 60, 60))
            else:
                font.draw_text(surf, key_label(self.binds[action]), (170, y), col)
            if on and not self.waiting:
                font.draw_text(surf, ">", (38, y), col)
        font.draw_text(surf, "UP DOWN SELECT   ENTER CHANGE", (w // 2, 200), (200, 200, 200), center=True)
        font.draw_text(surf, "R RESET ALL   ESC BACK", (w // 2, 214), (200, 200, 200), center=True)
