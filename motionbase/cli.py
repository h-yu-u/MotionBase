"""Thin command adapters: project resolution and Blender execution stay separate."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .assets import AssetPack
from .config import PRESETS, shot_at, style_at
from .project import Project
from .runner import compare_files, execute


def parser():
    cli = argparse.ArgumentParser(prog="motionbase", description="Asset-driven Blender shot execution")
    cli.add_argument("--version", action="version", version=f"MotionBase {__version__}")
    subs = cli.add_subparsers(dest="command", required=True)
    styles = subs.add_parser("styles", help="List compatibility and external styles")
    styles.add_argument("--pack", action="append", default=[], type=Path)
    styles.add_argument("--directory", action="append", default=[], type=Path)
    assets = subs.add_parser("assets", help="Inspect a portable asset manifest")
    assets.add_argument("--pack", required=True, type=Path)
    lock = subs.add_parser("lock", help="Accept current project, engine and asset fingerprints")
    lock.add_argument("project", type=Path)
    compile_cmd = subs.add_parser("compile", help="Compile a locked project shot to renderer v1")
    compile_cmd.add_argument("project", type=Path)
    compile_cmd.add_argument("--shot", dest="shot_id", required=True)
    compile_cmd.add_argument("--style", help="Style ID from an already locked pack")
    compile_cmd.add_argument("-o", "--output", required=True, type=Path)
    for command in ("check", "build", "render"):
        sub = subs.add_parser(command)
        sub.add_argument("shot", type=Path)
        sub.add_argument("--style", required=True, help="preset name or style JSON path")
        sub.add_argument("--style-dir", action="append", default=[], type=Path)
        sub.add_argument("--blender", help="Blender 4.5+ executable")
        if command != "check":
            sub.add_argument("-o", "--output", required=True, type=Path)
    compare = subs.add_parser("compare", help="Compare motion, framing and timing in two .blend files")
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.add_argument("--report", type=Path)
    compare.add_argument("--tolerance", type=float, default=1e-5)
    compare.add_argument("--blender")
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "styles":
        names = {path.stem for path in PRESETS.glob("*.json")}
        for directory in args.directory:
            if not directory.is_dir():
                raise ValueError(f"Style directory does not exist: {directory}")
            names.update(path.stem for path in directory.glob("*.json"))
        for path in args.pack:
            pack = AssetPack(path)
            names.update(f"{pack.id}:{aid}" for aid, spec in pack.assets.items() if spec["kind"] == "style")
        print("\n".join(sorted(names)))
    elif args.command == "assets":
        print(json.dumps(AssetPack(args.pack).data, ensure_ascii=False, indent=2))
    elif args.command == "lock":
        print(Project(args.project).lock())
    elif args.command == "compile":
        result = Project(args.project).compile(args.shot_id, args.output, args.style)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "compare":
        result = compare_files(args.left, args.right, args.report, args.tolerance, args.blender)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result["passed"] else 1
    else:
        shot = shot_at(args.shot)
        style = style_at(args.style, args.style_dir)
        result = execute(args.command, shot, style, getattr(args, "output", None), args.blender)
        if result is not None:
            print(result)
    return 0


def entrypoint():
    try:
        return main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"motionbase: {error}", file=sys.stderr)
        return 1
