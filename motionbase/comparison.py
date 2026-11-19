"""Compare evaluated motion and framing in two Blender projects.

Importing this module does not import bpy. ``compare`` runs inside Blender;
``run`` is the isolated worker entry point used by the normal Python CLI.
Art direction, materials and rendered appearance are deliberately not compared.
"""

import json
import math
import sys
from pathlib import Path


def _flatten(matrix):
    return tuple(float(value) for row in matrix for value in row)


def _actor_id(rig):
    """Use authored actor IDs; accept anchors from pre-split MotionBase files."""
    if rig.get("motionbase_actor_id"):
        return str(rig["motionbase_actor_id"])
    if rig.parent is not None:
        return str(rig.parent.get("motionbase_actor_id", rig.parent.name))
    return str(rig.get("motionbase_id", rig.name))


def _signature(path):
    import bpy

    if bpy.app.version < (4, 5, 0):
        raise RuntimeError(
            f"MotionBase comparison requires Blender 4.5 or newer; found {bpy.app.version_string}. "
            "Use Blender 4.5 LTS through --blender or BLENDER_BIN."
        )
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    if scene.camera is None:
        raise ValueError(f"{path}: scene has no active camera")
    render = scene.render
    framing = {
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "frame_step": scene.frame_step,
        "fps": render.fps,
        "fps_base": render.fps_base,
        "resolution_x": render.resolution_x,
        "resolution_y": render.resolution_y,
        "resolution_percentage": render.resolution_percentage,
        "pixel_aspect_x": render.pixel_aspect_x,
        "pixel_aspect_y": render.pixel_aspect_y,
        "use_border": render.use_border,
        "use_crop_to_border": render.use_crop_to_border,
        "border_min_x": render.border_min_x,
        "border_min_y": render.border_min_y,
        "border_max_x": render.border_max_x,
        "border_max_y": render.border_max_y,
    }
    rigs = {}
    for rig in scene.objects:
        if rig.type != "ARMATURE":
            continue
        key = _actor_id(rig)
        if key in rigs:
            raise ValueError(f"{path}: duplicate comparison actor ID {key!r}")
        rigs[key] = rig
    topology = {key: sorted(bone.name for bone in rig.pose.bones) for key, rig in rigs.items()}
    frames = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        camera = scene.camera.evaluated_get(graph)
        camera_data = camera.data
        camera_values = {
            "type": camera_data.type,
            "lens": camera_data.lens,
            "ortho_scale": camera_data.ortho_scale,
            "shift_x": camera_data.shift_x,
            "shift_y": camera_data.shift_y,
            "sensor_fit": camera_data.sensor_fit,
            "sensor_width": camera_data.sensor_width,
            "sensor_height": camera_data.sensor_height,
            "clip_start": camera_data.clip_start,
            "clip_end": camera_data.clip_end,
        }
        projection = _flatten(camera.calc_matrix_camera(
            graph,
            x=render.resolution_x,
            y=render.resolution_y,
            scale_x=render.pixel_aspect_x,
            scale_y=render.pixel_aspect_y,
        ))
        matrices = {("camera",): _flatten(camera.matrix_world)}
        for key, original in sorted(rigs.items()):
            rig = original.evaluated_get(graph)
            matrices[("actor", key)] = _flatten(rig.matrix_world)
            for bone in sorted(rig.pose.bones, key=lambda item: item.name):
                matrices[("actor", key, "bone", bone.name)] = _flatten(rig.matrix_world @ bone.matrix)
        frames.append({"frame": frame, "matrices": matrices, "camera": camera_values, "projection": projection})
    return {"framing": framing, "actors": topology, "frames": frames}


def compare(left, right, tolerance=1e-5):
    """Return an audit report, allowing still shots and scenes without actors."""
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Comparison tolerance must be a finite non-negative number")
    a, b = _signature(left), _signature(right)
    mismatches = []
    mismatch_count = 0
    max_matrix_delta = 0.0
    max_camera_delta = 0.0

    def record(category, path, before, after, frame=None, delta=None):
        nonlocal mismatch_count
        mismatch_count += 1
        if len(mismatches) < 50:
            entry = {"category": category, "path": path, "left": before, "right": after}
            if frame is not None:
                entry["frame"] = frame
            if delta is not None:
                entry["delta"] = delta
            mismatches.append(entry)

    for key in a["framing"]:
        if a["framing"][key] != b["framing"][key]:
            record("framing", key, a["framing"][key], b["framing"][key])
    if a["actors"] != b["actors"]:
        record("actors", "actor IDs and bone names", a["actors"], b["actors"])

    frames_compared = 0
    if (a["framing"]["frame_start"], a["framing"]["frame_end"]) == (
        b["framing"]["frame_start"], b["framing"]["frame_end"]
    ):
        for before, after in zip(a["frames"], b["frames"]):
            frames_compared += 1
            frame = before["frame"]
            if before["matrices"].keys() == after["matrices"].keys():
                for key, values in before["matrices"].items():
                    other = after["matrices"][key]
                    label = "/".join(key)
                    if not all(math.isfinite(v) for v in (*values, *other)):
                        record("motion", label, "non-finite or invalid matrix", "non-finite or invalid matrix", frame)
                        continue
                    delta = max(abs(x - y) for x, y in zip(values, other))
                    max_matrix_delta = max(max_matrix_delta, delta)
                    if delta > tolerance:
                        record("motion", label, list(values), list(other), frame, delta)
            for key, value in before["camera"].items():
                other = after["camera"][key]
                if isinstance(value, (int, float)):
                    if not (math.isfinite(value) and math.isfinite(other)):
                        record("camera", key, "non-finite value", "non-finite value", frame)
                        continue
                    delta = abs(value - other)
                    max_camera_delta = max(max_camera_delta, delta)
                    if delta > tolerance:
                        record("camera", key, value, other, frame, delta)
                elif value != other:
                    record("camera", key, value, other, frame)
            values, other = before["projection"], after["projection"]
            if not all(math.isfinite(v) for v in (*values, *other)):
                record("camera", "projection", "non-finite matrix", "non-finite matrix", frame)
            else:
                delta = max(abs(x - y) for x, y in zip(values, other))
                max_camera_delta = max(max_camera_delta, delta)
                if delta > tolerance:
                    record("camera", "projection", list(values), list(other), frame, delta)
    return {
        "version": 1,
        "passed": mismatch_count == 0,
        "left": str(Path(left).resolve()),
        "right": str(Path(right).resolve()),
        "tolerance": tolerance,
        "frames_compared": frames_compared,
        "max_matrix_delta": max_matrix_delta,
        "max_camera_delta": max_camera_delta,
        "mismatch_count": mismatch_count,
        "mismatches": mismatches,
        "mismatches_truncated": mismatch_count > len(mismatches),
    }


def run(jobfile):
    """Write the report even when comparison fails; let the CLI choose its exit code."""
    job = json.loads(Path(jobfile).read_text(encoding="utf-8"))
    result = compare(job["left"], job["right"], job.get("tolerance", 1e-5))
    target = Path(job["report"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    run(Path(sys.argv[sys.argv.index("--") + 1]))
