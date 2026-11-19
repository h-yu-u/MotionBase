"""Synthesize a quiet wind bed, an aerial sweep and a landing for the demo."""
import array
import math
import random
import sys
import wave
from pathlib import Path


def build(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sr=44100
    rng=random.Random(77)
    out=array.array("h")
    wind=air=0.0
    for i in range(sr*5):
        t=i/sr
        noise=rng.uniform(-1,1)
        wind+=.021*(noise-wind)
        air+=.25*(noise-air)
        launch=math.exp(-((t-1.57)/.16)**2)
        sweep=math.exp(-((t-2.83)/.22)**2)
        u=max(0,t-3.30)
        hit=(1-math.exp(-90*u))*math.exp(-10*u)
        ring=max(0,t-2.94)
        chime=(1-math.exp(-140*ring))*math.exp(-6.*ring)*math.sin(2*math.pi*1140*ring)
        sample=wind*(.25+1.2*launch+1.55*sweep)+air*(.21*launch+.6*sweep)
        sample+=hit*(.6*math.sin(2*math.pi*57*u)+.7*wind)+.042*chime
        fade=min(1,t/.12,(5-t)/.26)
        out.append(round(25500*min(1,max(-1,sample))*fade))
    if sys.byteorder=="big":
        out.byteswap()
    with wave.open(str(path),"wb") as file:
        file.setparams((1,2,sr,0,"NONE","not compressed"))
        file.writeframes(out.tobytes())


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1]/"audio/leap.wav")
    build(parser.parse_args().output)
