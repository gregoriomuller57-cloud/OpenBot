"""Erzeugt die Sprachspuren mit Piper (neuronale Stimme "Thorsten", CC0).
Neu ab Folge 03 (menschlicher): jeder Satz wird einzeln gesprochen, mit leicht wechselndem Tempo,
echten Atempausen zwischen den Sätzen und etwas Raumklang statt "trockener" Roboterstimme.
Aufruf: python3.13 tts.py <arbeitsordner> <pfad/zu/de-thorsten-low.onnx>
"""
import json, random, re, subprocess, sys, wave
sys.path.insert(0, ".")
from piper import PiperVoice, SynthesisConfig
from segments import SEGMENTS
S, model = sys.argv[1], sys.argv[2]
random.seed(3)
voice = PiperVoice.load(model)
# neuere espeak-Daten liefern "ç" (ich-Laut) zerlegt als "c" + Cedille; die Stimme kennt nur das fertige "ç"
_ph = voice.phonemize
def _fix(text):
    out = []
    for sent in _ph(text):
        res = []
        for p in sent:
            if p == "̧" and res and res[-1] == "c": res[-1] = "ç"
            elif p in voice.config.phoneme_id_map: res.append(p)
        out.append(res)
    return out
voice.phonemize = _fix
rate = voice.config.sample_rate

def sentences(txt):
    return [s.strip() for s in re.split(r"(?<=[.!?:])\s+", txt) if s.strip()]

def silence(sec): return b"\x00\x00" * int(rate * sec)

durs = []
for i, (_, _, txt) in enumerate(SEGMENTS):
    raw, out = f"{S}/raw{i:02d}.wav", f"{S}/seg{i:02d}.wav"
    pcm = b""
    for s in sentences(txt):
        # Fragen und Ausrufe etwas lebendiger, Erklärsätze etwas ruhiger
        ls = random.uniform(0.86, 0.93) if s.endswith(("?", "!")) else random.uniform(0.9, 0.99)
        cfg = SynthesisConfig(length_scale=ls, noise_scale=random.uniform(0.62, 0.78), noise_w_scale=0.9)
        for chunk in voice.synthesize(s, syn_config=cfg):
            pcm += chunk.audio_int16_bytes
        pcm += silence(random.uniform(0.18, 0.3) if not s.endswith("?") else random.uniform(0.3, 0.42))
    with wave.open(raw, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate); wf.writeframes(pcm)
    # wärmerer Klang, Präsenz, leichte Kompression, kleiner Raum, 44,1 kHz
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
        "highpass=f=70,equalizer=f=160:t=q:w=1:g=3,equalizer=f=3200:t=q:w=1.4:g=2,equalizer=f=7000:t=q:w=1:g=-2,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=90,"
        "aecho=0.9:0.85:28|47:0.12|0.07,aresample=44100,apad=pad_dur=0.2",
        "-ac", "1", out], check=True)
    durs.append(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", out])))
json.dump(durs, open(f"{S}/durs.json", "w"))
print([round(d, 1) for d in durs], round(sum(durs), 1))
