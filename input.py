"""Bound keys (see controls.py) and optional gamepad -> Inputs."""
import pygame

import controls
from game import Inputs

ACTION_FIELDS = [a for a, _ in controls.ACTIONS]


def read_inputs(pressed, binds, joystick=None, coin_event=False, pulses=()):
    """Build an Inputs from the key state, the user's bindings and an optional joystick.

    `pulses` holds keys that changed state this frame and are bound to latching keys
    (Caps Lock); those count as a press for one tick regardless of `pressed`.
    """
    inp = Inputs()
    for action in ACTION_FIELDS:
        key = binds[action]
        if key in controls.TOGGLE_KEYS:
            held = key in pulses
        else:
            held = any(pressed[k] for k in controls.keys_for(key))
        setattr(inp, action, held)
    if joystick is not None:
        ax = joystick.get_axis(0) if joystick.get_numaxes() > 0 else 0.0
        ay = joystick.get_axis(1) if joystick.get_numaxes() > 1 else 0.0
        inp.up = inp.up or ay < -0.5
        inp.down = inp.down or ay > 0.5
        inp.thrust = inp.thrust or joystick.get_button(0)
        inp.fire = inp.fire or joystick.get_button(1)
        inp.smart_bomb = inp.smart_bomb or joystick.get_button(2)
        inp.hyperspace = inp.hyperspace or joystick.get_button(3)
        inp.reverse = inp.reverse or joystick.get_button(4) or abs(ax) > 0.8
    inp.coin = coin_event
    return inp
