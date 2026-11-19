"""Integration regression for reusable actions, repeated actors and material libraries.

Run with Blender 4.5 LTS; use -- --engine-root PATH for a source checkout.
"""

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

import bpy

pack = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--engine-root", type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
if args.engine_root:
    sys.path.insert(0, str(args.engine_root.resolve()))
from motionbase.config import shot_at, style_at
from motionbase.worker import run
from motionbase.look import linear_rgb


with tempfile.TemporaryDirectory() as temporary:
    tmp = Path(temporary)
    shot = shot_at(pack / "tests/shot.json")
    shot.pop("audio", None)
    actor = copy.deepcopy(shot["actors"][0])
    actor["id"] = "echo"
    actor["position"] = [2.0, 0.3, 0]
    actor["clips"] = [dict(actor["clips"][0], start=31, end=105)]
    shot["actors"].append(actor)
    material = bpy.data.materials.new("Custom enamel")
    material.diffuse_color = (1.0, 0.1, 0.6, 1)
    custom_file = tmp / "look.blend"
    bpy.data.libraries.write(str(custom_file), {material}, fake_user=True)
    style = style_at(pack / "looks/moon-cel.json")
    style["materials"] = {"file": str(custom_file), "roles": {"mask": "Custom enamel"}}
    path = tmp / "job.json"
    path.write_text(json.dumps(dict(shot=shot, style=style, command="check")))
    run(path)
    scene = bpy.context.scene
    rigs = {o.parent.name: o for o in scene.objects if o.type == "ARMATURE"}
    assert set(rigs) == {"fox", "echo"}
    # At frame 105 the compressed 75-frame clip has reached the source's last pose.
    scene.frame_set(105)
    shortened = rigs["echo"].pose.bones["prop"].matrix.copy()
    scene.frame_set(150)
    original = rigs["fox"].pose.bones["prop"].matrix
    mismatch = max(
        abs(a - b) for row1, row2 in zip(shortened, original) for a, b in zip(row1, row2)
    )
    assert mismatch < 1e-4, f"Retimed action mismatch: {mismatch}"
    masks = [
        o
        for o in scene.objects
        if o.name.startswith("Fox mask") and not o.name.startswith("Fox mask outline")
    ]
    assert len(masks) == 2
    assert all(o.material_slots[0].material.name.startswith("Custom enamel") for o in masks)
    print(
        "Verified independent actor instances, clip retiming, and custom material replacement."
    )

    hair = next(o for o in scene.objects if o.name == "Hair")
    ramp = hair.data.materials[0].node_tree.nodes["Color Ramp"].color_ramp
    expected = linear_rgb(style["palette"]["hair"])
    assert all(abs(a - b) < 1e-6 for a, b in zip(ramp.elements[-1].color, expected))
