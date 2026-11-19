"""Runs in an isolated Blender process. Importing the CLI never initializes bpy."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from motionbase.look import apply_look, linear_rgb
from motionbase.trails import bake


def require_blender():
    """Keep the Action-slot contract explicit before reading any asset."""
    if bpy.app.version < (4, 5, 0):
        raise RuntimeError(
            f"MotionBase requires Blender 4.5 or newer; found {bpy.app.version_string}. "
            "Use Blender 4.5 LTS through --blender or BLENDER_BIN."
        )


def append(file, kind, name):
    with bpy.data.libraries.load(file, link=False) as (source, dest):
        if name not in getattr(source, kind):
            raise ValueError(f"{file}: missing {kind}/{name}")
        setattr(dest, kind, [name])
    return getattr(dest, kind)[0]


def member(collection, name, kind):
    # Blender uniquifies names on append; stable IDs keep repeated instances independent.
    found = [
        o
        for o in collection.all_objects
        if o.type == kind and (o.get("motionbase_id", o.name) == name or o.name == name)
    ]
    if len(found) != 1:
        raise ValueError(
            f"{collection.name}: expected one {kind} with asset id {name!r}, found {len(found)}"
        )
    return found[0]


def animate(rig, clips):
    rig.animation_data_clear()
    track = rig.animation_data_create().nla_tracks.new()
    track.name = "Shot clips"
    for clip in clips:
        action = append(clip["file"], "actions", clip["action"])
        if len(action.slots) != 1:
            raise ValueError(f"{action.name}: a clip must target one object action slot")
        slot = action.slots[0]
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                for curve in bag.fcurves if bag else ():
                    try:
                        rig.path_resolve(curve.data_path)
                    except ValueError as exc:
                        raise ValueError(
                            f"{rig.name} cannot bind {action.name}: {curve.data_path}"
                        ) from exc
        native = track.strips.new(clip["action"], clip["start"], action)
        native.action_slot = slot
        native.extrapolation = "NOTHING"
        # Blender strip end is inclusive for evaluation. A hold occupies one scene frame.
        native.frame_end = max(clip["end"], clip["start"] + 0.001)


def run(jobfile):
    require_blender()
    jobfile = Path(jobfile)
    job = json.loads(jobfile.read_text(encoding="utf-8"))
    shot, style = job["shot"], job["style"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, shot["frames"]
    scene.render.fps = shot["fps"]
    scene.render.resolution_x, scene.render.resolution_y = shot["size"]
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = shot.get("samples", 2)
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_animated_seed = False
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("Backdrop")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        *linear_rgb(style["palette"]["sky"]),
        1,
    )
    spec = shot["stage"]
    stage = append(spec["file"], "collections", spec["collection"])
    scene.collection.children.link(stage)
    scene.camera = member(stage, spec["camera"], "CAMERA")
    rigs = {}
    for actor in shot["actors"]:
        coll = append(actor["file"], "collections", actor["collection"])
        scene.collection.children.link(coll)
        rig = member(coll, actor["rig"], "ARMATURE")
        anchor = bpy.data.objects.new(actor["id"], None)
        anchor["motionbase_actor_id"] = actor["id"]
        rig["motionbase_actor_id"] = actor["id"]
        scene.collection.objects.link(anchor)
        for obj in coll.all_objects:
            if obj.parent is None:
                obj.parent = anchor
        anchor.location = actor["position"]
        animate(rig, actor["clips"])
        rigs[actor["id"]] = rig
    for effect in shot.get("trails", []):
        bake(scene, rigs[effect["actor"]], effect)
    apply_look(list(scene.objects), style)
    scene.frame_set(1)
    if job["command"] == "check":
        print(f"Validated {len(rigs)} actor(s), {shot['frames']} frames, look {style['name']}")
        return
    if job["command"] == "build":
        if shot.get("audio"):
            scene.sequence_editor_create().strips.new_sound("Shot audio", shot["audio"], 1, 1)
            scene.render.use_sequencer = False
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(
            filepath=str(jobfile.parent / "result.blend"), compress=True
        )
        return
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 12
    scene.render.filepath = str(jobfile.parent / "frame-")
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    run(Path(sys.argv[sys.argv.index("--") + 1]))
