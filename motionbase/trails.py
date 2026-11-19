"""Bake a tapered surface between two bone-local points into native shape keys."""

import bpy
from mathutils import Vector


def bake(scene, rig, spec):
    count, start, end = spec["history"], spec["start"], spec["end"]
    name = f"{rig.name} / {spec['role']}"
    bone = spec["bone"]
    if bone not in rig.pose.bones:
        raise ValueError(f"{name}: no bone {bone!r}")
    points = [Vector(spec[k]) for k in ("inner", "outer")]
    samples = {}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        mat = rig.matrix_world @ rig.pose.bones[bone].matrix
        samples[frame] = [mat @ p for p in points]

    def vertices(frame):
        coords = []
        for age in range(count + 1):
            left, right = samples[max(start, frame - age)]
            width = (1 - age / count) ** 0.7 * min(1, (end - frame) / max(1, count / 2))
            coords.extend([right.lerp(left, width), right])
        return coords

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(
        vertices(start), [], [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(count)]
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    mat = bpy.data.materials.new(spec["role"])
    mat["motionbase_role"], mat["motionbase_flat"] = spec["role"], True
    obj.data.materials.append(mat)
    basis = obj.shape_key_add(name="Start")
    keys = obj.data.shape_keys
    keys.use_relative = False
    basis.interpolation = "KEY_LINEAR"
    for frame in range(start, end + 1):
        key = basis if frame == start else obj.shape_key_add(name=f"F{frame:03d}")
        key.interpolation = "KEY_LINEAR"
        for idx, pt in enumerate(vertices(frame)):
            key.data[idx].co = pt
        keys.eval_time = key.frame
        keys.keyframe_insert("eval_time", frame=frame)
    for frame, hidden in [(start - 1, True), (start, False), (end, False), (end + 1, True)]:
        obj.hide_render = hidden
        obj.hide_viewport = hidden
        obj.keyframe_insert("hide_render", frame=frame)
        obj.keyframe_insert("hide_viewport", frame=frame)
    return obj
