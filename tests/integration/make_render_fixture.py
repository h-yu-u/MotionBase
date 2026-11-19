"""Create a tiny shot and a short PCM track for the encoder smoke test."""

import json
import math
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import make_fixture

job = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
directory = Path(job["directory"])
shot, style = make_fixture(directory)
audio = directory / "tone.wav"
with wave.open(str(audio), "wb") as stream:
    stream.setnchannels(1)
    stream.setsampwidth(2)
    stream.setframerate(24000)
    stream.writeframes(b"".join(struct.pack("<h", int(600 * math.sin(i * math.tau * 440 / 24000)))
                              for i in range(6000)))
shot["audio"] = str(audio)
for name, value in (("shot.json", shot), ("style.json", style)):
    (directory / name).write_text(json.dumps(value), encoding="utf-8")
