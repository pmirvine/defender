import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
import controls
from input import read_inputs


class Keys(dict):
    def __missing__(self, k):
        return False


def test_defaults_match_spec():
    d = controls.DEFAULTS
    assert d["up"] == pygame.K_a and d["down"] == pygame.K_z
    assert d["thrust"] == pygame.K_LSHIFT and d["reverse"] == pygame.K_CAPSLOCK
    assert d["fire"] == pygame.K_RETURN and d["smart_bomb"] == pygame.K_SPACE
    assert d["hyperspace"] == pygame.K_h


def test_read_inputs_default_keys():
    b = dict(controls.DEFAULTS)
    inp = read_inputs(Keys({pygame.K_a: True, pygame.K_RETURN: True}), b)
    assert inp.up and inp.fire and not inp.down and not inp.smart_bomb


def test_right_shift_also_thrusts():
    inp = read_inputs(Keys({pygame.K_RSHIFT: True}), dict(controls.DEFAULTS))
    assert inp.thrust


def test_capslock_is_a_pulse_not_held_state():
    b = dict(controls.DEFAULTS)
    assert read_inputs(Keys({pygame.K_CAPSLOCK: True}), b).reverse is False
    assert read_inputs(Keys(), b, pulses={pygame.K_CAPSLOCK}).reverse is True


def test_rebind_swaps_on_conflict_and_rejects_escape():
    b = dict(controls.DEFAULTS)
    assert controls.rebind(b, "up", pygame.K_z)
    assert b["up"] == pygame.K_z and b["down"] == pygame.K_a
    assert not controls.rebind(b, "up", pygame.K_ESCAPE)
    assert b["up"] == pygame.K_z


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    b = dict(controls.DEFAULTS)
    controls.rebind(b, "fire", pygame.K_f)
    controls.save(b, p)
    assert controls.load(p) == b
    assert controls.load(tmp_path / "missing.json") == controls.DEFAULTS


def test_menu_rebind_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(controls, "PATH", tmp_path / "m.json")
    monkeypatch.setattr(controls, "save", lambda b, path=None: None)
    b = dict(controls.DEFAULTS)
    m = controls.ControlsMenu(b)
    ev = lambda k: pygame.event.Event(pygame.KEYDOWN, key=k)
    m.handle_event(ev(pygame.K_RETURN))       # start waiting on "up"
    assert m.waiting
    m.handle_event(ev(pygame.K_q))
    assert b["up"] == pygame.K_q and not m.waiting
    assert m.handle_event(ev(pygame.K_ESCAPE)) is True
