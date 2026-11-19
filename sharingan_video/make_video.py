import math, sys, wave, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1280, 720, 30, 65.0
OUT = "/home/user/Test/sharingan_video"
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=False): return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sstep(a, b, x):
    u = clamp((x - a) / (b - a)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u

# ---------- Weltzeit (Zeitlupe) ----------
def speed(t):
    if t < 24: return 1.0
    if t < 27: return lerp(1.0, 0.1, sstep(24, 27, t))
    if t < 49: return 0.1
    if t < 53: return lerp(0.1, 1.0, sstep(49, 53, t))
    return 1.0
_tw = np.cumsum([speed(i / FPS) / FPS for i in range(int(DUR * FPS) + 2)])
def tw(t): return _tw[min(int(t * FPS), len(_tw) - 1)]

# ---------- Hintergrund: Stadt bei Nacht ----------
def make_bg():
    rnd = random.Random(7)
    y = np.linspace(0, 1, H)[:, None, None]
    sky = np.array([8, 10, 24]) * (1 - y) + np.array([40, 28, 50]) * y
    img = np.tile(sky, (1, W, 1)).astype(np.float32)
    im = Image.fromarray(img.astype(np.uint8)); d = ImageDraw.Draw(im)
    x = -20
    while x < W:
        bw = rnd.randint(70, 160); bh = rnd.randint(150, 400)
        top = 500 - bh
        d.rectangle([x, top, x + bw, 500], fill=(14 + rnd.randint(0, 8), 14, 26))
        for wx in range(x + 8, x + bw - 10, 18):
            for wy in range(top + 10, 490, 24):
                if rnd.random() < 0.38:
                    c = rnd.choice([(255, 214, 120), (255, 190, 90), (150, 200, 255)])
                    d.rectangle([wx, wy, wx + 8, wy + 12], fill=c)
        x += bw + rnd.randint(0, 12)
    # Strasse
    d.rectangle([0, 500, W, H], fill=(18, 18, 26))
    d.rectangle([0, 500, W, 506], fill=(60, 60, 72))
    a = np.array(im).astype(np.float32)
    refl = a[400:500][::-1]
    refl = np.array(Image.fromarray(refl.astype(np.uint8)).resize((W, 220)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32)
    a[506:726 if 726 <= H else H] = a[506:H] * 0.5 + refl[: H - 506] * 0.5
    a[506:H] *= np.linspace(0.9, 0.55, H - 506)[:, None, None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    # Strassenlaterne
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(gl)
    for r, al in [(160, 10), (110, 18), (70, 30), (35, 70)]:
        g.ellipse([300 - r, 250 - r, 300 + r, 250 + r], fill=(255, 210, 140, al))
    d = ImageDraw.Draw(im); d.rectangle([297, 250, 303, 540], fill=(10, 10, 14))
    im = Image.alpha_composite(im.convert("RGBA"), gl.filter(ImageFilter.GaussianBlur(10))).convert("RGB")
    ImageDraw.Draw(im).ellipse([292, 244, 308, 258], fill=(255, 235, 190))
    return im
BG = make_bg()

# ---------- Regen ----------
_r = random.Random(3)
DROPS = [(_r.uniform(0, W), _r.uniform(0, H + 60), _r.uniform(700, 1100), _r.uniform(10, 24)) for _ in range(380)]

# ---------- Sharingan ----------
def sharingan(r, c=1.0, tom=1.0, ang=0.0, openness=1.0, round_=False, ss=2):
    a = r * 2.2; h = r * 1.35 * max(openness, 0.02)
    cw = int(2 * a + 8) * ss; ch = int((2 * r * 1.45 + 8)) * ss if not round_ else int(2 * r + 8) * ss
    if round_: cw = ch
    L = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); cx, cy = cw / 2, ch / 2
    R = r * ss
    mask = Image.new("L", (cw, ch), 0); md = ImageDraw.Draw(mask)
    if round_:
        md.ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
    else:
        pts_t, pts_b = [], []
        for i in range(81):
            u = -1 + i / 40; px = cx + u * a * ss
            e = (1 - u * u) ** 0.85
            pts_t.append((px, cy - h * ss * e)); pts_b.append((px, cy + h * ss * 0.85 * e))
        md.polygon(pts_t + pts_b[::-1], fill=255)
    d = ImageDraw.Draw(L)
    if not round_:
        arr = np.zeros((ch, cw, 4), np.uint8)
        v = 1 - 0.45 * (np.abs(np.arange(ch) - cy) / max(h * ss, 1)) ** 2
        arr[..., :3] = (np.array([236, 228, 222])[None, None, :] * np.clip(v, 0.4, 1)[:, None, None]).astype(np.uint8)
        arr[..., 3] = 255
        L = Image.fromarray(arr); d = ImageDraw.Draw(L)
    c0 = np.array([70, 40, 25]) * (1 - c) + np.array([110, 0, 8]) * c
    c1 = np.array([135, 82, 46]) * (1 - c) + np.array([240, 30, 28]) * c
    for i in range(24):
        u = i / 23; rr = R * (1 - u)
        col = tuple(int(c0[k] * (1 - u) + c1[k] * u) for k in range(3)) + (255,)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(8, 4, 4, 255), width=int(R * 0.07))
    pr = R * (0.2 + 0.05 * c)
    d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=(0, 0, 0, 255))
    if tom > 0.01:
        T = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); td = ImageDraw.Draw(T)
        rr = R * 0.6
        td.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(10, 0, 0, int(255 * tom)), width=max(1, int(R * 0.03)))
        for k in range(3):
            a0 = ang + k * 2 * math.pi / 3
            hx, hy = cx + rr * math.cos(a0), cy + rr * math.sin(a0)
            hr = R * 0.13
            td.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(8, 0, 0, int(255 * tom)))
            outer, inner = [], []
            for i in range(21):
                s = i / 20; th = a0 - s * 1.0; w = hr * (1 - s)
                outer.append((cx + (rr + w * 0.4) * math.cos(th), cy + (rr + w * 0.4) * math.sin(th)))
                inner.append((cx + (rr - w * 0.9) * math.cos(th), cy + (rr - w * 0.9) * math.sin(th)))
            td.polygon(outer + inner[::-1], fill=(8, 0, 0, int(255 * tom)))
        L = Image.alpha_composite(L, T)
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); out.paste(L, (0, 0), mask)
    if not round_:
        ImageDraw.Draw(out).line(pts_t, fill=(25, 12, 10, 255), width=int(5 * ss), joint="curve")
        ImageDraw.Draw(out).line(pts_b, fill=(25, 12, 10, 255), width=int(3 * ss), joint="curve")
    return out.resize((cw // ss, ch // ss), Image.LANCZOS)

def paste_c(base, sprite, cx, cy):
    base.alpha_composite(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)))

# ---------- Szenen ----------
def person_x(t):
    if t < 49: return min(100 + 55 * tw(t), 520)
    if t < 51: return lerp(520, 1000, sstep(48.8, 50.8, t))
    if t < 55: return 1000
    return 1000 + 70 * (tw(t) - tw(55))

def draw_person(d, x, fy, t, alpha=255, scale=1.0, walking=True):
    s = scale; ph = tw(t) * 6.0
    sw = math.sin(ph) * 22 * s if walking else 0
    col = (12, 12, 18, alpha)
    d.line([x, fy - 70 * s, x + sw, fy], fill=col, width=int(13 * s))
    d.line([x, fy - 70 * s, x - sw, fy], fill=col, width=int(13 * s))
    d.polygon([(x - 22 * s, fy - 75 * s), (x + 22 * s, fy - 75 * s), (x + 28 * s, fy - 130 * s), (x - 28 * s, fy - 130 * s)], fill=(20, 20, 30, alpha))
    d.ellipse([x - 15 * s, fy - 165 * s, x + 15 * s, fy - 133 * s], fill=(14, 14, 20, alpha))
    d.pieslice([x - 62 * s, fy - 215 * s, x + 62 * s, fy - 135 * s], 180, 360, fill=(110, 18, 28, alpha))
    d.line([x, fy - 175 * s, x, fy - 128 * s], fill=(10, 10, 14, alpha), width=max(2, int(3 * s)))

def car_p(t):
    if t < 36: return -1
    if t < 50: return (t - 36) / 14
    return 1 + 0.3 * sstep(50, 53, t) * 1.0 + 0.0

def draw_car(base, t):
    p = car_p(t)
    if p < 0: return
    wd = 40 + 700 * p * p; ht = wd * 0.42
    cx = 900 - 380 * min(p, 1) - max(0, p - 1) * 3800
    by = 480 + 160 * min(p, 1) ** 2 + 0
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rounded_rectangle([cx - wd / 2, by - ht, cx + wd / 2, by], radius=wd * 0.06, fill=(10, 12, 18, 255))
    d.rounded_rectangle([cx - wd * 0.33, by - ht * 1.25, cx + wd * 0.33, by - ht * 0.75], radius=wd * 0.05, fill=(16, 20, 30, 255))
    for sgn in (-1, 1):
        hx = cx + sgn * wd * 0.36; hy = by - ht * 0.42
        for r, al in [(wd * 0.14, 40), (wd * 0.09, 90), (wd * 0.055, 255)]:
            d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 245, 210, al))
    glow = L.filter(ImageFilter.GaussianBlur(max(2, wd * 0.03)))
    base.alpha_composite(glow); base.alpha_composite(L)

def render_world(t):
    base = BG.convert("RGBA")
    d = ImageDraw.Draw(base)
    px = person_x(t); walking = (t < 8.2) or (t > 54)
    ghost = 40 <= t < 49
    draw_person(d, px, 600, t, walking=walking and True if t < 8.2 or t > 54 else False)
    draw_car(base, t)
    if 38 <= t < 49.5:                       # Zukunftsvision
        a = int(200 * sstep(38, 39.5, t) * (1 - sstep(48.5, 49.5, t)))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
        pts = [(900 - 380 * u, 480 + 160 * u * u) for u in np.linspace(0, 1, 25)]
        for i in range(0, 24, 2): ld.line([pts[i], pts[i + 1]], fill=(255, 40, 40, a), width=5)
        ld.ellipse([520 - 40, 640 - 40, 520 + 40, 640 + 40], outline=(255, 40, 40, a), width=4)
        ld.line([520 - 28, 640 - 28, 520 + 28, 640 + 28], fill=(255, 40, 40, a), width=4)
        ld.line([520 - 28, 640 + 28, 520 + 28, 640 - 28], fill=(255, 40, 40, a), width=4)
        if t > 42:
            ga = int(a * 0.7 * sstep(42, 44, t))
            for i in range(0, 20, 2):
                u0, u1 = i / 20, (i + 1) / 20
                ld.line([(lerp(520, 1000, u0), 600 - 40 * math.sin(math.pi * u0)), (lerp(520, 1000, u1), 600 - 40 * math.sin(math.pi * u1))], fill=(90, 200, 255, ga), width=4)
            draw_person(ld, 1000, 600, t, alpha=int(ga * 0.5), walking=False)
        base.alpha_composite(L.filter(ImageFilter.GaussianBlur(1.5)))
        base.alpha_composite(L)
    # Regen
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L); w_ = tw(t)
    for x0, y0, vy, ln in DROPS:
        y = (y0 + vy * w_) % (H + 60) - 30; x = (x0 - 0.12 * vy * w_) % W
        d.line([x, y, x - ln * 0.12, y - ln], fill=(175, 195, 230, 120), width=1)
    base.alpha_composite(L)
    return np.array(base.convert("RGB")).astype(np.float32)

def vision_filter(arr, w, t):
    g = arr.mean(2, keepdims=True)
    out = g * np.array([1.25, 0.5, 0.5]) + arr * np.array([0.2, 0.0, 0.0])
    yy, xx = np.mgrid[0:H, 0:W]
    rr = (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    v = (1 - 0.7 * rr ** 1.2)[..., None]
    pulse = 0.85 + 0.15 * math.sin(t * 5)
    out = out * v; out[..., 0] += 60 * (1 - v[..., 0]) * pulse
    return arr * (1 - w) + out * w

def render_eye(t):
    img = Image.new("RGBA", (W, H), (4, 2, 4, 255))
    c = sstep(16, 18.5, t); tom = sstep(18, 20, t)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    ga = int(150 * c)
    for r, al in [(520, 10), (400, 18), (300, 28)]:
        gd.ellipse([640 - r, 360 - r, 640 + r, 360 + r], fill=(220, 20, 20, int(al * ga / 150)))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
    o = sstep(11, 13.5, t)
    if 15.0 < t < 15.4: o *= 1 - math.sin((t - 15.0) / 0.4 * math.pi) * 0.92
    ang = 1.5 * max(0, t - 18) ** 2 + 0.3 * t
    if o > 0.01: paste_c(img, sharingan(150, c, tom, ang, o), 640, 360)
    return np.array(img.convert("RGB")).astype(np.float32)

def draw_text(arr, text, y, sz, alpha, bold=False, color=(255, 255, 255), center_x=W // 2, anchor="mm"):
    if alpha <= 0.01: return arr
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L); f = font(sz, bold)
    a = int(255 * alpha)
    d.text((center_x + 2, y + 2), text, font=f, fill=(0, 0, 0, int(a * 0.8)), anchor=anchor)
    d.text((center_x, y), text, font=f, fill=color + (a,), anchor=anchor)
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    base.alpha_composite(L)
    return np.array(base.convert("RGB")).astype(np.float32)

CAPS = [
 (0.6, 4.6, "Dienstag, 23:47 Uhr. Regen in der Stadt."),
 (5.0, 9.6, "Niemand beachtet ihn. Ein Tag wie jeder andere."),
 (11.8, 15.8, "Doch heute stimmt etwas nicht ..."),
 (16.4, 20.0, "Sein Auge brennt."),
 (20.4, 24.0, "Rot. Drei Tomoe. Das Sharingan."),
 (27.6, 31.6, "Plötzlich wird die Welt langsam."),
 (31.9, 35.4, "Jeder Regentropfen. Jeder Schritt."),
 (36.4, 40.4, "Ein Wagen. Zu schnell. Zu nah."),
 (40.8, 45.0, "Das Auge sieht die Zukunft – einen Atemzug voraus."),
 (45.4, 48.6, "Dort. Genau dort wird er stehen."),
 (49.2, 52.6, "Er bewegt sich, bevor es passiert."),
 (53.4, 57.4, "Der Wagen rauscht vorbei. Niemand hat etwas bemerkt."),
]
PARTS = [(0, "TEIL 1 · ALLTAG"), (10, "TEIL 2 · DAS AUGE"), (24, "TEIL 3 · ERWACHEN"),
         (36, "TEIL 4 · GEFAHR"), (49, "TEIL 5 · ENTSCHEIDUNG"), (55, "TEIL 6 · DANACH")]

def fade(t, a, b, f=0.6): return sstep(a, a + f, t) * (1 - sstep(b - f, b, t))

def frame(t):
    # Basis
    if t < 10: arr = render_world(t)
    elif t < 11: arr = render_world(t) * (1 - sstep(10, 11, t)) + render_eye(t) * sstep(10, 11, t)
    elif t < 24: arr = render_eye(t)
    elif t < 27:
        p = sstep(24, 27, t); wv = render_world(t); wv = vision_filter(wv, 1.0, t); ey = render_eye(24)
        yy, xx = np.mgrid[0:H, 0:W]; r = np.hypot(xx - W / 2, yy - H / 2)
        m = (r < p * 850)[..., None]; arr = np.where(m, wv, ey)
    else:
        arr = render_world(t)
        w = sstep(27, 28, t) * (1 - sstep(54.5, 56, t))
        if w > 0: arr = vision_filter(arr, w, t)
    # Abblende zum Titel
    if t >= 56.5:
        arr = arr * (1 - sstep(56.5, 58.5, t))
    # Sharingan-Icon in der Ecke
    if 27 <= t < 56:
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
        a = sstep(27, 28, t) * (1 - sstep(54.5, 56, t))
        sp = sharingan(40, 1, 1, t * 3.5 * (1 if t < 49 else 3), round_=True, ss=3)
        sp.putalpha(sp.getchannel("A").point(lambda v: int(v * a)))
        paste_c(im, sp, W - 70, 70); arr = np.array(im.convert("RGB")).astype(np.float32)
    # Titelkarte
    if t >= 58:
        im = Image.new("RGBA", (W, H), (3, 1, 3, 255))
        a = sstep(58, 60, t)
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
        for r, al in [(420, 12), (300, 22), (200, 36)]:
            gd.ellipse([640 - r, 300 - r, 640 + r, 300 + r], fill=(220, 20, 20, int(al * a)))
        im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(40)))
        sp = sharingan(120, 1, 1, 1.5 * (t - 58) + 1, round_=True, ss=3)
        sp.putalpha(sp.getchannel("A").point(lambda v: int(v * a)))
        paste_c(im, sp, 640, 270); arr = np.array(im.convert("RGB")).astype(np.float32)
        arr = draw_text(arr, "SHARINGAN", 480, 78, sstep(60, 61.5, t), bold=True, color=(235, 40, 40))
        arr = draw_text(arr, "In der echten Welt", 550, 34, sstep(61.5, 63, t))
        arr = draw_text(arr, "Ende von Teil 1", 640, 20, sstep(63, 64.2, t) * 0.7)
    # Untertitel + Teilnummer
    for a_, b_, s in CAPS:
        if a_ <= t < b_: arr = draw_text(arr, s, 655, 34, fade(t, a_, b_))
    for i, (st, s) in enumerate(PARTS):
        if st <= t < st + 3.2 and not (t >= 58):
            arr = draw_text(arr, s, 48, 22, fade(t, st, st + 3.2, 0.5) * 0.9, bold=True, color=(235, 70, 70), center_x=40, anchor="lm")
    # Fade-in am Anfang
    arr = arr * sstep(0, 1.0, t)
    return np.clip(arr, 0, 255).astype(np.uint8)

# ---------- Audio ----------
def make_audio(path):
    sr = 44100; N = int(DUR * sr); t = np.arange(N) / sr; rng = np.random.default_rng(1)
    n = rng.standard_normal(N)
    k1 = np.ones(3) / 3; k2 = np.ones(60) / 60
    hi = np.convolve(n, k1, "same"); lo = np.convolve(n, k2, "same") * 4
    slow = np.array([1 - speed(x) for x in t[::441]]); slow = np.interp(t, t[::441], slow)
    rain = (hi * (1 - slow * 0.8) + lo * slow * 0.9) * 0.05
    swell = 0.10 + 0.14 * sstep_arr(t, 10, 20) + 0.08 * sstep_arr(t, 27, 36) - 0.14 * sstep_arr(t, 56, 59)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.5 * t + 1) + 0.4 * np.sin(2 * np.pi * 110.7 * t)) * swell * (0.8 + 0.2 * np.sin(2 * np.pi * 0.2 * t))
    heart = np.zeros(N); bt = 20.0; iv = 1.1
    while bt < 58:
        for off, amp in [(0, 1.0), (0.26, 0.6)]:
            i0 = int((bt + off) * sr); L = int(0.3 * sr)
            if i0 + L < N:
                tt = np.arange(L) / sr; heart[i0:i0 + L] += amp * np.sin(2 * np.pi * 52 * tt) * np.exp(-tt * 16) * 0.55
        iv = max(0.6, iv - 0.012); bt += iv
    ct = np.clip((t - 36) / 14, 0, 1)
    f = np.where(t < 50, 60 + 120 * ct, np.where(t < 53, 180 - 110 * sstep_arr(t, 50, 53), 70))
    eng = np.sin(2 * np.pi * np.cumsum(f) / sr) * 0.08 * ((t > 36) & (t < 54)) * np.minimum(1, (t - 36) / 3).clip(0, 1)
    wenv = np.exp(-((t - 51.2) ** 2) / 1.2) * (t > 49.5)
    whoosh = np.convolve(rng.standard_normal(N), np.ones(8) / 8, "same") * wenv * 0.5
    chord = sum(np.sin(2 * np.pi * fr * t) for fr in (110, 164.8, 220, 261.6, 329.6)) * 0.05 * (t > 58) * np.exp(-(t - 58).clip(0) * 0.25) * sstep_arr(t, 58, 59)
    mix = rain + drone + heart + eng + whoosh + chord
    mix = mix * np.minimum(1, t / 1.5) * np.minimum(1, (DUR - t) / 2)
    mix = mix / np.abs(mix).max() * 0.85
    s = (mix * 32767).astype(np.int16)
    st = np.column_stack([s, s]).ravel()
    with wave.open(path, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(st.tobytes())

def sstep_arr(t, a, b):
    u = np.clip((t - a) / (b - a), 0, 1); return u * u * (3 - 2 * u)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for tt in [3, 9, 14, 21, 25.5, 33, 43, 50, 56, 62]:
            Image.fromarray(frame(tt)).save(f"{OUT}/still_{tt}.png")
        sys.exit()
    make_audio(f"{OUT}/audio.wav")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", f"{OUT}/audio.wav", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", f"{OUT}/sharingan.mp4"], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0: print(i, flush=True)
    p.stdin.close(); p.wait(); print("fertig")
