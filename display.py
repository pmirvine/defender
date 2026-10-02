"""Window management: the game draws on a 304x256 canvas that is scaled into the window here."""
import pygame

import font
import settings

W, H = 304, 256
DESKTOP_FILL = 0.9  # 'auto' scale uses at most this fraction of the desktop


def layout(win_w, win_h, smooth):
    """Where the canvas goes in a window: (target_w, target_h, x, y).

    Crisp mode only uses whole-number scales (letterboxed) so every game pixel is the same size;
    smooth mode fills the window as far as the aspect ratio allows.
    """
    fit = min(win_w / W, win_h / H)
    if not smooth and fit >= 1:
        fit = int(fit)
    tw, th = max(1, round(W * fit)), max(1, round(H * fit))
    return tw, th, (win_w - tw) // 2, (win_h - th) // 2


def auto_scale(desktop_w, desktop_h):
    return max(1, int(min(desktop_w * DESKTOP_FILL / W, desktop_h * DESKTOP_FILL / H)))


class Display:
    def __init__(self, scale="auto", fullscreen=False, smooth=False):
        self.scale, self.fullscreen, self.smooth = scale, fullscreen, smooth
        self.canvas = None
        self.toast, self.toast_ticks = "", 0
        self._apply()
        self.canvas = pygame.Surface((W, H), 0, 32)

    # -- window ------------------------------------------------------------
    def window_scale(self):
        if self.scale != "auto":
            return self.scale
        dw, dh = pygame.display.get_desktop_sizes()[0]
        return auto_scale(dw, dh)

    def _apply(self):
        if self.fullscreen:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            n = self.window_scale()
            pygame.display.set_mode((W * n, H * n), pygame.RESIZABLE)

    def current(self):
        return {"scale": self.scale, "fullscreen": self.fullscreen, "smooth": self.smooth}

    def _say(self, text):
        self.toast, self.toast_ticks = text, 90

    def change_scale(self, delta):
        """Step the window scale up/down (leaves fullscreen and 'auto')."""
        n = max(1, min(settings.MAX_SCALE, self.window_scale() + delta))
        self.scale, self.fullscreen = n, False
        self._apply()
        self._say("SCALE %dX" % n)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._apply()
        self._say("FULLSCREEN" if self.fullscreen else "WINDOWED")

    def toggle_smooth(self):
        self.smooth = not self.smooth
        self._say("SMOOTH" if self.smooth else "CRISP PIXELS")

    # -- output ------------------------------------------------------------
    def present(self):
        win = pygame.display.get_surface()
        if self.toast_ticks > 0:
            self.toast_ticks -= 1
            font.draw_text(self.canvas, self.toast, (W // 2, 0), (255, 255, 255), center=True)
        tw, th, x, y = layout(*win.get_size(), self.smooth)
        scale_fn = pygame.transform.smoothscale if self.smooth else pygame.transform.scale
        win.fill((0, 0, 0))
        win.blit(scale_fn(self.canvas, (tw, th)), (x, y))
        pygame.display.flip()
