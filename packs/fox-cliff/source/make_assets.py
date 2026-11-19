"""Rebuild the fox-cliff Blender assets without importing the MotionBase engine."""

import argparse
import sys
from pathlib import Path

import bpy

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))
import character
import choreography
import stage


def build(destination):
    destination = Path(destination).resolve()
    for name in ("characters", "actions", "stages"):
        (destination / name).mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection, rig = character.build()
    bpy.data.libraries.write(
        str(destination / "characters/fox.blend"),
        {collection}, fake_user=True, compress=True,
    )
    action = choreography.build(rig)
    bpy.data.libraries.write(
        str(destination / "actions/leap.blend"),
        {action}, fake_user=True, compress=True,
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = stage.build()
    bpy.data.libraries.write(
        str(destination / "stages/cliff.blend"),
        {collection}, fake_user=True, compress=True,
    )
    print("Wrote fox-cliff assets to", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SOURCE.parent)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    build(args.output)
