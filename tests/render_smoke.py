"""Verify the actual Blender -> PNG -> H.264/AAC output without an external pack."""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from motionbase.io import write_json
from motionbase.runner import backend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender")
    args = parser.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Render smoke test needs FFmpeg and FFprobe")
    with tempfile.TemporaryDirectory(prefix="motionbase-render-test-") as temporary:
        directory = Path(temporary)
        job = write_json(directory / "job.json", {"directory": str(directory)})
        commands = [backend(ROOT / "tests/integration/make_render_fixture.py", job, args.blender)]
        render = [sys.executable, "-m", "motionbase", "render", str(directory / "shot.json"),
                  "--style", str(directory / "style.json"), "-o", str(directory / "clip.mp4")]
        if args.blender:
            render += ["--blender", args.blender]
        commands.append(render)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        for command in commands:
            result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError("\n".join(result.stdout.splitlines()[-50:]))
        result = subprocess.check_output([
            "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
            "-of", "json", str(directory / "clip.mp4")
        ], text=True)
        probe = json.loads(result)
        video = next(s for s in probe["streams"] if s["codec_type"] == "video")
        audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
        assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p", video
        assert (video["width"], video["height"]) == (64, 64), video
        assert video["avg_frame_rate"] == "24/1" and int(video["nb_read_frames"]) == 12, video
        assert math.isclose(float(video["duration"]), 0.5, abs_tol=0.001), video
        assert audio["codec_name"] == "aac", audio
        assert math.isclose(float(audio["duration"]), 0.5, abs_tol=0.05), audio
        print("Verified 12 frames, 24 fps, 64x64, 0.5 s, H.264/yuv420p and padded AAC audio")


if __name__ == "__main__":
    main()
