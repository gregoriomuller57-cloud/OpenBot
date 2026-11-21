"""Erzeugt die Sprachspuren mit Piper (neuronale Stimme "Thorsten", CC0) statt espeak.
Aufruf: python3.13 tts.py <arbeitsordner> <pfad/zu/de-thorsten-low.onnx> [length_scale]
"""
import json, subprocess, sys, wave
sys.path.insert(0, ".")
from piper import PiperVoice, SynthesisConfig
from segments import SEGMENTS
S, model = sys.argv[1], sys.argv[2]
ls = float(sys.argv[3]) if len(sys.argv) > 3 else 0.95
voice = PiperVoice.load(model)
# neuere espeak-Daten liefern "ç" (ich-Laut) zerlegt als "c" + Cedille; die Stimme kennt nur das fertige "ç"
_ph = voice.phonemize
def _fix(text):
    out = []
    for sent in _ph(text):
        res = []
        for p in sent:
            if p == "\u0327" and res and res[-1] == "c": res[-1] = "ç"
            elif p in voice.config.phoneme_id_map: res.append(p)
        out.append(res)
    return out
voice.phonemize = _fix
cfg = SynthesisConfig(length_scale=ls, noise_scale=0.7, noise_w_scale=0.85)
durs = []
for i, (_, _, txt) in enumerate(SEGMENTS):
    raw, out = f"{S}/raw{i:02d}.wav", f"{S}/seg{i:02d}.wav"
    with wave.open(raw, "wb") as wf:
        voice.synthesize_wav(txt, wf, syn_config=cfg)
    # wärmerer Klang, leichte Kompression, 44,1 kHz, kurze Pause am Ende
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
        "highpass=f=60,equalizer=f=150:t=q:w=1:g=2.5,equalizer=f=4000:t=q:w=1.5:g=1.5,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,aresample=44100,apad=pad_dur=0.35",
        "-ac", "1", out], check=True)
    durs.append(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", out])))
json.dump(durs, open(f"{S}/durs.json", "w"))
print([round(d, 1) for d in durs], round(sum(durs), 1))
