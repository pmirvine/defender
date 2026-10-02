import pytest

import display
import settings


def test_crisp_layout_uses_whole_number_scales_and_centres():
    tw, th, x, y = display.layout(1000, 800, smooth=False)
    assert (tw, th) == (304 * 3, 256 * 3)          # 3.28 and 3.125 -> 3
    assert (x, y) == ((1000 - tw) // 2, (800 - th) // 2)


def test_smooth_layout_fills_to_aspect():
    tw, th, x, y = display.layout(1000, 800, smooth=True)
    assert th == 800 or tw == 1000
    assert abs(tw / th - 304 / 256) < 0.01


def test_window_smaller_than_native_still_scales_down():
    tw, th, _, _ = display.layout(200, 150, smooth=False)
    assert tw <= 200 and th <= 150


def test_auto_scale_fits_desktop():
    n = display.auto_scale(1920, 1080)
    assert 256 * n <= 1080 * 0.9 and 256 * (n + 1) > 1080 * 0.9
    assert display.auto_scale(100, 100) == 1


@pytest.mark.parametrize("v,want", [("auto", "auto"), ("3", 3), ("4x", 4), (2, 2), ("AUTO", "auto")])
def test_parse_scale(v, want):
    assert settings.parse_scale(v) == want


@pytest.mark.parametrize("bad", ["0", "17", "-1", "big"])
def test_parse_scale_rejects(bad):
    with pytest.raises(ValueError):
        settings.parse_scale(bad)


def test_settings_roundtrip_and_fallback(tmp_path):
    p = tmp_path / "s.json"
    s = {"scale": 5, "fullscreen": True, "smooth": True}
    settings.save(s, p)
    assert settings.load(p) == s
    p.write_text("garbage")
    assert settings.load(p) == settings.DEFAULTS
    assert settings.load(tmp_path / "none.json") == settings.DEFAULTS
