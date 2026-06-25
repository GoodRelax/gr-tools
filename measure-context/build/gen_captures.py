# -*- coding: utf-8 -*-
"""Generate two dummy in-vehicle HMI screenshots with Pillow.

capture1.png : LKAS ACTIVE status screen.
capture2.png : Lane departure warning screen.
Both are forced to exactly 1280x720 px (Image.new guarantees the canvas size);
the actual on-disk dimensions are re-read and returned for verification.

Labels are ASCII only to avoid font-substitution issues; no real imagery is used.
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720

BG = (18, 22, 30)
PANEL = (30, 36, 48)
PANEL2 = (24, 29, 39)
WHITE = (236, 239, 244)
GREEN = (60, 210, 120)
AMBER = (245, 182, 40)
RED = (235, 72, 60)
GREY = (130, 140, 156)
ROAD = (44, 50, 62)
LINE = (232, 235, 240)
BLUE = (72, 132, 236)


def _font(size, bold=False):
    for p in (
        (r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        r"C:\Windows\Fonts\segoeui.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _rrect(d, box, radius, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _dashed(d, p0, p1, fill, width=3, dash=18, gap=14):
    x0, y0 = p0
    x1, y1 = p1
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    if length == 0:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    pos = 0.0
    while pos < length:
        seg = min(dash, length - pos)
        a = (x0 + ux * pos, y0 + uy * pos)
        b = (x0 + ux * (pos + seg), y0 + uy * (pos + seg))
        d.line([a, b], fill=fill, width=width)
        pos += dash + gap


def _car(d, cx, top, w=120, h=170, color=BLUE):
    body = [cx - w / 2, top, cx + w / 2, top + h]
    _rrect(d, body, radius=26, fill=color)
    # windshield + rear window (top view)
    _rrect(d, [cx - w / 2 + 16, top + 22, cx + w / 2 - 16, top + 64], radius=10, fill=(20, 26, 38))
    _rrect(d, [cx - w / 2 + 16, top + h - 70, cx + w / 2 - 16, top + h - 26], radius=10, fill=(20, 26, 38))


def _lane(d, box, drift, left_alert=False):
    x, y, w, h = box
    cx = x + w / 2.0
    bl = (x + w * 0.05, y + h)
    br = (x + w * 0.95, y + h)
    tl = (cx - w * 0.09, y + h * 0.12)
    tr = (cx + w * 0.09, y + h * 0.12)
    d.polygon([bl, br, tr, tl], fill=ROAD)
    # side lines
    d.line([bl, tl], fill=(RED if left_alert else LINE), width=(12 if left_alert else 6))
    d.line([br, tr], fill=LINE, width=6)
    # centre dashed line
    _dashed(d, (x + w * 0.5, y + h), ((tl[0] + tr[0]) / 2, y + h * 0.12), fill=(210, 210, 120), width=4)
    # car near the bottom, offset by drift
    car_cx = cx + drift * (w * 0.30)
    _car(d, car_cx, y + h - 230)


def _panel_row(d, x, y, label, value, value_color, fsmall, fbig):
    d.text((x, y), label, font=fsmall, fill=GREY)
    d.text((x, y + 26), value, font=fbig, fill=value_color)


def _build_capture1(path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = _font(34, bold=True)
    f_big = _font(46, bold=True)
    f_mid = _font(28, bold=True)
    f_small = _font(20)
    # header
    d.rectangle([0, 0, W, 84], fill=(14, 17, 25))
    d.text((40, 24), "LKAS  Lane Keeping Assist System", font=f_title, fill=WHITE)
    d.ellipse([W - 70, 30, W - 46, 54], fill=GREEN)
    # lane view
    _rrect(d, [40, 110, 760, 680], 16, fill=PANEL2, outline=(60, 70, 86), width=2)
    _lane(d, (60, 130, 680, 530), drift=0.0, left_alert=False)
    d.text((70, 140), "LANE TRACKING", font=f_small, fill=GREEN)
    # status panel
    _rrect(d, [800, 110, 1240, 680], 16, fill=PANEL, outline=(60, 70, 86), width=2)
    d.text((830, 132), "SYSTEM STATUS", font=f_mid, fill=WHITE)
    d.line([830, 178, 1210, 178], fill=(70, 80, 96), width=2)
    _panel_row(d, 830, 210, "STATUS", "ACTIVE", GREEN, f_small, f_big)
    _panel_row(d, 830, 320, "VEHICLE SPEED", "112 km/h", WHITE, f_small, f_big)
    _panel_row(d, 830, 430, "STEERING ASSIST", "ON", GREEN, f_small, f_big)
    _panel_row(d, 830, 540, "LANE DETECTION", "BOTH LINES", WHITE, f_small, f_big)
    # indicator dots
    for i, col in enumerate([GREEN, GREEN, GREY]):
        d.ellipse([1130 + i * 34, 214, 1154 + i * 34, 238], fill=col)
    img.save(path)


def _build_capture2(path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = _font(34, bold=True)
    f_big = _font(46, bold=True)
    f_mid = _font(28, bold=True)
    f_small = _font(20)
    f_warn = _font(40, bold=True)
    # header (amber accent)
    d.rectangle([0, 0, W, 84], fill=(34, 26, 10))
    d.text((40, 24), "LKAS  Lane Keeping Assist System", font=f_title, fill=WHITE)
    d.ellipse([W - 70, 30, W - 46, 54], fill=AMBER)
    # lane view with car drifting across the left line
    _rrect(d, [40, 110, 760, 680], 16, fill=PANEL2, outline=(60, 70, 86), width=2)
    _lane(d, (60, 130, 680, 530), drift=-0.62, left_alert=True)
    # warning triangle
    tri_cx, tri_cy = 400, 250
    d.polygon([(tri_cx, tri_cy - 60), (tri_cx - 64, tri_cy + 52), (tri_cx + 64, tri_cy + 52)],
              fill=AMBER)
    d.text((tri_cx, tri_cy + 2), "!", font=f_warn, fill=(20, 20, 20), anchor="mm")
    # status panel
    _rrect(d, [800, 110, 1240, 680], 16, fill=PANEL, outline=(90, 70, 30), width=2)
    d.text((830, 132), "SYSTEM STATUS", font=f_mid, fill=WHITE)
    d.line([830, 178, 1210, 178], fill=(70, 80, 96), width=2)
    _panel_row(d, 830, 210, "STATUS", "WARNING", AMBER, f_small, f_big)
    d.text((830, 300), "LANE DEPARTURE WARNING", font=f_mid, fill=AMBER)
    _panel_row(d, 830, 360, "VEHICLE SPEED", "118 km/h", WHITE, f_small, f_big)
    _panel_row(d, 830, 470, "AUDIBLE ALERT", "ON", RED, f_small, f_big)
    _panel_row(d, 830, 580, "DRIFT DIRECTION", "LEFT", AMBER, f_small, f_big)
    img.save(path)


def make_captures(out_dir):
    p1 = os.path.join(out_dir, "capture1.png")
    p2 = os.path.join(out_dir, "capture2.png")
    _build_capture1(p1)
    _build_capture2(p2)
    sizes = {}
    for p in (p1, p2):
        with Image.open(p) as im:
            sizes[os.path.basename(p)] = im.size  # (width, height) read back from disk
    return sizes


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "samples")
    out = os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    sizes = make_captures(out)
    for name, (w, h) in sizes.items():
        print("%s : %dx%d  %s" % (name, w, h, "OK" if (w, h) == (1280, 720) else "MISMATCH"))
