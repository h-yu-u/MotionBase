"""Run isolated Blender jobs and atomically publish successful outputs."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import number
from .io import read_json, write_json


def backend(script, job, executable=None):
    binary = executable or os.environ.get("BLENDER_BIN") or shutil.which("blender")
    if not binary and sys.platform == "darwin":
        app = Path("/Applications/Blender.app/Contents/MacOS/Blender")
        if app.is_file():
            binary = str(app)
    if binary:
        return [str(binary), "--background", "--factory-startup", "--disable-autoexec",
                "--python-exit-code", "1", "--python", str(script), "--", str(job)]
    if importlib.util.find_spec("bpy") is not None:
        return [sys.executable, str(script), "--", str(job)]
    raise ValueError("Blender not found. Supply --blender /path/to/blender or use Python with bpy.")


def input_files(shot, style):
    paths = {Path(shot["stage"]["file"]).resolve()}
    for actor in shot["actors"]:
        paths.add(Path(actor["file"]).resolve())
        paths.update(Path(clip["file"]).resolve() for clip in actor["clips"])
    if shot.get("audio"):
        paths.add(Path(shot["audio"]).resolve())
    if style.get("materials"):
        paths.add(Path(style["materials"]["file"]).resolve())
    return paths


def execute(command, shot, style, output=None, blender=None):
    if command not in ("check", "build", "render"):
        raise ValueError(f"Unknown worker command {command!r}")
    target = Path(output).resolve() if output is not None else None
    suffix = ".blend" if command == "build" else ".mp4"
    if command != "check":
        if target is None or target.suffix.lower() != suffix:
            raise ValueError(f"Output must use {suffix}")
        if target in input_files(shot, style):
            raise ValueError("Output must not overwrite an input asset")
        target.parent.mkdir(parents=True, exist_ok=True)
    encoder = shutil.which("ffmpeg")
    if command == "render" and not encoder:
        raise ValueError("FFmpeg is required to encode MP4")
    with tempfile.TemporaryDirectory(prefix="motionbase-", dir=target.parent if target else None) as tmp:
        directory = Path(tmp)
        job = write_json(directory / "job.json", {"shot": shot, "style": style, "command": command})
        subprocess.run(backend(Path(__file__).with_name("worker.py"), job, blender), check=True)
        if command == "check":
            return None
        result = directory / ("result" + suffix)
        if command == "render":
            missing = next((f for f in range(1, shot["frames"] + 1)
                            if not (directory / f"frame-{f:04d}.png").is_file()), None)
            if missing is not None:
                raise ValueError(f"Blender did not finish the frame sequence (missing frame {missing})")
            cmd = [encoder, "-hide_banner", "-loglevel", "error", "-y", "-framerate",
                   str(shot["fps"]), "-start_number", "1", "-i", str(directory / "frame-%04d.png")]
            if shot.get("audio"):
                cmd += ["-i", shot["audio"], "-map", "0:v:0", "-map", "1:a:0", "-af", "apad",
                        "-c:a", "aac", "-b:a", "192k"]
            else:
                cmd += ["-map", "0:v:0", "-an"]
            cmd += ["-frames:v", str(shot["frames"]), "-t", str(shot["frames"] / shot["fps"]),
                    "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-vf",
                    "scale=out_color_matrix=bt709", "-color_primaries", "bt709", "-colorspace",
                    "bt709", "-color_trc", "bt709", "-movflags", "+faststart", str(result)]
            subprocess.run(cmd, check=True)
        os.replace(result, target)
    return target


def compare_files(left, right, report=None, tolerance=1e-5, blender=None):
    number(tolerance, "tolerance")
    if tolerance < 0:
        raise ValueError("tolerance must be nonnegative")
    left, right = Path(left).resolve(), Path(right).resolve()
    for path in (left, right):
        if not path.is_file() or path.suffix.lower() != ".blend":
            raise ValueError(f"Expected an existing .blend file: {path}")
    if report is not None and Path(report).resolve() in (left, right):
        raise ValueError("Comparison report must not overwrite an input")
    with tempfile.TemporaryDirectory(prefix="motionbase-compare-") as tmp:
        directory = Path(tmp)
        result = directory / "report.json"
        job = write_json(directory / "job.json", {
            "left": str(left), "right": str(right), "tolerance": tolerance, "report": str(result)
        })
        subprocess.run(backend(Path(__file__).with_name("comparison.py"), job, blender), check=True)
        data = read_json(result)
    if report is not None:
        write_json(report, data)
    return data
