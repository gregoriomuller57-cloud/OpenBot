"""Rendert das TikTok-Video (1080x1920) für Folge 01 – Abseits.
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
def sc_hook(d, p, t):
    pitch(d)
    ax = 540; ay = lerp(900, 620, ease(p / 0.35))
    player(d, 620, 760, BLUE); player(d, 540, 520, YEL, "TW")
    player(d, ax, ay, RED)
    if p < 0.35: ball(d, ax + 30, ay - 40)
    else:
        bp = ease((p - 0.35) / 0.15); ball(d, lerp(ax + 30, 600, bp), lerp(ay - 40, PY0 - 12, bp))
    if 0.45 < p < 0.62: text_c(d, (540, 1000), "TOOOR!", 150, fill=YEL, stroke=10)
    if p >= 0.62:
        flag(d, PX1 - 20, 1250, ease((p - 0.62) / 0.1), 1.2)
        badge(d, 540, 1020, "ABSEITS!", RED, 96)

def sc_intro(d, p, t):
    s = 1 + 0.05 * math.sin(t * 5)
    text_c(d, (540, 760), "DIE", 80, fill=WHITE)
    text_c(d, (540, 900), "ABSEITS", int(170 * s), fill=YEL, stroke=12)
    text_c(d, (540, 1040), "REGEL", 80)
    badge(d, 540, 1220, "in 2 Minuten erklärt", (20, 90, 50), 52)

def sc_why(d, p, t):
    pitch(d)
    player(d, 540, 530, YEL, "TW"); player(d, 600, 560, RED, "Stürmer")
    player(d, 400, 900, BLUE); player(d, 700, 900, BLUE)
    if p > 0.3: arrow(d, (540, 1300), (580, 600), WHITE, 7, dash=True); ball(d, 540, 1290)
    if p > 0.55:
        check(d, 820, 640, False, 60)
        badge(d, 540, 1180, "Langweilig!", RED, 60)

def sc_position(d, p, t):
    pitch(d, half_line=1180)
    dashed(d, 760)
    player(d, 540, 520, YEL, "TW"); player(d, 380, 760, BLUE); player(d, 720, 830, BLUE)
    player(d, 600, 680, RED, "A"); player(d, 300, 1050, RED); ball(d, 335, 1020)
    items = ["1. gegnerische Hälfte", "2. näher am Tor als der Ball", "3. näher als vorletzter Gegner"]
    shown = 1 + int(p * 3.6)
    for i, s in enumerate(items[:min(3, shown)]):
        y = 1420 + i * 0  # wird unten in Box gezeichnet
    d.rounded_rectangle([90, 1350, 990, 1620], 26, fill=(0, 0, 0))
    for i, s in enumerate(items):
        if i < shown: d.text((130, 1375 + i * 78), s, font=font(46), fill=YEL if i == min(2, shown - 1) else WHITE)
    if shown > 1: d.line([PX0, 1020, PX1, 1020], fill=(255, 255, 255), width=2)

def sc_keeper(d, p, t):
    pitch(d)
    player(d, 540, 520, YEL, "letzter (TW)")
    pulse = 30 + 6 * math.sin(t * 6)
    player(d, 380, 820, BLUE, "vorletzter", r=pulse)
    player(d, 720, 950, BLUE)
    if p > 0.35: dashed(d, 820); text_c(d, (840, 790), "LINIE", 40, fill=YEL, stroke=5)
    player(d, 640, 860, RED, "A")

def sc_moment(d, p, t):
    pitch(d)
    player(d, 540, 520, YEL, "TW"); player(d, 400, 820, BLUE)
    dashed(d, 820)
    pass_t = 0.35
    ay = 820 if p < pass_t else lerp(820, 600, ease((p - pass_t) / 0.4))
    player(d, 650, ay, RED, "A")
    player(d, 300, 1150, RED)
    if p < pass_t: ball(d, 330, 1120); text_c(d, (540, 1250), "Pass … JETZT!", 56, fill=YEL)
    else:
        bp = ease((p - pass_t) / 0.4); ball(d, lerp(330, 680, bp), lerp(1120, 640, bp))
        text_c(d, (540, 1250), "beim Pass auf einer Höhe", 50)
    if p > 0.8: check(d, 860, 600, True, 50); badge(d, 540, 1000, "Alles sauber", (20, 140, 70), 60)

def sc_level(d, p, t):
    pitch(d); player(d, 540, 520, YEL, "TW")
    dashed(d, 820); player(d, 420, 820, BLUE); player(d, 660, 820, RED, "A")
    badge(d, 540, 1100, "KEIN ABSEITS", (20, 140, 70), 80)

def sc_body(d, p, t):
    human(d, 540, 520, 1.0, p > 0.25)
    if p > 0.25:
        text_c(d, (240, 600), "Kopf", 52, fill=OKG); text_c(d, (230, 800), "Rumpf", 52, fill=OKG)
        text_c(d, (250, 1100), "Füße", 52, fill=OKG); text_c(d, (860, 760), "Arme", 52, fill=RED)
        check(d, 900, 860, False, 30)
    if p > 0.65: dashed(d, 1150, YEL, 150, 930, 8); text_c(d, (540, 1210), "VAR-Linie am Knie", 46, fill=YEL)

def sc_active(d, p, t):
    text_c(d, (540, 520), "Im Abseits stehen = erlaubt", 50, fill=WHITE)
    cards = [("Ball spielen", "Er nimmt den Pass an", YEL), ("Gegner stören", "z. B. Sicht vom Torwart", YEL),
             ("Vorteil ziehen", "Abpraller von Pfosten oder TW", YEL)]
    n = 1 + int(max(0, p - 0.2) * 4)
    for i, (a, b, c) in enumerate(cards[:min(3, n)]):
        y = 610 + i * 250
        card(d, (110, y, 970, y + 220), a, b, c)

def sc_exceptions(d, p, t):
    text_c(d, (540, 520), "KEIN Abseits nach …", 66, fill=YEL)
    items = ["Einwurf", "Eckstoß", "Abstoß", "in der eigenen Hälfte"]
    n = 1 + int(p * 5)
    for i, s in enumerate(items[:min(4, n)]):
        y = 650 + i * 160
        d.rounded_rectangle([140, y, 940, y + 130], 30, fill=(18, 40, 28), outline=OKG, width=5)
        check(d, 220, y + 65, True, 30)
        d.text((290, y + 65), s, font=font(56), fill=WHITE, anchor="lm")

def sc_offpitch(d, p, t):
    pitch(d)
    ay = 820 + 40 * math.sin(t * 2)
    dashed(d, ay); player(d, 440, ay, BLUE); player(d, 650, ay + 30, RED)
    flag(d, PX1 + 20, ay + 40, 0.3 if p < 0.55 else 1.0, 0.8)
    text_c(d, (PX1 - 90, ay - 70), "Assistent", 34, fill=YEL, stroke=5)
    if p > 0.5:
        d.rounded_rectangle([240, 1000, 840, 1290], 24, fill=(10, 14, 20), outline=WHITE, width=6)
        text_c(d, (540, 1110), "VAR", 110, fill=YEL, stroke=0)
        text_c(d, (540, 1220), "Tor wird geprüft …", 44, stroke=0, bold=False)

def sc_penalty(d, p, t):
    text_c(d, (540, 560), "Folge von Abseits:", 56)
    # Schiri mit gestrecktem Arm (Zeichen für indirekten Freistoß)
    cx, top = 540, 680
    d.ellipse([cx - 50, top, cx + 50, top + 100], fill=(240, 200, 160), outline=BLACK, width=4)
    d.rounded_rectangle([cx - 70, top + 115, cx + 70, top + 360], 30, fill=(20, 20, 20), outline=WHITE, width=4)
    d.line([cx + 60, top + 140, cx + 90, top - 120], fill=(20, 20, 20), width=36)
    d.line([cx - 60, top + 140, cx - 120, top + 320], fill=(20, 20, 20), width=36)
    for s in (-1, 1): d.line([cx + s * 35, top + 360, cx + s * 55, top + 560], fill=(20, 20, 20), width=40)
    if p > 0.3: badge(d, 540, 1330, "Indirekter Freistoß", (20, 90, 160), 60)

def sc_recap(d, p, t):
    text_c(d, (540, 500), "MERKE DIR", 80, fill=YEL)
    items = ["gegnerische Hälfte", "vor dem Ball", "vor dem vorletzten Gegner", "im Moment des Passes", "nur wenn aktiv"]
    n = 1 + int(p * 6)
    for i, s in enumerate(items[:min(5, n)]):
        y = 600 + i * 150
        d.rounded_rectangle([110, y, 970, y + 120], 26, fill=(18, 40, 28), outline=YEL, width=4)
        text_c(d, (180, y + 60), str(i + 1), 60, fill=YEL, stroke=0)
        d.text((250, y + 60), s, font=font(52), fill=WHITE, anchor="lm")

def sc_outro(d, p, t):
    text_c(d, (540, 620), "MORGEN:", 80)
    s = 1 + 0.06 * math.sin(t * 5)
    text_c(d, (540, 790), "HANDSPIEL", int(150 * s), fill=YEL, stroke=12)
    badge(d, 540, 1040, "+ Folgen", RED, 80)
    text_c(d, (540, 1250), "Deine schlimmste", 52); text_c(d, (540, 1320), "Abseits-Entscheidung?", 52)
    text_c(d, (540, 1400), "→ Kommentare", 52, fill=YEL)

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
    text_c(d, (540, 110), "FUSSBALL ERKLÄRT · Folge 1", 40, fill=WHITE, stroke=0)
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
    player(d, 540, 520, YEL); player(d, 400, 820, BLUE); dashed(d, 820, YEL, PX0, PX1, 10)
    player(d, 660, 760, RED, r=40); ball(d, 700, 700, 22)
    flag(d, PX1 - 40, 1300, 1.0, 1.6)
    text_c(d, (540, 230), "WARUM", 120, fill=WHITE, stroke=12)
    text_c(d, (540, 370), "ABSEITS?!", 150, fill=YEL, stroke=14)
    d.rounded_rectangle([90, 1420, 990, 1640], 40, fill=RED, outline=WHITE, width=8)
    text_c(d, (540, 1490), "Die Regel in", 70, stroke=0); text_c(d, (540, 1580), "2 Minuten erklärt", 70, stroke=0)
    text_c(d, (540, 1760), "FUSSBALL ERKLÄRT · Folge 1", 46, fill=WHITE, stroke=6)
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
