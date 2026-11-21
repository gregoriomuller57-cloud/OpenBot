"""Rendert das TikTok-Video (1080x1920) für Folge 02 – Handspiel.
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

def sc_hook(d, p, t):
    pitch(d)
    player(d, 540, 520, YEL, "TW")
    fx, fy = PX0 + 60, 760
    player(d, fx, fy, RED)
    bp = ease(min(1, p / 0.35))
    bx, by = lerp(fx + 30, 520, bp), lerp(fy - 20, 690 - 60 * math.sin(bp * math.pi), bp)
    arm_player(d, 540, 700, BLUE, spread=0.8)
    if p < 0.38: ball(d, bx, by)
    else:
        ball(d, 590, 690)
        r = 40 + 30 * math.sin(t * 8)
        d.ellipse([590 - r, 690 - r, 590 + r, 690 + r], outline=YEL, width=6)
    if p > 0.42: badge(d, 540, 1020, "HAND!!!", RED, 110)
    if p > 0.7: text_c(d, (540, 1200), "… oder nicht?", 70, fill=YEL, stroke=8)

def sc_intro(d, p, t):
    s = 1 + 0.05 * math.sin(t * 5)
    text_c(d, (540, 760), "DIE", 80, fill=WHITE)
    text_c(d, (540, 900), "HANDSPIEL", int(150 * s), fill=YEL, stroke=12)
    text_c(d, (540, 1040), "REGEL", 80)
    badge(d, 540, 1220, "Regel 12 · einfach erklärt", (20, 90, 50), 50)

def sc_arm(d, p, t):
    big_human(d, 540, 520, 1.15, "side")
    if p > 0.2:
        y = 520 + 165 * 1.15
        dashed(d, y + 10, YEL, 180, 900, 8)
        text_c(d, (540, y - 40), "Achsel-Grenze", 44, fill=YEL, stroke=6)
    if p > 0.45:
        for s in (-1, 1):
            d.line([540 + s * 90 * 1.15, 520 + 185 * 1.15, 540 + s * 230 * 1.15, 520 + 300 * 1.15], fill=RED, width=40)
        text_c(d, (200, 1020), "zählt", 54, fill=RED); text_c(d, (880, 1020), "zählt", 54, fill=RED)
    if p > 0.7:
        text_c(d, (540, 1330), "Schulter = erlaubt", 60, fill=OKG); check(d, 860, 1330, True, 30)

def sc_not_every(d, p, t):
    text_c(d, (540, 620), "Arm getroffen", 70)
    text_c(d, (540, 720), "≠", 120, fill=YEL)
    text_c(d, (540, 830), "automatisch Hand", 70)
    if p > 0.4:
        d.rounded_rectangle([140, 960, 940, 1130], 30, fill=(18, 40, 28), outline=YEL, width=5)
        text_c(d, (540, 1045), "2 Fragen für den Schiri", 56, fill=YEL, stroke=0)
    if p > 0.6:
        text_c(d, (540, 1230), "1. Absicht?", 56); text_c(d, (540, 1320), "2. Körper vergrößert?", 56)

def sc_deliberate(d, p, t):
    big_human(d, 540, 560, 1.0, "down" if p < 0.3 else "wide", hi=RED if p > 0.3 else None)
    bx = lerp(980, 800, ease(p)); ball(d, bx, 690, 30)
    if p > 0.3: arrow(d, (720, 900), (820, 720), YEL, 8)
    if p > 0.55: badge(d, 540, 1300, "Hand zum Ball = IMMER Hand", RED, 50)

def sc_bigger(d, p, t):
    pitch(d)
    player(d, 540, 520, YEL, "TW")
    spread = ease(p / 0.3)
    arm_player(d, 540, 820, BLUE, spread=spread, r=36)
    if p > 0.3:
        d.rectangle([540 - 120, 790, 540 + 120, 850], outline=YEL, width=5)
        text_c(d, (540, 920), "„Wand“ = Risiko", 56, fill=YEL)
    if p > 0.5:
        bp = ease((p - 0.5) / 0.2); ball(d, lerp(250, 640, bp), lerp(1150, 815, bp))
    if p > 0.75: badge(d, 540, 1220, "Strafraum → ELFMETER", RED, 60)

def sc_natural(d, p, t):
    text_c(d, (540, 560), "Arme bewegen sich mit:", 54)
    items = [("Laufen", True), ("Springen", True), ("Grätschen", True), ("Abstützen beim Fallen", True)]
    n = 1 + int(p * 5)
    for i, (s, ok) in enumerate(items[:min(4, n)]):
        y = 660 + i * 160
        d.rounded_rectangle([140, y, 940, y + 130], 30, fill=(18, 40, 28), outline=OKG, width=5)
        check(d, 220, y + 65, ok, 30)
        d.text((290, y + 65), s, font=font(48), fill=WHITE, anchor="lm")
    if p > 0.8: text_c(d, (540, 1340), "passt zur Bewegung → meist OK", 48, fill=OKG)

def sc_goal(d, p, t):
    pitch(d)
    player(d, 540, 530, YEL, "TW")
    arm_player(d, 620, 700, RED, spread=0.5, label="Stürmer")
    bp = ease(min(1, p / 0.4)); ball(d, lerp(680, 560, bp), lerp(680, PY0 - 14, bp))
    if p > 0.45: badge(d, 540, 1000, "TOR ZÄHLT NICHT", RED, 80)
    if p > 0.7: text_c(d, (540, 1180), "auch ohne Absicht!", 60, fill=YEL)

def sc_teammate(d, p, t):
    pitch(d)
    player(d, 540, 530, YEL, "TW")
    arm_player(d, 340, 980, RED, spread=0.5, label="Mitspieler")
    player(d, 640, 700, RED, "Torschütze")
    if p < 0.3: ball(d, 380, 960)
    elif p < 0.6:
        bp = ease((p - 0.3) / 0.3); ball(d, lerp(380, 620, bp), lerp(960, 690, bp))
    else:
        bp = ease((p - 0.6) / 0.2); ball(d, lerp(620, 560, bp), lerp(690, PY0 - 14, bp))
    if p > 0.75: badge(d, 540, 1220, "TOR ZÄHLT ✓", (20, 140, 70), 80)

def sc_keeper(d, p, t):
    pitch(d)
    cx = (PX0 + PX1) / 2
    d.rectangle([cx - 260, PY0, cx + 260, PY0 + 210], fill=(60, 200, 110))
    d.rectangle([cx - 260, PY0, cx + 260, PY0 + 210], outline=WHITE, width=5)
    text_c(d, (cx, PY0 + 150), "Hände erlaubt", 44, fill=WHITE, stroke=5)
    ky = lerp(540, 820, ease(p))
    player(d, 540, ky, YEL, "TW")
    if p > 0.6:
        check(d, 700, ky, False, 40)
        badge(d, 540, 1220, "draußen = normales Handspiel", RED, 48)

def sc_cards(d, p, t):
    for i, (col, title, sub) in enumerate([(YEL, "GELB", "vielversprechenden Angriff mit der Hand gestoppt"),
                                           (RED, "ROT", "Tor oder klare Torchance absichtlich mit der Hand verhindert")]):
        if p < 0.1 + 0.4 * i: continue
        y = 560 + i * 420
        d.rounded_rectangle([130, y, 330, y + 280], 20, fill=col, outline=WHITE, width=6)
        text_c(d, (640, y + 60), title, 70, fill=col, stroke=6)
        for j, l in enumerate(wrap(sub, 42, 560)):
            text_c(d, (640, y + 140 + j * 54), l, 42, bold=False, stroke=4)

def sc_offpitch(d, p, t):
    d.rounded_rectangle([140, 560, 940, 1060], 30, fill=(10, 14, 20), outline=WHITE, width=8)
    big_human(d, 540, 600, 0.6, "side", hi=RED if int(t * 2) % 2 else None)
    text_c(d, (540, 1010), "Zeitlupe" if p < 0.55 else "Echtzeit ▶", 50, fill=YEL, stroke=0)
    if p > 0.2:
        d.rounded_rectangle([240, 1130, 840, 1360], 24, fill=(10, 14, 20), outline=YEL, width=6)
        text_c(d, (540, 1210), "VAR", 100, fill=YEL, stroke=0)
        text_c(d, (540, 1310), "nur bei klarem Fehler", 42, stroke=0, bold=False)

def sc_recap(d, p, t):
    text_c(d, (540, 500), "MERKE DIR", 80, fill=YEL)
    items = ["ab der Achsel abwärts", "Absicht = immer Hand", "Arme weg vom Körper = Risiko",
             "natürlich bewegt = meist OK", "eigenes Hand-Tor zählt nie"]
    n = 1 + int(p * 6)
    for i, s in enumerate(items[:min(5, n)]):
        y = 600 + i * 150
        d.rounded_rectangle([110, y, 970, y + 120], 26, fill=(18, 40, 28), outline=YEL, width=4)
        text_c(d, (180, y + 60), str(i + 1), 60, fill=YEL, stroke=0)
        d.text((250, y + 60), s, font=font(44), fill=WHITE, anchor="lm")

def sc_outro(d, p, t):
    text_c(d, (540, 620), "MORGEN:", 80)
    s = 1 + 0.06 * math.sin(t * 5)
    text_c(d, (540, 790), "GELB & ROT", int(140 * s), fill=YEL, stroke=12)
    badge(d, 540, 1040, "+ Folgen", RED, 80)
    text_c(d, (540, 1250), "Hand oder nicht?", 56)
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
    text_c(d, (540, 110), "FUSSBALL ERKLÄRT · Folge 2", 40, fill=WHITE, stroke=0)
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
    pitch(d)
    player(d, 540, 520, YEL)
    arm_player(d, 540, 860, BLUE, spread=1.0, r=48)
    ball(d, 640, 840, 26)
    for r in (60, 90): d.ellipse([640 - r, 840 - r, 640 + r, 840 + r], outline=YEL, width=7)
    text_c(d, (540, 230), "HAND", 150, fill=WHITE, stroke=14)
    text_c(d, (540, 380), "ODER NICHT?!", 120, fill=YEL, stroke=14)
    badge(d, 540, 1150, "ELFMETER?", RED, 100)
    d.rounded_rectangle([90, 1420, 990, 1640], 40, fill=RED, outline=WHITE, width=8)
    text_c(d, (540, 1490), "Die Handspiel-Regel", 66, stroke=0); text_c(d, (540, 1580), "in 2 Minuten erklärt", 66, stroke=0)
    text_c(d, (540, 1760), "FUSSBALL ERKLÄRT · Folge 2", 46, fill=WHITE, stroke=6)
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
