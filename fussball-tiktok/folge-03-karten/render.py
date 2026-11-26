"""Rendert das TikTok-Video (1080x1920) für Folge 03 – Gelbe und Rote Karte.
Aufruf: python3 render.py <arbeitsordner mit seg*.wav + durs.json> <ausgabe.mp4> [thumbnail.png]
"""
import json, math, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, ".")
from segments import SEGMENTS

W, H, FPS = 1080, 1920, 30
B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F = {}
def font(sz, bold=True):
    k = (sz, bold)
    if k not in F: F[k] = ImageFont.truetype(B if bold else R, sz)
    return F[k]

GREEN1, GREEN2 = (22, 110, 52), (30, 128, 62)
WHITE, YEL, RED, BLUE, BLACK = (255, 255, 255), (255, 214, 10), (230, 57, 70), (40, 110, 230), (12, 16, 14)
OKG = (60, 220, 110)

def ease(x): x = max(0, min(1, x)); return x * x * (3 - 2 * x)
def lerp(a, b, t): return a + (b - a) * t

def text_c(d, xy, s, sz, fill=WHITE, stroke=6, sfill=BLACK, bold=True):
    d.text(xy, s, font=font(sz, bold), fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sfill)

def wrap(s, sz, maxw):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font(sz).getlength(t) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

# ---------- Spielfeld (Ausschnitt, Angriff nach oben) ----------
PX0, PY0, PX1, PY1 = 90, 470, 990, 1330   # Feldbereich auf dem Bildschirm
def pitch(d, half_line=None):
    for i in range(8):
        y0 = PY0 + i * (PY1 - PY0) / 8
        d.rectangle([PX0, y0, PX1, y0 + (PY1 - PY0) / 8], fill=GREEN1 if i % 2 else GREEN2)
    d.rectangle([PX0, PY0, PX1, PY1], outline=WHITE, width=5)
    cx = (PX0 + PX1) / 2
    d.rectangle([cx - 260, PY0, cx + 260, PY0 + 210], outline=WHITE, width=5)   # Strafraum
    d.rectangle([cx - 110, PY0, cx + 110, PY0 + 75], outline=WHITE, width=5)    # Torraum
    d.rectangle([cx - 85, PY0 - 34, cx + 85, PY0], outline=WHITE, width=5, fill=(235, 235, 235))  # Tor
    for x in range(int(cx - 80), int(cx + 80), 16): d.line([x, PY0 - 32, x, PY0 - 2], fill=(180, 180, 180), width=2)
    d.arc([cx - 90, PY0 + 140, cx + 90, PY0 + 280], 20, 160, fill=WHITE, width=5)
    hl = PY1 - 60 if half_line is None else half_line
    d.line([PX0, hl, PX1, hl], fill=WHITE, width=5)                            # Mittellinie
    d.arc([cx - 150, hl - 150, cx + 150, hl + 150], 180, 360, fill=WHITE, width=5)

def player(d, x, y, col, label=None, r=30):
    d.ellipse([x - r + 4, y - r + 8, x + r + 4, y + r + 8], fill=(0, 0, 0, 90))
    d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=WHITE, width=4)
    if label: text_c(d, (x, y + r + 26), label, 30, stroke=4)

def ball(d, x, y, r=16):
    d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE, outline=BLACK, width=3)
    d.regular_polygon((x, y, r * 0.45), 5, fill=BLACK)

def dashed(d, y, col=YEL, x0=PX0, x1=PX1, w=6):
    x = x0
    while x < x1:
        d.line([x, y, min(x + 30, x1), y], fill=col, width=w); x += 50

def arrow(d, a, b, col=WHITE, w=7, dash=False):
    (x0, y0), (x1, y1) = a, b
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    if dash:
        s = 0
        while s < L - 30:
            e = min(s + 26, L - 30)
            d.line([x0 + ux * s, y0 + uy * s, x0 + ux * e, y0 + uy * e], fill=col, width=w); s += 44
    else: d.line([x0, y0, x1 - ux * 20, y1 - uy * 20], fill=col, width=w)
    px, py = -uy, ux
    d.polygon([(x1, y1), (x1 - ux * 36 + px * 18, y1 - uy * 36 + py * 18), (x1 - ux * 36 - px * 18, y1 - uy * 36 - py * 18)], fill=col)

def badge(d, cx, cy, s, col, sz=64):
    w = font(sz).getlength(s) + 70
    d.rounded_rectangle([cx - w / 2, cy - sz * 0.85, cx + w / 2, cy + sz * 0.85], 26, fill=col, outline=WHITE, width=5)
    text_c(d, (cx, cy), s, sz, stroke=3)

def check(d, x, y, ok, s=34):
    if ok: d.line([x - s, y, x - s / 3, y + s * 0.7, x + s, y - s * 0.7], fill=OKG, width=11)
    else:
        d.line([x - s, y - s, x + s, y + s], fill=RED, width=11); d.line([x - s, y + s, x + s, y - s], fill=RED, width=11)

def flag(d, x, y, up=1.0, sz=1.0):
    d.line([x, y, x, y - 170 * sz * up], fill=(60, 60, 60), width=int(9 * sz))
    if up > 0.5:
        t = y - 170 * sz * up
        for i in range(4):
            for j in range(3):
                c = RED if (i + j) % 2 == 0 else YEL
                d.rectangle([x + i * 25 * sz, t + j * 25 * sz, x + (i + 1) * 25 * sz, t + (j + 1) * 25 * sz], fill=c)

def card(d, box, title, sub, col):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 30, fill=(18, 40, 28), outline=col, width=6)
    text_c(d, ((x0 + x1) / 2, y0 + 70), title, 54, fill=col, stroke=0)
    for i, l in enumerate(wrap(sub, 38, x1 - x0 - 60)):
        text_c(d, ((x0 + x1) / 2, y0 + 140 + i * 50), l, 38, stroke=0, bold=False)

def human(d, cx, top, sc, hi):
    """Strichmännchen: hi = Teile, die zählen (grün), Arme rot."""
    g, r = OKG, RED
    d.ellipse([cx - 55 * sc, top, cx + 55 * sc, top + 110 * sc], fill=g if hi else WHITE, outline=BLACK, width=4)
    d.rounded_rectangle([cx - 70 * sc, top + 125 * sc, cx + 70 * sc, top + 380 * sc], 30, fill=g if hi else WHITE, outline=BLACK, width=4)
    for s in (-1, 1):
        d.line([cx + s * 72 * sc, top + 150 * sc, cx + s * 170 * sc, top + 330 * sc], fill=r if hi else WHITE, width=int(34 * sc))
        d.line([cx + s * 35 * sc, top + 380 * sc, cx + s * 70 * sc, top + 640 * sc], fill=g if hi else WHITE, width=int(40 * sc))


# ---------- Szenen: p = Fortschritt 0..1, t = Sekunden in der Szene ----------
def arm_player(d, x, y, col, spread=0.0, r=30, label=None):
    """Spieler von oben mit Armen; spread 0 = Arme am Körper, 1 = weit ausgestreckt."""
    for s in (-1, 1):
        ex, ey = x + s * lerp(r + 6, r + 70, spread), y + lerp(r + 10, -6, spread)
        d.line([x + s * (r - 6), y, ex, ey], fill=col, width=16)
        d.ellipse([ex - 10, ey - 10, ex + 10, ey + 10], fill=(240, 200, 160))
    player(d, x, y, col, label, r)

def big_human(d, cx, top, sc, arms="down", hi=None):
    skin, shirt = (240, 200, 160), BLUE
    d.ellipse([cx - 55 * sc, top, cx + 55 * sc, top + 110 * sc], fill=skin, outline=BLACK, width=4)
    d.rounded_rectangle([cx - 70 * sc, top + 125 * sc, cx + 70 * sc, top + 380 * sc], 30, fill=shirt, outline=BLACK, width=4)
    for s in (-1, 1):
        sx, sy = cx + s * 72 * sc, top + 150 * sc
        if arms == "down": ex, ey = cx + s * 120 * sc, top + 370 * sc
        elif arms == "wide": ex, ey = cx + s * 300 * sc, top + 120 * sc
        else: ex, ey = cx + s * 230 * sc, top + 300 * sc
        col = hi if hi else skin
        d.line([sx, sy, ex, ey], fill=col, width=int(34 * sc))
        d.ellipse([ex - 22 * sc, ey - 22 * sc, ex + 22 * sc, ey + 22 * sc], fill=col, outline=BLACK, width=3)
    for s in (-1, 1): d.line([cx + s * 35 * sc, top + 380 * sc, cx + s * 70 * sc, top + 640 * sc], fill=(20, 20, 20), width=int(40 * sc))

def whistle_badge(d, s, col, y=1250, sz=70): badge(d, 540, y, s, col, sz)

ORANGE = (245, 140, 30)

def pcard(d, cx, cy, col, h=260, tilt=0.0, label=None):
    """Spielkarte (Hochformat) mit leichtem Schatten; tilt in Pixeln schräg."""
    w = h * 0.68
    d.rounded_rectangle([cx - w / 2 + 10, cy - h / 2 + 14, cx + w / 2 + 10, cy + h / 2 + 14], 18, fill=(0, 0, 0))
    d.rounded_rectangle([cx - w / 2 + tilt, cy - h / 2, cx + w / 2 + tilt, cy + h / 2], 18, fill=col, outline=WHITE, width=6)
    if label: text_c(d, (cx + tilt, cy), label, int(h * 0.22), stroke=5)

def ref(d, x, y, arm=0.0, col=BLACK, r=34, card_col=None):
    """Schiedsrichter von vorne, arm = 0..1 hebt den rechten Arm (mit Karte)."""
    d.ellipse([x - r, y - 2.2 * r, x + r, y - 0.2 * r], fill=(240, 200, 160), outline=BLACK, width=3)
    d.rounded_rectangle([x - 1.3 * r, y, x + 1.3 * r, y + 3.2 * r], 24, fill=col, outline=WHITE, width=3)
    d.line([x - 1.2 * r, y + 0.4 * r, x - 1.9 * r, y + 2.6 * r], fill=col, width=int(0.6 * r))
    ex, ey = x + lerp(2.0 * r, 1.6 * r, arm), y + lerp(2.6 * r, -2.6 * r, arm)
    d.line([x + 1.2 * r, y + 0.4 * r, ex, ey], fill=col, width=int(0.6 * r))
    if card_col and arm > 0.6: pcard(d, ex, ey - 0.9 * r, card_col, h=2.4 * r)
    for s in (-1, 1): d.line([x + s * 0.6 * r, y + 3.2 * r, x + s * 0.8 * r, y + 5.6 * r], fill=BLACK, width=int(0.6 * r))

def listbox(d, items, p, col, y0=620, step=150, icon=None):
    n = 1 + int(p * (len(items) + 1))
    for i, s in enumerate(items[:min(len(items), n)]):
        y = y0 + i * step
        d.rounded_rectangle([110, y, 970, y + step - 28], 26, fill=(18, 40, 28), outline=col, width=5)
        pcard(d, 180, y + (step - 28) / 2, col, h=80)
        d.text((240, y + (step - 28) / 2), s, font=font(44), fill=WHITE, anchor="lm")

def sc_hook(d, p, t):
    pitch(d)
    player(d, 540, 520, YEL, "TW")
    sx = lerp(300, 600, ease(min(1, p / 0.3)))
    player(d, 640, 900, RED, "Stürmer" if p < 0.3 else None)
    player(d, sx, 980, BLUE)
    if p > 0.3:
        badge(d, 540, 1120, "FOUL!", RED, 90)
    if p > 0.45:
        ref(d, 540, 1450, arm=ease((p - 0.45) / 0.25), card_col=YEL if int(t * 2.5) % 2 else RED, r=36)
    if p > 0.75: text_c(d, (820, 1480), "Gelb?\nRot?", 70, fill=YEL, stroke=8)

def sc_intro(d, p, t):
    s = 1 + 0.05 * math.sin(t * 5)
    pcard(d, 330, 760, YEL, h=300, tilt=-20)
    pcard(d, 750, 760, RED, h=300, tilt=20)
    text_c(d, (540, 1020), "GELB & ROT", int(130 * s), fill=YEL, stroke=12)
    text_c(d, (540, 1140), "wann gibt's was?", 64)
    badge(d, 540, 1300, "Regel 12 · einfach erklärt", (20, 90, 50), 50)

def sc_history(d, p, t):
    # Ampel
    d.rounded_rectangle([390, 520, 690, 1120], 50, fill=(30, 30, 30), outline=WHITE, width=6)
    phase = 0 if p < 0.45 else (1 if p < 0.75 else 2)
    for i, c in enumerate([RED, YEL, OKG]):
        on = (phase == 1 and i == 1) or (phase == 2 and i == 0) or (phase == 0 and i == 2)
        col = c if on else tuple(int(v * 0.25) for v in c)
        d.ellipse([460, 560 + i * 185, 620, 720 + i * 185], fill=col)
    text_c(d, (540, 1210), "WM 1970 · Ken Aston", 58, fill=YEL)
    if p > 0.45: text_c(d, (800, 840), "Vorsicht", 44, fill=YEL); 
    if p > 0.75: text_c(d, (800, 650), "Stopp!", 48, fill=RED)
    if p > 0.85: text_c(d, (540, 1320), "versteht jeder – ohne Worte", 48)

def sc_yellow(d, p, t):
    listbox(d, ["rücksichtsloses Foul", "Meckern / Reklamieren", "Zeitspiel", "Abstand nicht eingehalten",
                "Trikot aus beim Jubel"], p, YEL, y0=560, step=150)

def sc_tactical(d, p, t):
    pitch(d, half_line=1240)
    player(d, 540, 520, YEL, "TW")
    ax = lerp(540, 600, ease(p)); ay = lerp(1150, 980, ease(p))
    arrow(d, (540, 1150), (560, 700), (255, 255, 255), 6, dash=True)
    player(d, 540, ay if p < 0.45 else 1020, RED, "Konter")
    ball(d, 575, (ay if p < 0.45 else 1020) - 40)
    if p > 0.3:
        bx = lerp(380, 500, ease((p - 0.3) / 0.15)); player(d, bx, 1060, BLUE)
        if p > 0.45: d.line([bx + 20, 1050, 520, 1030], fill=YEL, width=8); text_c(d, (330, 1120), "zieht am Trikot", 38, fill=YEL, stroke=5)
    if p > 0.65: pcard(d, 820, 760, YEL, h=220)
    if p > 0.7: badge(d, 540, 1450, "Angriff gestoppt = GELB", (150, 110, 0), 56)

def sc_yellowred(d, p, t):
    pcard(d, 300, 800, YEL, h=320)
    if p > 0.2: text_c(d, (540, 800), "+", 120, fill=WHITE)
    if p > 0.3: pcard(d, 780, 800, YEL, h=320)
    if p > 0.5:
        text_c(d, (540, 1060), "=", 110)
        # Gelb-Rot-Karte: diagonal geteilt
        cx, cy, h = 540, 1270, 260; w = h * 0.68
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 18, fill=YEL, outline=WHITE, width=6)
        d.polygon([(cx + w / 2 - 6, cy - h / 2 + 6), (cx + w / 2 - 6, cy + h / 2 - 6), (cx - w / 2 + 6, cy + h / 2 - 6)], fill=RED)
    if p > 0.75: text_c(d, (540, 1480), "Platzverweis → zu zehnt", 54, fill=YEL)

def sc_red(d, p, t):
    pcard(d, 540, 660, RED, h=280 + 10 * math.sin(t * 6))
    listbox(d, ["grobes Foulspiel", "Tätlichkeit", "Spucken", "Beleidigung"], p, RED, y0=870, step=145)

def sc_dogso(d, p, t):
    pitch(d)
    player(d, 540, 520, YEL, "TW")
    sy = lerp(1150, 820, ease(min(1, p / 0.5)))
    player(d, 540, sy, RED, "allein")
    ball(d, 580, sy - 40)
    dx = lerp(820, 600, ease(min(1, p / 0.5))); player(d, dx, sy + 40, BLUE, "letzter Mann")
    if p > 0.5:
        badge(d, 540, 1050, "NOTBREMSE", RED, 90)
    if p > 0.65: pcard(d, 860, 700, RED, h=220)
    if p > 0.75: text_c(d, (540, 1230), "klare Torchance verhindert", 54, fill=YEL)

def sc_penaltybox(d, p, t):
    pitch(d)
    cx = (PX0 + PX1) / 2
    d.rectangle([cx - 260, PY0, cx + 260, PY0 + 210], outline=YEL, width=9)
    player(d, 540, 520, YEL, "TW")
    player(d, 600, 620, RED); player(d, 650, 650, BLUE)
    if p > 0.2: text_c(d, (540, 820), "wollte den Ball spielen", 50, fill=WHITE)
    if p > 0.4:
        badge(d, 540, 960, "ELFMETER", RED, 70)
        pcard(d, 540, 1170, YEL, h=230, label="nur")
    if p > 0.7: text_c(d, (540, 1370), "statt 3-fach-Strafe", 56, fill=YEL)

def sc_seven(d, p, t):
    n = 11 if p < 0.15 else max(6, 11 - int((p - 0.15) * 10))
    for i in range(11):
        x, y = 210 + (i % 4) * 220, 620 + (i // 4) * 200
        col = RED if i < n else (60, 60, 60)
        player(d, x, y, col)
        if i >= n: d.line([x - 34, y - 34, x + 34, y + 34], fill=WHITE, width=6)
    text_c(d, (540, 1250), f"{n} Spieler", 80, fill=YEL if n >= 7 else RED)
    if n < 7: badge(d, 540, 1420, "SPIELABBRUCH", RED, 70)
    else: text_c(d, (540, 1400), "kein Ersatz nach Rot", 52)

def sc_offpitch(d, p, t):
    rows = [("5× Gelb", "1 Spiel Sperre", YEL), ("Gelb-Rot", "1 Spiel Sperre", ORANGE), ("Rot", "Sportgericht entscheidet", RED)]
    text_c(d, (540, 560), "BUNDESLIGA", 64, fill=WHITE)
    n = 1 + int(p * 4)
    for i, (a, b, c) in enumerate(rows[:min(3, n)]):
        y = 650 + i * 230
        d.rounded_rectangle([90, y, 990, y + 200], 30, fill=(18, 40, 28), outline=c, width=6)
        pcard(d, 170, y + 100, c, h=130)
        text_c(d, (560, y + 60), a, 58, fill=c, stroke=4)
        text_c(d, (560, y + 140), b, 44, stroke=0, bold=False)

def sc_coach(d, p, t):
    # Coaching-Zone
    d.rectangle([140, 900, 940, 1300], outline=WHITE, width=6)
    text_c(d, (540, 1340), "Coaching-Zone", 40, stroke=0)
    jump = abs(math.sin(t * 7)) * 40 if p < 0.6 else 0
    ref(d, 540, 1000 - jump, arm=0.0, col=(70, 70, 90), r=40)
    if p < 0.6: text_c(d, (540, 760), "!#@%?!", 80, fill=RED)
    else:
        pcard(d, 300, 720, YEL, h=200); pcard(d, 780, 720, RED, h=200)
        text_c(d, (540, 1450), "→ ab auf die Tribüne", 56, fill=YEL)

def sc_recap(d, p, t):
    text_c(d, (540, 500), "MERKE DIR", 80, fill=YEL)
    items = [("Gelb = Verwarnung", YEL), ("2× Gelb = Gelb-Rot", ORANGE), ("Rot = sofort runter", RED),
             ("Notbremse = meist Rot", RED), ("danach oft Sperre", WHITE)]
    n = 1 + int(p * 6)
    for i, (s, c) in enumerate(items[:min(5, n)]):
        y = 600 + i * 150
        d.rounded_rectangle([110, y, 970, y + 120], 26, fill=(18, 40, 28), outline=c, width=4)
        text_c(d, (180, y + 60), str(i + 1), 60, fill=c, stroke=0)
        d.text((250, y + 60), s, font=font(46), fill=WHITE, anchor="lm")

def sc_outro(d, p, t):
    text_c(d, (540, 620), "MORGEN:", 80)
    s = 1 + 0.06 * math.sin(t * 5)
    text_c(d, (540, 790), "DER ELFMETER", int(120 * s), fill=YEL, stroke=12)
    badge(d, 540, 1040, "+ Folgen", RED, 80)
    text_c(d, (540, 1250), "Deine krasseste Rote?", 56)
    text_c(d, (540, 1330), "→ Kommentare", 56, fill=YEL)

SCENES = {k[3:]: v for k, v in globals().items() if k.startswith("sc_")}

# ---------- Hintergrund + Overlay ----------
BG = Image.new("RGB", (W, H))
bd = ImageDraw.Draw(BG)
for y in range(H):
    k = y / H
    bd.line([0, y, W, y], fill=(int(lerp(8, 4, k)), int(lerp(46, 20, k)), int(lerp(30, 14, k))))
for x in range(-H, W, 90): bd.line([x, 0, x + H, H], fill=(14, 56, 36), width=22)

def chunks(text, dur):
    words, out, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 5 or w.endswith((".", "?", "!", ":")):
            out.append(" ".join(cur)); cur = []
    if cur: out.append(" ".join(cur))
    tot = sum(len(c) + 4 for c in out); t, res = 0, []
    for c in out:
        dd = dur * (len(c) + 4) / tot; res.append((t, t + dd, c)); t += dd
    return res

def frame(i_seg, t, dur, total_t, total):
    sc, cap, txt = SEGMENTS[i_seg]
    im = BG.copy(); d = ImageDraw.Draw(im)
    # Kopfzeile
    d.rounded_rectangle([60, 70, 1020, 150], 40, fill=(0, 0, 0))
    text_c(d, (540, 110), "FUSSBALL ERKLÄRT · Folge 3", 40, fill=WHITE, stroke=0)
    # Titel der Szene (Pop-in)
    pop = ease(t / 0.35)
    for j, l in enumerate(wrap(cap, 70, 960)):
        text_c(d, (540, 250 + j * 85), l, int(70 * (0.7 + 0.3 * pop)), fill=YEL, stroke=8)
    SCENES[sc](d, min(1, t / max(dur - 0.3, 0.1)), t)
    # Untertitel
    for a, b, c in chunks(txt, dur - 0.3):
        if a <= t < b or (t >= b and c == chunks(txt, dur - 0.3)[-1][2] and t >= dur - 0.3):
            lines = wrap(c, 62, 940)
            y0 = 1730 - (len(lines) - 1) * 40
            for j, l in enumerate(lines):
                tw = font(62).getlength(l)
                d.rounded_rectangle([540 - tw / 2 - 24, y0 + j * 80 - 44, 540 + tw / 2 + 24, y0 + j * 80 + 40], 18, fill=(0, 0, 0))
                text_c(d, (540, y0 + j * 80), l, 62, fill=WHITE, stroke=0)
            break
    # Fortschrittsbalken
    d.rectangle([0, H - 14, W, H], fill=(0, 0, 0)); d.rectangle([0, H - 14, W * total_t / total, H], fill=YEL)
    return im

def thumbnail(path):
    im = BG.copy(); d = ImageDraw.Draw(im)
    # Strahlen hinter den Karten
    for k in range(18):
        a = k * math.pi / 9
        d.polygon([(540, 900), (540 + 1400 * math.cos(a), 900 + 1400 * math.sin(a)),
                   (540 + 1400 * math.cos(a + 0.17), 900 + 1400 * math.sin(a + 0.17))], fill=(16, 70, 42))
    text_c(d, (540, 230), "GELB", 150, fill=YEL, stroke=14)
    text_c(d, (540, 390), "ODER ROT?!", 130, fill=RED, stroke=14)
    for cx, cy, col, ang in ((370, 900, YEL, 12), (710, 930, RED, -12)):
        L = Image.new("RGBA", (520, 640), (0, 0, 0, 0)); ld = ImageDraw.Draw(L)
        ld.rounded_rectangle([90, 70, 440, 590], 24, fill=(0, 0, 0, 150))
        ld.rounded_rectangle([75, 55, 425, 575], 24, fill=col, outline=WHITE, width=8)
        L = L.rotate(ang, resample=Image.BICUBIC, expand=True)
        im.paste(L, (int(cx - L.width / 2), int(cy - L.height / 2)), L)
    d = ImageDraw.Draw(im)
    badge(d, 540, 1290, "Notbremse = immer Rot?", (20, 20, 20), 60)
    d.rounded_rectangle([90, 1420, 990, 1640], 40, fill=RED, outline=WHITE, width=8)
    text_c(d, (540, 1490), "Alle Karten-Regeln", 66, stroke=0); text_c(d, (540, 1580), "in 2 Minuten erklärt", 66, stroke=0)
    text_c(d, (540, 1760), "FUSSBALL ERKLÄRT · Folge 3", 46, fill=WHITE, stroke=6)
    im.save(path)

if __name__ == "__main__":
    S, out = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3: thumbnail(sys.argv[3])
    durs = json.load(open(f"{S}/durs.json")); total = sum(durs)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", f"{S}/voice_mix.wav", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
                          "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    start = 0.0
    for i, dur in enumerate(durs):
        for f in range(int(round(dur * FPS))):
            t = f / FPS
            p.stdin.write(frame(i, t, dur, start + t, total).tobytes())
        start += dur
    p.stdin.close(); p.wait()
