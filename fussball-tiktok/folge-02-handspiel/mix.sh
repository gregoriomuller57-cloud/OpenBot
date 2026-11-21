#!/bin/sh
# Hängt die Sprachspuren aneinander und legt ein leises, selbst erzeugtes Musikbett darunter (wird beim Sprechen abgesenkt).
W=$1
ls $W/seg*.wav | sort | sed "s/^/file '/;s/$/'/" > $W/list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i $W/list.txt -c pcm_s16le $W/voice.wav
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $W/voice.wav)
ffmpeg -y -loglevel error -f lavfi -i "aevalsrc='0.05*(sin(2*PI*110*t)+0.7*sin(2*PI*164.8*t)+0.6*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*0.25*t))+0.5*sin(2*PI*277.2*t)*(0.5-0.5*sin(2*PI*0.25*t)))*(0.6+0.4*abs(sin(2*PI*2*t)))':s=44100:d=$D" \
  -af "lowpass=f=1800,afade=t=in:d=1.5,afade=t=out:st=$(echo "$D-2" | bc):d=2,volume=0.5" $W/bed.wav
ffmpeg -y -loglevel error -i $W/voice.wav -i $W/bed.wav -filter_complex \
  "[1][0]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[b];[0][b]amix=inputs=2:duration=first:weights=1 0.35,loudnorm=I=-14:TP=-1.5:LRA=9" \
  -ar 44100 $W/voice_mix.wav
