"""Sharingan-Story (Hochformat 9:16, Cartoon-Stil mit HUD) - komplett per Code."""
import math, sys, wave, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops

W, H, FPS, DUR, K = 720, 1280, 30, 65.0, 2
OUT = "/home/user/Test/sharingan_video"
FD = "/usr/share/fonts/truetype/dejavu/"
OL = (24, 22, 34)
_fc = {}
def font(sz, bold=True):
    k = (int(sz), bold)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), int(sz))
    return _fc[k]
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(a, b, x):
    u = clamp((x - a) / (b - a)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u

class C:
    """Zeichenflaeche mit 2x Supersampling (Koordinaten logisch)."""
    def __init__(s, w=W, h=H, fill=(0, 0, 0, 0)):
        s.w, s.h = w, h; s.im = Image.new("RGBA", (int(w * K), int(h * K)), fill); s.d = ImageDraw.Draw(s.im)
    def P(s, p): return [(x * K, y * K) for x, y in p]
    def poly(s, pts, fill=None, out=None, w=6):
        p = s.P(pts)
        if fill: s.d.polygon(p, fill=fill)
        if out: s.d.line(p + [p[0]], fill=out, width=int(w * K), joint="curve")
    def ell(s, cx, cy, rx, ry, fill=None, out=None, w=6):
        s.d.ellipse([(cx - rx) * K, (cy - ry) * K, (cx + rx) * K, (cy + ry) * K], fill=fill, outline=out, width=int(w * K) if out else 0)
    def rr(s, x0, y0, x1, y1, r, fill=None, out=None, w=6):
        s.d.rounded_rectangle([x0 * K, y0 * K, x1 * K, y1 * K], radius=r * K, fill=fill, outline=out, width=int(w * K) if out else 0)
    def line(s, pts, fill, w=6):
        s.d.line(s.P(pts), fill=fill, width=int(w * K), joint="curve")
        for x, y in (pts[0], pts[-1]): s.ell(x, y, w / 2, w / 2, fill=fill)
    def text(s, x, y, t, sz, fill, anchor="mm", bold=True, stroke=0, sf=None):
        s.d.text((x * K, y * K), t, font=font(sz * K, bold), fill=fill, anchor=anchor, stroke_width=int(stroke * K), stroke_fill=sf)
    def done(s): return s.im.convert("RGBa").reduce(K).convert("RGBA")

def put(base, spr, x, y, a=1.0):
    if a < 1: spr = spr.copy(); spr.putalpha(spr.getchannel("A").point(lambda v: int(v * a)))
    base.paste(spr, (int(x), int(y)), spr)
def putc(base, spr, cx, cy, a=1.0): put(base, spr, cx - spr.width / 2, cy - spr.height / 2, a)
def rot(spr, deg): return spr.rotate(deg, expand=True, resample=Image.BICUBIC)
def scl(spr, f): return spr.resize((max(1, int(spr.width * f)), max(1, int(spr.height * f))), Image.LANCZOS)

# ======================= Sharingan / Augen =======================
def sharingan_sprite(r, ang, red=1.0):
    s = int(2 * r + 10); c = C(s, s); cx = cy = s / 2
    d0, d1, r0, r1 = (60, 30, 20), (135, 82, 48), (125, 0, 10), (240, 36, 36)
    c0 = [lerp(d0[k], r0[k], red) for k in range(3)]; c1 = [lerp(d1[k], r1[k], red) for k in range(3)]
    for i in range(14):
        u = i / 13; rr_ = r * (1 - u)
        c.ell(cx, cy, rr_, rr_, fill=tuple(int(lerp(c0[k], c1[k], u)) for k in range(3)) + (255,))
    c.ell(cx, cy, r, r, out=OL, w=max(3, r * 0.09))
    if red > 0.5:
        c.ell(cx, cy, r * 0.6, r * 0.6, out=(25, 0, 0, 255), w=max(1.5, r * 0.04))
        for k in range(3):
            a0 = ang + k * 2 * math.pi / 3; rr_ = r * 0.6; hr = r * 0.15
            hx, hy = cx + rr_ * math.cos(a0), cy + rr_ * math.sin(a0)
            c.ell(hx, hy, hr, hr, fill=(10, 0, 0, 255))
            o, i_ = [], []
            for j in range(16):
                u = j / 15; th = a0 - u * 0.95; w_ = hr * (1 - u)
                o.append((cx + (rr_ + w_ * .45) * math.cos(th), cy + (rr_ + w_ * .45) * math.sin(th)))
                i_.append((cx + (rr_ - w_ * .9) * math.cos(th), cy + (rr_ - w_ * .9) * math.sin(th)))
            c.poly(o + i_[::-1], fill=(10, 0, 0, 255))
    pr = r * (0.2 + 0.12 * (1 - red)); c.ell(cx, cy, pr, pr, fill=(8, 0, 0, 255))
    c.ell(cx - r * .33, cy - r * .42, r * .14, r * .17, fill=(255, 255, 255, 255))
    return c.done()

def eye_layer(rx, ry, op, iris, look=(0, 0)):
    pad = 14; w = int(2 * rx + 2 * pad); h = int(2 * ry + 2 * pad); ryo = max(ry * op, 3)
    c = C(w, h); c.ell(w / 2, h / 2, rx, ryo, fill=(255, 255, 255, 255)); base = c.done(); mask = base.getchannel("A")
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    lay.alpha_composite(iris, (int(w / 2 + look[0] - iris.width / 2), int(h / 2 + look[1] - iris.height / 2)))
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), mask)); base.alpha_composite(lay)
    o = C(w, h); o.ell(w / 2, h / 2, rx, ryo, out=OL, w=8); base.alpha_composite(o.done())
    return base

# ======================= Figur =======================
SKIN, HAIR, HL = (252, 238, 228), (30, 30, 40), (78, 80, 96)
EYE_A, EYE_B = (265, 700, 105, 92), (505, 690, 100, 88)
EX = {  # Brauen A, Brauen B, Mund, Augen offen, Schweiss
    "sleepy": ([(170, 610), (345, 620)], [(430, 605), (600, 600)], "line", 0.55, False),
    "shock": ([(170, 585), (345, 572)], [(430, 568), (600, 580)], "open", 1.0, True),
    "smirk": ([(170, 615), (345, 603)], [(440, 565), (600, 595)], "smirk", 0.8, False),
    "evil": ([(175, 590), (345, 632)], [(430, 630), (600, 588)], "grin", 0.62, False),
    "worry": ([(175, 632), (345, 596)], [(430, 594), (600, 630)], "wave", 0.95, True),
}
def build_face(ex):
    ba, bb, mouth, _, sweat = EX[ex]; c = C()
    c.poly([(0, 1120), (720, 1090), (720, 1280), (0, 1280)], fill=(200, 138, 76), out=OL, w=6)
    c.ell(380, 760, 335, 410, fill=SKIN, out=OL, w=8)
    c.ell(150, 880, 48, 26, fill=(250, 190, 185)); c.ell(620, 870, 48, 26, fill=(250, 190, 185))
    rnd = random.Random(5); top = []; n = 11
    for i in range(n):
        x = i * (740 / n); top.append((x + 10, rnd.randint(110, 230) + (0 if 2 < i < 8 else 70)))
        top.append((x + 10 + 740 / n * .5, rnd.randint(360, 430)))
    bangs = [(740, 720), (690, 592), (640, 520), (590, 602), (540, 500), (490, 592), (430, 480), (380, 582),
             (330, 500), (270, 592), (215, 520), (150, 612), (95, 540), (30, 650)]
    c.poly([(-10, 760)] + top + [(750, 760)] + bangs, fill=HAIR, out=OL, w=7)
    for i in range(1, n - 1, 2):
        x, y = top[2 * i]; c.line([(x, y + 25), (x + 18, y + 110)], HL, 10)
    for br in (ba, bb): c.line(br, OL, 13)
    c.line([(395, 800), (380, 832), (406, 840)], OL, 5)
    if mouth == "line": c.line([(340, 960), (440, 964)], OL, 7)
    elif mouth == "open":
        c.ell(420, 965, 105, 76, fill=(122, 32, 46), out=OL, w=8); c.ell(432, 1005, 56, 24, fill=(240, 132, 132))
    elif mouth == "smirk": c.line([(330, 955), (390, 980), (460, 965), (505, 925)], OL, 8)
    elif mouth == "grin":
        c.poly([(285, 935), (495, 935), (485, 978), (445, 1005), (390, 1015), (335, 1005), (295, 978)], fill=(255, 255, 255), out=OL, w=8)
        for x in (340, 390, 440): c.line([(x, 938), (x, 1010)], OL, 4)
    elif mouth == "wave": c.line([(320, 985), (352, 962), (386, 985), (420, 962), (455, 985)], OL, 8)
    if sweat: c.poly([(160, 765), (188, 808), (190, 832), (160, 852), (130, 832), (133, 808)], fill=(205, 232, 255), out=OL, w=5)
    c.poly([(0, 1060), (160, 1040), (330, 1092), (560, 1040), (720, 1060), (720, 1280), (0, 1280)], fill=(34, 36, 50), out=OL, w=7)
    return c.done()

def build_hand():
    c = C(360, 420)
    c.rr(70, 130, 310, 400, 70, fill=SKIN, out=OL, w=8); c.rr(135, 40, 240, 215, 50, fill=SKIN, out=OL, w=8)
    for y in (250, 295, 340): c.line([(95, y), (215, y + 6)], OL, 6)
    c.poly([(70, 240), (30, 330), (60, 400), (100, 340)], fill=(200, 138, 76), out=OL, w=6)
    return c.done()

# ======================= Hintergruende =======================
def build_bath():
    c = C(fill=(176, 186, 200, 255))
    for g in range(-1, 9): c.line([(g * 100, 0), (g * 100, H)], (128, 138, 154), 4)
    for g in range(0, 14): c.line([(0, g * 100), (W, g * 100)], (128, 138, 154), 4)
    c.rr(24, 60, 250, 330, 6, fill=(150, 196, 238), out=OL, w=7)
    c.line([(137, 60), (137, 330)], OL, 6); c.line([(24, 195), (250, 195)], OL, 6)
    c.ell(90, 130, 34, 18, fill=(255, 255, 255)); c.ell(190, 260, 38, 18, fill=(255, 255, 255))
    c.rr(20, 880, 52, 1070, 12, fill=(214, 60, 60), out=OL, w=6); c.rr(20, 800, 52, 886, 8, fill=(90, 160, 240), out=OL, w=6)
    return c.done().convert("RGB")

def build_kitchen():
    c = C(fill=(250, 226, 176, 255))
    for x in range(0, W, 60): c.rr(x, 0, x + 30, 1130, 0, fill=(246, 214, 160))
    c.rr(400, 250, 670, 570, 8, fill=(140, 200, 245), out=OL, w=8); c.line([(535, 250), (535, 570)], OL, 6); c.line([(400, 410), (670, 410)], OL, 6)
    c.ell(480, 330, 40, 18, fill=(255, 255, 255)); c.poly([(380, 240), (420, 240), (420, 600), (380, 600)], fill=(214, 70, 70), out=OL, w=6)
    c.rr(30, 420, 330, 440, 4, fill=(176, 120, 70), out=OL, w=6)
    for i, col in enumerate([(230, 90, 90), (90, 170, 230), (250, 200, 70)]): c.rr(60 + i * 90, 340, 120 + i * 90, 420, 10, fill=col, out=OL, w=6)
    c.rr(0, 1130, W, H, 0, fill=(156, 108, 72), out=OL, w=6)
    for x in range(0, W, 120): c.line([(x, 1130), (x - 40, H)], (120, 80, 50), 4)
    c.rr(-20, 860, 540, 905, 6, fill=(220, 164, 100), out=OL, w=7); c.rr(-20, 905, 540, 965, 6, fill=(180, 126, 72), out=OL, w=7)
    for x in (30, 440): c.rr(x, 965, x + 52, 1130, 6, fill=(180, 126, 72), out=OL, w=7)
    return c.done().convert("RGB")

def build_ball_bg():
    a = np.zeros((H, W + 200, 3), np.float32); y = np.linspace(0, 1, H)[:, None]
    a[:] = (np.array([110, 175, 240]) * (1 - y[..., None]) + np.array([200, 230, 255]) * y[..., None])
    c = C(W + 200, H); c.im = Image.fromarray(a.astype(np.uint8)).convert("RGBA").resize(((W + 200) * K, H * K))
    c.d = ImageDraw.Draw(c.im)
    c.ell(120, 230, 60, 60, fill=(255, 240, 150), out=OL, w=6)
    c.rr(50, 600, 870, 840, 0, fill=(230, 200, 160), out=OL, w=7)
    for x in range(90, 850, 70):
        for yy in (630, 700, 770): c.rr(x, yy, x + 36, yy + 40, 4, fill=(150, 200, 240), out=OL, w=4)
    for x, r in [(60, 90), (780, 100), (860, 80)]: c.ell(x, 600, r, r, fill=(70, 160, 80), out=OL, w=6)
    c.rr(0, 830, W + 200, H, 0, fill=(110, 182, 92))
    for i in range(-6, 8): c.line([(460 + i * 40, 850), (460 + i * 330, H)], (150, 210, 120), 6)
    c.rr(0, 800, W + 200, 830, 0, fill=(190, 150, 110), out=OL, w=5)
    for x in range(0, W + 200, 46): c.rr(x, 740, x + 30, 830, 4, fill=(205, 165, 120), out=OL, w=5)
    c.line([(0, 770), (W + 200, 770)], OL, 6)
    # Kind in der Ferne (Wurfpose)
    kx, ky = 460, 775
    c.line([(kx, ky - 40), (kx - 10, ky)], OL, 10); c.line([(kx, ky - 40), (kx + 12, ky)], OL, 10)
    c.rr(kx - 16, ky - 90, kx + 16, ky - 36, 6, fill=(230, 80, 70), out=OL, w=5); c.ell(kx, ky - 108, 16, 16, fill=SKIN, out=OL, w=5)
    c.line([(kx + 10, ky - 80), (kx + 36, ky - 118)], OL, 8)
    return c.done().convert("RGB")

def build_lotto_bg():
    c = C(fill=(252, 232, 130, 255))
    for i in range(0, 28, 2):
        a0, a1 = i * math.pi / 14, (i + 1) * math.pi / 14
        c.poly([(360, 760), (360 + 1800 * math.cos(a0), 760 + 1800 * math.sin(a0)), (360 + 1800 * math.cos(a1), 760 + 1800 * math.sin(a1))], fill=(250, 208, 90))
    return c.done().convert("RGB")

def build_alley():
    a = np.zeros((H, W, 3), np.float32); y = np.linspace(0, 1, H)[:, None, None]
    a[:] = np.array([10, 12, 30]) * (1 - y) + np.array([30, 32, 60]) * y
    c = C(); c.im = Image.fromarray(a.astype(np.uint8)).convert("RGBA").resize((W * K, H * K)); c.d = ImageDraw.Draw(c.im)
    c.poly([(0, 150), (250, 520), (250, 820), (0, 1100)], fill=(70, 44, 56), out=OL, w=6)
    c.poly([(720, 150), (470, 520), (470, 820), (720, 1100)], fill=(62, 40, 52), out=OL, w=6)
    for i in range(1, 12):
        u = i / 12
        c.line([(0, 150 + 950 * u), (250, 520 + 300 * u)], (36, 24, 34), 3); c.line([(720, 150 + 950 * u), (470, 520 + 300 * u)], (36, 24, 34), 3)
    c.rr(250, 520, 470, 820, 0, fill=(36, 48, 88))
    c.poly([(0, 1100), (250, 820), (470, 820), (720, 1100), (720, 1280), (0, 1280)], fill=(22, 24, 44), out=OL, w=6)
    c.line([(300, 840), (200, 1280)], (60, 70, 120), 8); c.line([(430, 840), (560, 1280)], (60, 70, 120), 8)
    im = c.done()
    g = C();
    for r, al in [(260, 14), (190, 22), (120, 40), (60, 90)]: g.ell(140, 430, r, r, fill=(255, 214, 130, al))
    gl = g.done().filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(14)); im.alpha_composite(gl)
    d = ImageDraw.Draw(im); d.rectangle([134, 430, 146, 900], fill=(10, 10, 16)); d.ellipse([120, 416, 160, 450], fill=(255, 240, 200))
    return im.convert("RGB")

BATH, KIT, BALLBG, LOTBG, ALLEY = build_bath(), build_kitchen(), build_ball_bg(), build_lotto_bg(), build_alley()
FACES = {k: build_face(k) for k in EX}; HAND = build_hand()

# ======================= Objekte =======================
def build_cup(tint=None):
    c = C(170, 180)
    c.ell(142, 88, 32, 36, out=OL, w=17); c.ell(142, 88, 32, 36, out=(255, 255, 255), w=9)
    c.poly([(30, 32), (130, 32), (116, 152), (46, 152)], fill=(255, 255, 255), out=OL, w=7)
    c.poly([(36, 78), (125, 78), (122, 104), (40, 104)], fill=(70, 130, 230))
    c.ell(80, 32, 50, 14, fill=(80, 52, 40), out=OL, w=6)
    im = c.done()
    if tint:
        t = Image.new("RGBA", im.size, tint); t.putalpha(ImageChops.multiply(t.getchannel("A"), im.getchannel("A"))); im = Image.alpha_composite(im, t)
    return im
CUP = build_cup(); CUP_RED = build_cup((255, 20, 20, 140))

def build_ball():
    c = C(220, 220); c.ell(110, 110, 100, 100, fill=(255, 255, 255), out=OL, w=9)
    pent = [(110 + 34 * math.cos(math.radians(a - 90)), 110 + 34 * math.sin(math.radians(a - 90))) for a in range(0, 360, 72)]
    c.poly(pent, fill=OL)
    for p in pent:
        ang = math.atan2(p[1] - 110, p[0] - 110); c.line([p, (110 + 84 * math.cos(ang), 110 + 84 * math.sin(ang))], OL, 6)
        c.ell(110 + 84 * math.cos(ang), 110 + 84 * math.sin(ang), 14, 14, fill=OL)
    return c.done()
BALL = build_ball()

def card_sprite(rank, suit, down=False, w=120, h=170):
    c = C(w, h)
    if down:
        c.rr(3, 3, w - 3, h - 3, 12, fill=(40, 70, 170), out=OL, w=5); c.rr(14, 14, w - 14, h - 14, 8, out=(230, 235, 255), w=3)
        c.text(w / 2, h / 2, "◆", 44, (230, 235, 255))
    else:
        col = (205, 30, 40) if suit in "♥♦" else (20, 20, 30)
        c.rr(3, 3, w - 3, h - 3, 12, fill=(255, 255, 255), out=OL, w=5); c.text(20, 28, rank, 32, col, "lm"); c.text(w / 2, h / 2 + 10, suit, 62, col)
    return c.done()

def build_figure():
    c = C(300, 540)
    c.poly([(60, 200), (240, 200), (275, 530), (25, 530)], fill=(14, 14, 24), out=(40, 40, 60), w=4)
    c.poly([(125, 200), (150, 270), (175, 200)], fill=(30, 30, 46))
    c.ell(150, 150, 44, 50, fill=(16, 16, 26)); c.ell(150, 108, 92, 17, fill=(10, 10, 18)); c.rr(98, 40, 202, 112, 22, fill=(10, 10, 18))
    return c.done()
FIG = build_figure()

def build_ticket():
    c = C(480, 520); nums = [[3, 11, 19, 27, 36, 44], [5, 9, 23, 31, 40, 48], [7, 14, 21, 28, 35, 42], [2, 16, 22, 33, 38, 45], [8, 13, 25, 29, 41, 47]]
    c.rr(4, 4, 476, 516, 18, fill=(253, 247, 226), out=OL, w=7); c.rr(4, 4, 476, 112, 18, fill=(212, 48, 48), out=OL, w=7)
    c.text(240, 60, "LOTTO", 66, (255, 255, 255), stroke=3, sf=OL)
    for i, row in enumerate(nums):
        for j, n in enumerate(row):
            c.rr(18 + j * 74, 140 + i * 74, 82 + j * 74, 196 + i * 74, 10, fill=(236, 228, 200), out=(150, 140, 110), w=3); c.text(50 + j * 74, 168 + i * 74, str(n), 28, (30, 30, 40))
    return c.done()
TICKET = build_ticket()
def ticket_pos(i, j): return 50 + j * 74, 168 + i * 74

# ---------- Fotos (Vorahnung) ----------
def photo_inner(kind):
    c = C(360, 330)
    if kind == "cup":
        c.rr(0, 0, 360, 330, 0, fill=(156, 108, 72)); [c.line([(x, 0), (x - 40, 330)], (120, 80, 50), 4) for x in range(60, 400, 110)]
        c.ell(190, 210, 95, 38, fill=(80, 52, 40))
        for pts in [[(110, 190), (160, 150), (170, 205)], [(210, 170), (270, 175), (240, 225)], [(130, 240), (190, 250), (170, 285)], [(250, 225), (300, 215), (290, 260)]]:
            c.poly(pts, fill=(255, 255, 255), out=OL, w=5)
        c.text(180, 60, "KLIRR!", 54, (255, 235, 90), stroke=5, sf=OL)
    elif kind == "ball":
        c.rr(0, 0, 360, 330, 0, fill=(150, 205, 245)); c.ell(150, 220, 95, 105, fill=SKIN, out=OL, w=7)
        c.poly([(70, 160), (230, 160), (200, 100), (150, 70), (100, 100)], fill=HAIR, out=OL, w=6)
        c.ell(250, 130, 80, 80, fill=(255, 255, 255), out=OL, w=7); c.poly([(250 + 22 * math.cos(math.radians(a - 90)), 130 + 22 * math.sin(math.radians(a - 90))) for a in range(0, 360, 72)], fill=OL)
        for k in range(5):
            a = k * 1.256; x, y = 100 + 40 * math.cos(a) * 2.2, 70 + 30 * math.sin(a); c.text(x, y, "★", 34, (255, 220, 40), stroke=2, sf=OL)
    elif kind == "cards":
        c.rr(0, 0, 360, 330, 0, fill=(28, 110, 72))
        for i, (r_, s_) in enumerate([("K", "♠"), ("Q", "♥"), ("J", "♦")]):
            spr = rot(card_sprite(r_, s_, w=130, h=185), 18 - i * 18); c.im.alpha_composite(spr, (int((70 + i * 85) * K - spr.width / 2), int((160) * K - spr.height / 2)))
    elif kind == "ticket":
        c.rr(0, 0, 360, 330, 0, fill=(250, 220, 110)); t = scl(TICKET, 0.62); c.im.alpha_composite(rot(t, -6), (int(30 * K), int(10 * K)))
        c.text(290, 240, "7 14 21", 24, (200, 30, 40), stroke=3, sf=(255, 255, 255))
    else:  # eye
        c.rr(0, 0, 360, 330, 0, fill=(14, 16, 36)); c.poly([(30, 165), (180, 70), (330, 165), (180, 260)], fill=(240, 235, 225), out=OL, w=8)
        c.ell(180, 165, 62, 62, fill=(50, 40, 40), out=OL, w=7); c.ell(180, 165, 22, 22, fill=(0, 0, 0)); c.ell(160, 145, 10, 10, fill=(255, 255, 255))
    return c.done()
PHOTO_CAP = {"cup": "in 2 Sekunden", "ball": "in 2 Sekunden", "cards": "ihre Karten", "ticket": "Gewinnzahlen", "eye": "wer ist das?"}
PHOTOS = {}
def build_photo(kind):
    c = C(440, 500)
    c.rr(14, 22, 428, 492, 8, fill=(0, 0, 0, 90)); c.rr(8, 8, 420, 480, 8, fill=(250, 250, 250), out=OL, w=6)
    c.rr(180, -6, 260, 34, 4, fill=(255, 214, 80, 220), out=OL, w=3)
    c.text(214, 437, PHOTO_CAP[kind], 30, (60, 60, 70), bold=False)
    im = c.done(); inner = photo_inner(kind)
    red = Image.new("RGBA", inner.size, (255, 40, 40, 38)); inner = Image.alpha_composite(inner, red)
    im.alpha_composite(inner, (34, 40)); ImageDraw.Draw(im).rectangle([34, 40, 394, 370], outline=OL, width=4)
    return im
for k_ in PHOTO_CAP: PHOTOS[k_] = build_photo(k_)

# ======================= Zeitplan =======================
SEGS = [(0, 9), (9, 15.2), (15.2, 19), (19, 25.4), (25.4, 28), (28, 35.5), (35.5, 40), (40, 45.8), (45.8, 48), (48, 56), (56, 65)]
PH = [(9.6, 11.4, "cup"), (19.5, 21.3, "ball"), (28.2, 29.6, "cards"), (40.6, 42.2, "ticket"), (48.4, 50.0, "eye")]
CH = [(0, 100), (11.8, 100), (12.6, 94), (23, 94), (24, 88), (33, 88), (34, 72), (43, 72), (44.5, 55), (52, 55), (53, 35), (60, 35), (61.5, 18)]
GE = [(0, 200), (33.2, 200), (34.2, 1400), (44.2, 1400), (45.2, 5200)]
VE = [(0, 0), (34, 0), (35, 15), (44.5, 15), (45.5, 45), (50, 45), (52, 80), (60, 80), (62, 100)]
def keyval(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t < t1: return lerp(v0, v1, sstep(t0, t1, t))
    return keys[-1][1]
CAPS = [
 (0.3, 3.0, "Heute morgen bin ich aufgewacht ..."), (3.0, 5.4, "und mein Auge fühlte sich komisch an."),
 (5.4, 8.9, "Ich hab ein *SHARINGAN* bekommen."),
 (9.2, 11.4, "Meine Tasse stand am Tischrand ..."), (11.5, 13.6, "Ich sah *voraus*, wie sie runterfällt"), (13.6, 15.1, "und fing sie *vorher* auf."),
 (15.4, 19.0, "Mein Sharingan sieht die *Zukunft*."),
 (19.2, 21.4, "Auf dem Schulhof flog ein Ball auf mich zu ..."), (21.6, 25.2, "Ich wusste es *zwei* *Sekunden* vorher."),
 (25.6, 28.0, "Ausweichen war *kinderleicht*."),
 (28.2, 31.0, "Beim Pokern sah ich *alle* *Karten* vorher."), (31.2, 35.4, "Aus 200 € wurden *1.400* *€*."),
 (35.8, 39.8, "Das Auge macht mich *unschlagbar*."),
 (40.1, 43.4, "Dann kaufte ich ein *Lotterielos* ..."), (43.5, 45.6, "und gewann *5.200* *€*."), (46.0, 48.0, "Alles lief *perfekt*."),
 (48.3, 52.0, "Doch jemand merkt, dass ich zu viel *Glück* habe ..."), (52.2, 55.9, "Er beobachtet mich *schon* *seit* *Tagen*."),
 (56.2, 60.2, "Mein Chakra ist fast *leer* ..."), (60.3, 64.6, "Und der Verdacht steigt auf *100%*."),
]
SHAKES = [(12.2, .3, 12), (23.2, .35, 16), (30.0, .15, 6), (43.4, .3, 8), (50.0, .3, 8), (60.2, .4, 10)]

# ======================= Szenen =======================
def seg_of(t):
    for i, (a, b) in enumerate(SEGS):
        if a <= t < b: return i, a
    return len(SEGS) - 1, SEGS[-1][0]

def scene_face(t, ex):
    base = BATH.copy(); put(base, FACES[ex], 0, 0)
    ba, bb, mouth, op, sweat = EX[ex]
    t_red = 4.6; red = 0.0 if t < t_red else 1.0
    spin = t * 3.4 + (3.0 * max(0, t - 56)) * 0
    pulse = math.exp(-(t - t_red) * 7) if t >= t_red else 0
    ax, ay, arx, ary = EYE_A; bx, by, brx, bry = EYE_B
    openA = op if not (t < 4.6) else 0.55
    if 4.6 <= t < 5.0: openA = lerp(0.55, 1.0, sstep(4.6, 4.9, t)) if ex == "shock" else openA
    look = (math.sin(t * 1.3) * 4, 0)
    ia = sharingan_sprite(int(58 * (1 + 0.3 * pulse)), spin, red); ib = sharingan_sprite(52, 0, 0)
    blink = 0.12 if (int(t * 10) % 37 == 0 and ex not in ("shock",)) else 1.0
    putc(base, eye_layer(arx, ary, openA * blink, ia, look), ax, ay); putc(base, eye_layer(brx, bry, op * blink, ib, look), bx, by)
    if t < 6.4:   # Auge reiben
        k = 1 - sstep(5.4, 6.4, t); dx, dy = 9 * math.cos(t * 9) * k, 6 * math.sin(t * 9) * k - 40 * (1 - k)
        put(base, scl(HAND, 0.8), 52 + dx - 60 * (1 - k), 772 + dy + 240 * (1 - k))
    if 4.6 <= t < 5.2:   # Strahlen
        c = C(); a = sstep(4.6, 4.7, t) * (1 - sstep(4.8, 5.2, t))
        for i in range(14):
            an = i * 2 * math.pi / 14; c.line([(ax + 120 * math.cos(an), ay + 120 * math.sin(an)), (ax + (170 + 40 * pulse) * math.cos(an), ay + (170 + 40 * pulse) * math.sin(an))], (255, 235, 120, int(255 * a)), 8)
        o = c.done(); put(base, o, 0, 0)
    return base

def scene_kitchen(t):
    base = KIT.copy(); tf, tc = 11.4, 12.2
    if 10.2 <= t < 12.4:
        a = sstep(10.2, 10.6, t) * (1 - sstep(12.0, 12.4, t)); c = C()
        for i in range(0, 30, 2):
            u0, u1 = i / 30, (i + 1) / 30; c.line([(480 + 120 * u0, 790 + 320 * u0 * u0), (480 + 120 * u1, 790 + 320 * u1 * u1)], (255, 50, 50, int(230 * a)), 9)
        put(base, c.done(), 0, 0); putc(base, rot(CUP_RED, 40), 600, 1100, a * 0.9)
    if t < tf: x, y, ang = 480, 790, (5 * math.sin((t - 10.4) * 40) * sstep(10.4, 10.6, t) if t > 10.4 else 0)
    elif t < tc: dt = t - tf; x, y, ang = 480 + 70 * dt / 0.8, 790 + 0.5 * 656 * dt * dt, -(20 + 300 * dt)
    else: x, y, ang = 550, 1000 + 7 * math.exp(-(t - tc) * 6) * math.sin((t - tc) * 25), 0
    putc(base, rot(CUP, ang), x, y)
    if t > 11.75:
        e = sstep(11.75, tc, t); hx = lerp(790, 550, e); c = C()
        c.ell(hx, 1090, 64, 30, fill=SKIN, out=OL, w=6)
        for k in range(4): c.rr(hx - 62 + k * 30, 1040 + (1 if k in (1, 2) else 8), hx - 36 + k * 30, 1090, 12, fill=SKIN, out=OL, w=5)
        put(base, c.done(), 0, 0)
    if tc <= t < tc + 0.7:
        a = 1 - (t - tc) / 0.7; c = C()
        for i in range(16):
            an = i * math.pi * 2 / 16; r0 = 120 + 80 * (t - tc); c.line([(550 + r0 * math.cos(an), 1000 + r0 * math.sin(an)), (550 + (r0 + 60) * math.cos(an), 1000 + (r0 + 60) * math.sin(an))], (255, 255, 255, int(255 * a)), 8)
        put(base, c.done(), 0, 0)
    return base

def scene_ball(t):
    t_throw, t_hit = 21.2, 23.4
    cs = 280 * sstep(22.7, 23.1, t); ox = 100 - int(cs * 0.3)
    base = BALLBG.crop((ox, 0, ox + W, H)).copy()
    if 20.7 <= t < 23.0:
        a = sstep(20.7, 21.0, t) * (1 - sstep(22.6, 23.0, t)); r = 150 + 12 * math.sin(t * 12); c = C()
        c.ell(360 + cs, 640, r, r, out=(255, 40, 40, int(230 * a)), w=8); c.line([(360 + cs - r - 30, 640), (360 + cs + r + 30, 640)], (255, 40, 40, int(230 * a)), 6); c.line([(360 + cs, 640 - r - 30), (360 + cs, 640 + r + 30)], (255, 40, 40, int(230 * a)), 6)
        put(base, c.done(), 0, 0)
    if t >= t_throw:
        u = clamp((t - t_throw) / (t_hit - t_throw))
        if t < t_hit: rr_ = 14 + 250 * u ** 2.2; bx = 460 + (360 - 460) * u + cs; by = 700 - 60 * u * u
        else: rr_ = 264; bx = 360 + cs + (t - t_hit) * 1800; by = 640
        if bx - rr_ < W + 50: putc(base, scl(rot(BALL, t * 400), rr_ * 2 / 220), bx, by)
    if 22.3 <= t < 23.7:
        a = sstep(22.3, 22.7, t) * (1 - sstep(23.3, 23.7, t)); c = C()
        for i in range(26):
            an = i * math.pi * 2 / 26 + 0.1; c.line([(360 + 260 * math.cos(an), 640 + 260 * math.sin(an)), (360 + 700 * math.cos(an), 640 + 700 * math.sin(an))], (255, 255, 255, int(200 * a)), 5)
        put(base, c.done(), 0, 0)
    return base

def scene_cards(t):
    base = LOT_TABLE.copy(); c = C()
    flips = [(29.7, 1), (30.0, 2), (30.3, 3), (31.2, 4)]
    opp = [("K", "♠", "9", "♦"), ("Q", "♥", "2", "♣"), ("J", "♦", "10", "♠")]
    for i, x in enumerate((140, 360, 580)):
        c.ell(x, 300, 46, 46, fill=[(70, 70, 90), (90, 60, 70), (60, 80, 70)][i], out=OL, w=6)
        c.poly([(x - 90, 400), (x - 70, 350), (x + 70, 350), (x + 90, 400)], fill=[(70, 70, 90), (90, 60, 70), (60, 80, 70)][i], out=OL, w=6)
    put(base, c.done(), 0, 0)
    for i, x in enumerate((140, 360, 580)):
        fl = flips[i][0]
        for j in range(2):
            px = x + (-42 if j == 0 else 42); py = 470
            u = clamp((t - fl) / 0.35); face = u > 0.5; wsc = max(0.04, abs(math.cos(math.pi * u))) if 0 < u < 1 else 1
            if u >= 1 or u <= 0: wsc = 1
            r_, s_ = opp[i][2 * j], opp[i][2 * j + 1]
            sp = card_sprite(r_, s_, down=not face, w=110, h=156); sp = sp.resize((max(2, int(sp.width * wsc)), sp.height))
            if t >= fl + 0.1:
                g = C(130, 176); g.rr(3, 3, 127, 173, 14, out=(255, 40, 40, 200), w=6); sp2 = g.done(); putc(base, sp2, px, py)
            putc(base, sp, px, py)
    for i, (r_, s_) in enumerate([("A", "♦"), ("A", "♣"), ("K", "♥"), ("7", "♠"), ("3", "♦")]): putc(base, card_sprite(r_, s_, w=96, h=136), 360 + (i - 2) * 104, 680)
    ch = clamp((t - 32.4) / 0.8); chy = lerp(815, 1010, sstep(0, 1, ch)); cc = C()
    for k in range(6): cc.ell(360 + (k % 3 - 1) * 24, chy - k * 7, 36, 14, fill=[(220, 50, 50), (60, 120, 230), (240, 200, 60)][k % 3], out=OL, w=4)
    put(base, cc.done(), 0, 0)
    for i, (r_, s_) in enumerate([("A", "♠"), ("A", "♥")]):
        u = clamp((t - 31.2) / 0.35); face = u > 0.5; wsc = max(0.04, abs(math.cos(math.pi * u))) if 0 < u < 1 else 1
        sp = card_sprite(r_, s_, down=not face, w=130, h=185); sp = sp.resize((max(2, int(sp.width * wsc)), sp.height))
        putc(base, rot(sp, 8 - i * 16), 330 + i * 70, 960)
    if 33.2 <= t < 34.8:
        u = (t - 33.2) / 1.6; d = ImageDraw.Draw(base); d.text((360, 780 - 80 * u), "+1.200 €", font=font(66), fill=(110, 240, 140), anchor="mm", stroke_width=6, stroke_fill=OL)
    return base

def scene_lotto(t):
    base = LOTBG.copy(); rise = 1 - sstep(40.0, 40.6, t); cx, cy = 360, 880 + 400 * rise; s = 0.84
    putc(base, scl(rot(TICKET, -3), s), cx, cy)
    c = C()
    for j in range(6):
        ta = 41.3 + 0.3 * j
        if t >= ta:
            x, y = ticket_pos(2, j); px = cx + (x - 240) * s - 3 * (y - 260) * 0.05; py = cy + (y - 260) * s
            u = clamp((t - ta) / 0.2); c.ell(px, py, 26 * s * (0.5 + 0.5 * u) + 4, 26 * s * (0.5 + 0.5 * u) + 4, fill=(230, 40, 40, 150), out=(230, 40, 40, 255), w=4)
    put(base, c.done(), 0, 0)
    if t >= 43.4:
        u = sstep(43.4, 43.7, t); sp = c2 = C(520, 130); sp.rr(6, 6, 514, 124, 18, out=(40, 180, 90), w=10); sp.text(260, 66, "GEWONNEN!", 72, (40, 180, 90), stroke=2, sf=(255, 255, 255))
        putc(base, rot(scl(sp.done(), 0.6 + 0.4 * u), -12), 360, 880, u)
        rng = random.Random(4); cf = C()
        for i in range(70):
            x0 = rng.uniform(80, 640); v = rng.uniform(300, 700); dx = rng.uniform(-30, 30); tt = t - 43.4 - rng.uniform(0, 0.4)
            if tt > 0:
                px, py = x0 + dx * tt * 10, 700 - v * tt + 600 * tt * tt
                cf.rr(px - 8, py - 6, px + 8, py + 6, 2, fill=[(255, 60, 90), (60, 160, 255), (255, 220, 40), (80, 220, 120)][i % 4])
        put(base, cf.done(), 0, 0)
    return base

def scene_obs(t):
    base = ALLEY.copy(); u = sstep(48, 55, t); s = lerp(0.55, 1.0, u)
    fig = scl(FIG, s); put(base, fig, 360 - fig.width / 2, 830 - fig.height)
    g = C(); gy = 830 - fig.height + 150 * s; pulse = 0.7 + 0.3 * math.sin(t * 6)
    for dx in (-20, 20):
        for r, al in [(22, 40), (14, 100), (8, 255)]: g.ell(360 + dx * s, gy, r * s, r * s * .7, fill=(255, 235, 130, int(al * pulse)))
    put(base, g.done(), 0, 0)
    return base

# ======================= Overlays =======================
LOT_TABLE = None
def _table():
    c = C(fill=(110, 70, 40, 255)); c.rr(24, 200, 696, 1090, 40, fill=(30, 112, 74), out=OL, w=8); c.ell(360, 640, 300, 320, fill=(38, 126, 84))
    return c.done().convert("RGB")
LOT_TABLE = _table()

def draw_hud(img, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); bw = (W - 24 - 20) / 3
    rows = [("CHAKRA", CH, lambda v: f"{int(round(v))}%", (120, 190, 255)), ("GELD", GE, lambda v: f"{int(round(v)):,}".replace(",", ".") + " €", (110, 235, 140)), ("VERDACHT", VE, lambda v: f"{int(round(v))}%", (255, 90, 90))]
    for i, (lab, keys, fmt, fc) in enumerate(rows):
        v = keyval(keys, t); chg = abs(v - keyval(keys, t - 0.4)) > 0.5
        x0 = 12 + i * (bw + 10); y0 = 100
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + 84], 10, fill=(34, 36, 42, 225) if not (i == 2 and v > 60) else (80, 20, 24, 235))
        x = x0 + bw / 2 - sum(font(14).getlength(ch) + 3 for ch in lab) / 2
        for ch in lab: d.text((x, y0 + 22), ch, font=font(14), fill=(165, 170, 182), anchor="lm"); x += font(14).getlength(ch) + 3
        d.text((x0 + bw / 2, y0 + 58), fmt(v), font=font(38), fill=fc if chg else (255, 255, 255), anchor="mm")
    img.paste(ov, (0, 0), ov)

def draw_caption(img, t):
    cur = None
    for t0, t1, tx in CAPS:
        if t0 <= t < t1: cur = (t0, t1, tx)
    if not cur: return
    t0, t1, text = cur; F = font(54); words = text.split(); n = len(words)
    rate = min(0.32, 0.7 * (t1 - t0) / n); cnt = min(n, int((t - t0) / rate) + 1)
    sp = F.getlength(" "); lines = []; row = []; rw = 0
    for i, wd in enumerate(words):
        cl = wd.replace("*", ""); wl = F.getlength(cl)
        if row and rw + sp + wl > 640: lines.append((row, rw)); row = []; rw = 0
        rw += (sp if row else 0) + wl; row.append((i, cl, wd.startswith("*"), wl))
    lines.append((row, rw)); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); y = 1115 - (len(lines) - 1) * 36
    for row, rw in lines:
        x = (W - rw) / 2
        for i, cl, hi, wl in row:
            if i < cnt:
                col = (240, 50, 50) if "SHARINGAN" in cl else ((255, 214, 60) if hi else (255, 255, 255)); age = t - (t0 + i * rate)
                if i == cnt - 1 and age < 0.14:
                    f = 1 + 0.35 * (1 - age / 0.14); tmp = Image.new("RGBA", (int(wl) + 60, 110), (0, 0, 0, 0)); ImageDraw.Draw(tmp).text((tmp.width / 2, 55), cl, font=F, fill=col, anchor="mm", stroke_width=8, stroke_fill=(0, 0, 0))
                    tmp = scl(tmp, f); ov.paste(tmp, (int(x + wl / 2 - tmp.width / 2), int(y - tmp.height / 2)), tmp)
                else: d.text((x, y), cl, font=F, fill=col, anchor="lm", stroke_width=8, stroke_fill=(0, 0, 0))
            x += wl + sp
        y += 72
    fa = min(1.0, (t1 - t) / 0.15)
    if fa < 1: ov.putalpha(ov.getchannel("A").point(lambda v: int(v * fa)))
    img.paste(ov, (0, 0), ov)

def draw_photo(img, t):
    for a, b, kind in PH:
        if a <= t < b:
            e = sstep(0, 0.28, t - a) * (1 - sstep(0, 0.22, t - (b - 0.22)))
            pop = 1 + 0.15 * math.sin(clamp((t - a) / 0.28) * math.pi); s = 0.85 * e * pop
            if s > 0.02: putc(img, rot(scl(PHOTOS[kind], s), -5 + 3 * math.sin(t * 3)), 360, 480)
            return True
    return False

VIG = None
def draw_vision(img, t):
    on = None
    for a, b, k in PH:
        if a - 0.1 <= t < b + 0.5: on = (a, b)
    if on is None: return
    f = sstep(on[0] - 0.1, on[0] + 0.2, t) * (1 - sstep(on[1], on[1] + 0.5, t))
    yy, xx = np.mgrid[0:H:4, 0:W:4]; r = (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    al = (np.clip(r, 0, 1) ** 1.3 * 190 * f * (0.8 + 0.2 * math.sin(t * 8))).astype(np.uint8)
    ov = np.zeros((al.shape[0], al.shape[1], 4), np.uint8); ov[..., 0] = 220; ov[..., 3] = al
    ov = Image.fromarray(ov).resize((W, H), Image.BILINEAR); img.paste(ov, (0, 0), ov)
    putc(img, sharingan_sprite(34, t * 6), 645, 245, f)

def zoom(img, z):
    if z <= 1.001: return img
    w, h = W / z, H / z; x0, y0 = (W - w) / 2, (H - h) / 2
    return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))

def frame(t):
    si, s0 = seg_of(t)
    if si == 0: sc = scene_face(t, "sleepy" if t < 4.6 else "shock")
    elif si == 1: sc = scene_kitchen(t)
    elif si in (2, 4): sc = scene_face(t, "smirk")
    elif si == 3: sc = scene_ball(t)
    elif si == 5: sc = scene_cards(t)
    elif si == 6: sc = scene_face(t, "evil")
    elif si == 7: sc = scene_lotto(t)
    elif si == 8: sc = scene_face(t, "shock")
    elif si == 9: sc = scene_obs(t)
    else: sc = scene_face(t, "worry")
    dt = t - s0
    if si in (0, 2, 4, 6, 8, 10) and dt < 0.35 and t > 0.1: sc = zoom(sc, 1 + 0.12 * (1 - sstep(0, 0.35, dt)))
    for a, d_, amp in SHAKES:
        if 0 <= t - a < d_:
            k = amp * (1 - (t - a) / d_); sc = ImageChops.offset(sc, int(k * math.sin(t * 95)), int(k * math.cos(t * 83)))
    draw_vision(sc, t); draw_photo(sc, t)
    if si == 9:  # rote Warnung
        pass
    if t >= 60.2:
        k = sstep(60.2, 61.0, t) * 0.55; dim = Image.new("RGB", (W, H), (0, 0, 0)); sc = Image.blend(sc, dim, k)
        d = ImageDraw.Draw(sc)
        if t >= 61.2:
            d.text((W / 2, 520), "TEIL 2?", font=font(110), fill=(240, 50, 50), anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0))
        if t >= 62.6: d.text((W / 2, 640), "Folge für die Fortsetzung", font=font(34), fill=(255, 255, 255), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))
    draw_hud(sc, t); draw_caption(sc, t)
    for st, _ in SEGS[1:]:
        if 0 <= t - st < 0.18:
            fl = Image.new("RGB", (W, H), (255, 255, 255)); sc = Image.blend(sc, fl, 0.75 * (1 - (t - st) / 0.18))
    if t < 0.5: sc = Image.blend(Image.new("RGB", (W, H)), sc, t / 0.5)
    if t > DUR - 0.6: sc = Image.blend(Image.new("RGB", (W, H)), sc, clamp((DUR - t) / 0.6))
    return sc

# ======================= Audio =======================
def make_audio(path):
    sr = 44100; N = int(DUR * sr); t = np.arange(N) / sr; rng = np.random.default_rng(2); mix = np.zeros(N)
    def add(t0, sig, g=1.0):
        i0 = int(t0 * sr)
        if i0 < N: i1 = min(N, i0 + len(sig)); mix[i0:i1] += sig[:i1 - i0] * g
    def tt(d): return np.arange(int(d * sr)) / sr
    for f, g in [(110, .05), (130.8, .04), (164.8, .04), (220, .02)]: mix += np.sin(2 * np.pi * f * t) * g * (0.7 + 0.3 * np.sin(2 * np.pi * 0.1 * t))
    x = tt(0.28)
    for kt in np.arange(9.0, 60.5, 0.5):
        f = 48 + 90 * np.exp(-x * 30); add(kt, np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-x * 12), 0.38)
        add(kt + 0.25, rng.standard_normal(len(tt(0.04))) * np.exp(-tt(0.04) * 90), 0.05)
    def whoosh(t0, d=0.45, g=0.2):
        x = tt(d); env = np.sin(np.pi * x / d) ** 2; n = rng.standard_normal(len(x)); k = np.ones(12) / 12; add(t0, np.convolve(n, k, "same") * env, g)
    def ding(t0, f, g=0.18): x = tt(0.7); add(t0, (np.sin(2 * np.pi * f * x) + 0.4 * np.sin(2 * np.pi * 2 * f * x)) * np.exp(-x * 6), g)
    def thump(t0, f=70, g=0.7): x = tt(0.5); add(t0, np.sin(2 * np.pi * f * x) * np.exp(-x * 9) + rng.standard_normal(len(x)) * np.exp(-x * 40) * 0.4, g)
    for st, _ in SEGS[1:]: whoosh(st - 0.05)
    x = tt(0.7); add(4.6, np.sin(2 * np.pi * np.cumsum(600 + 1800 * x / 0.7) / sr) * np.exp(-x * 4), 0.2)
    for a, b, _ in PH: ding(a, 1318); ding(a + 0.1, 1760, 0.1)
    thump(12.2); whoosh(22.6, 0.9, 0.35); thump(23.3, 55, 0.5)
    for ft in (29.7, 30.0, 30.3, 31.2): add(ft, rng.standard_normal(len(tt(0.03))) * np.exp(-tt(0.03) * 100), 0.3)
    for i, f in enumerate((988, 1319, 1568, 1976)): ding(33.2 + i * 0.09, f, 0.2)
    for i, f in enumerate((523, 659, 784, 1047, 1319)): ding(43.4 + i * 0.07, f, 0.2)
    thump(50.0, 45, 0.9)
    for ht in np.arange(48.0, 62.0, 0.9): thump(ht, 55, 0.35); thump(ht + 0.25, 50, 0.2)
    x = tt(5); add(60.2, (np.sin(2 * np.pi * 41 * x) + 0.5 * np.sin(2 * np.pi * 58 * x)) * np.exp(-x * 0.7), 0.5)
    mix *= np.minimum(1, t / 1.0) * np.minimum(1, (DUR - t) / 1.5); mix = mix / np.abs(mix).max() * 0.85
    s = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(np.column_stack([s, s]).ravel().tobytes())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        ts = [float(a) for a in sys.argv[2:]] or [3, 5.2, 10.5, 11.9, 12.6, 20.2, 23.2, 29.5, 31.5, 33.5, 41.8, 44.0, 49, 54, 59, 63]
        ims = [frame(x).resize((360, 640)) for x in ts]; cols = 4; rows = (len(ims) + cols - 1) // cols
        sh = Image.new("RGB", (360 * cols, 640 * rows))
        for i, im in enumerate(ims): sh.paste(im, ((i % cols) * 360, (i // cols) * 640))
        sh.save(f"{OUT}/sheet_v2.png"); sys.exit()
    make_audio(f"{OUT}/audio2.wav")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", f"{OUT}/audio2.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "medium",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", f"{OUT}/sharingan_story.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0: print(i, flush=True)
    p.stdin.close(); p.wait(); print("fertig")
