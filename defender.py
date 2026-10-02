"""Defender: main loop. Fixed 60 Hz logic, 304x256 scaled display."""
import argparse
import sys

import pygame

import controls
import font
import highscores
import settings
from display import Display
from attract import Attract
from game import Game
from input import read_inputs
from render import Renderer

W, H = 304, 256
DT = 1.0 / 60.0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="defender", description="Defender (Williams, 1981) in pygame-ce")
    ap.add_argument("--scale", type=settings.parse_scale, metavar="N|auto",
                    help="pixel scale: window is N x the 304x256 arcade screen (1-%d), or 'auto' to fit "
                         "your desktop" % settings.MAX_SCALE)
    ap.add_argument("--fullscreen", action=argparse.BooleanOptionalAction, help="start fullscreen")
    ap.add_argument("--smooth", action=argparse.BooleanOptionalAction,
                    help="smooth scaling instead of crisp square pixels")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    prefs = settings.load()
    for key in ("scale", "fullscreen", "smooth"):  # command line overrides saved settings for this run
        if getattr(args, key) is not None:
            prefs[key] = getattr(args, key)
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption("DEFENDER")
    display = Display(**prefs)
    screen = display.canvas
    pygame.mouse.set_visible(False)

    try:
        from sound import SoundBoard
        sound = SoundBoard()
        sound.preload()
    except Exception as exc:  # sound is optional; never block play
        print("sound disabled:", exc, file=sys.stderr)
        sound = None

    joy = None
    if pygame.joystick.get_count():
        joy = pygame.joystick.Joystick(0)
        joy.init()

    binds = controls.load()
    menu = None  # ControlsMenu while the remap screen is open
    pulses = set()  # latching-key changes (Caps Lock) waiting to be fed to the game
    scores = highscores.load()
    game = Game(highscores=scores)
    renderer = Renderer()
    attract = Attract(scores)
    clock = pygame.time.Clock()
    credits = 0
    playing = False
    entering = None  # [initials list] while typing a high-score name
    acc = 0.0
    entry_done = False
    game_over_ticks = 0

    def play(name):
        if sound:
            sound.play(name)

    while True:
        coin = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type in (pygame.KEYDOWN, pygame.KEYUP) and ev.key in controls.TOGGLE_KEYS:
                pulses.add(ev.key)
            if ev.type == pygame.KEYDOWN and not (menu is not None and menu.waiting):
                changed = True
                if ev.key == pygame.K_F11:
                    display.toggle_fullscreen()
                elif ev.key == pygame.K_F8:
                    display.change_scale(+1)
                elif ev.key == pygame.K_F7:
                    display.change_scale(-1)
                elif ev.key == pygame.K_F9:
                    display.toggle_smooth()
                else:
                    changed = False
                if changed:
                    settings.save(display.current())
                    continue
            if menu is not None:
                if menu.handle_event(ev):
                    menu = None
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
                if ev.key == pygame.K_F2 and not playing:
                    menu = controls.ControlsMenu(binds)
                    continue
                if ev.key == pygame.K_5 and not playing:
                    credits += 1
                    coin = True
                    play("coin")
                if entering is not None:
                    if ev.key == pygame.K_BACKSPACE and entering:
                        entering.pop()
                    elif ev.unicode and ev.unicode.isalpha() and len(entering) < 3:
                        entering.append(ev.unicode.upper())
                    elif ev.key == pygame.K_RETURN and len(entering) == 3:
                        scores = highscores.insert(scores, "".join(entering), game.score)
                        highscores.save(scores)
                        attract.scores = scores
                        entering = None
                        entry_done = True
                elif not playing and ev.key in (pygame.K_1, pygame.K_RETURN):
                    # free play when no credit has been inserted
                    credits = max(0, credits - 1)
                    game.start_game()
                    playing = True
                    play("start")

        acc += min(clock.tick(60) / 1000.0, 0.1)
        while acc >= DT:
            acc -= DT
            if playing:
                if entering is None:
                    game.update(read_inputs(pygame.key.get_pressed(), binds, joy, coin, pulses))
                    pulses.clear()
                if game.state == "game_over" and entering is None:
                    if not entry_done and highscores.qualifies(scores, game.score):
                        entering = []
                    elif game_over_ticks > 240 or entry_done:
                        playing = False
                    game_over_ticks += 1
                elif game.state != "game_over":
                    game_over_ticks = 0
                    entry_done = False
            elif menu is None:
                attract.update()
            if sound:
                sound.update()
                for name in game.pop_events():
                    play(name)
                    if name == "thrust_off":
                        sound.stop("thrust_on")

        if playing:
            renderer.draw(screen, game)
            if entering is not None:
                font.draw_text(screen, "ENTER YOUR INITIALS", (W // 2, 100), (255, 255, 255), center=True)
                font.draw_text(screen, "".join(entering).ljust(3, "_"), (W // 2, 120),
                               (255, 182, 0), center=True, scale=3)
        elif menu is not None:
            menu.draw(screen, pygame.time.get_ticks() // 16)
        else:
            attract.draw(screen, credits)
        display.present()


if __name__ == "__main__":
    main()
