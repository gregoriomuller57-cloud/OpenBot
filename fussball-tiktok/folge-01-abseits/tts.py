import subprocess, json, sys
sys.path.insert(0,'.')
from segments import SEGMENTS
S=sys.argv[1]; rate=sys.argv[2]; durs=[]
for i,(sc,cap,txt) in enumerate(SEGMENTS):
    raw=f"{S}/raw{i:02d}.wav"; out=f"{S}/seg{i:02d}.wav"
    subprocess.run(["espeak-ng","-v","mb-de6","-s",rate,"-p","50","-a","180","-g","2",txt,"-w",raw],check=True,capture_output=True)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",raw,"-af",
      "highpass=f=70,equalizer=f=180:t=q:w=1:g=3,equalizer=f=3500:t=q:w=1:g=2,aecho=0.8:0.5:35:0.12,acompressor=threshold=-18dB:ratio=3,aresample=44100,apad=pad_dur=0.3",
      "-ac","1",out],check=True)
    durs.append(float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",out])))
json.dump(durs,open(f"{S}/durs.json","w"))
print([round(d,1) for d in durs], round(sum(durs),1))
