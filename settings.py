"""Persistent display settings (~/.defender_settings.json)."""
import json
from pathlib import Path

PATH = Path.home() / ".defender_settings.json"
MAX_SCALE = 16
DEFAULTS = {"scale": "auto", "fullscreen": False, "smooth": False}


def parse_scale(value):
    """'auto' or an integer 1..MAX_SCALE (also accepts '3x'). Raises ValueError otherwise."""
    if isinstance(value, str):
        v = value.strip().lower().rstrip("x")
        if v == "auto":
            return "auto"
        value = v
    n = int(value)
    if not 1 <= n <= MAX_SCALE:
        raise ValueError("scale must be 'auto' or 1-%d" % MAX_SCALE)
    return n


def load(path=PATH):
    s = dict(DEFAULTS)
    try:
        data = json.loads(Path(path).read_text())
        s["scale"] = parse_scale(data.get("scale", "auto"))
        s["fullscreen"] = bool(data.get("fullscreen", False))
        s["smooth"] = bool(data.get("smooth", False))
    except (OSError, ValueError, TypeError, AttributeError):
        return dict(DEFAULTS)
    return s


def save(settings, path=PATH):
    try:
        Path(path).write_text(json.dumps(settings, indent=1))
    except OSError:
        pass
