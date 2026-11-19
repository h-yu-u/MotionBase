"""Generate tiny redistributable Blender assets, independent of any art pack."""

import math
from pathlib import Path

import bpy


def make_fixture(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    character = bpy.data.collections.new("TestCharacter")
    bpy.context.scene.collection.children.link(character)
    armature = bpy.data.armatures.new("TestArmature")
    rig = bpy.data.objects.new("TestRig", armature)
    rig["motionbase_id"] = "test-rig"
    character.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    root = armature.edit_bones.new("root")
    root.head, root.tail = (0, 0, 0), (0, 0, 1)
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh = bpy.data.meshes.new("TestTriangle")
    mesh.from_pydata([(-0.3, 0, 0), (0.3, 0, 0), (0, 0, 0.7)], [], [(0, 1, 2)])
    mesh.update()
    prop = bpy.data.objects.new("TestProp", mesh)
    prop.parent, prop.parent_type, prop.parent_bone = rig, "BONE", "root"
    character.objects.link(prop)
    material = bpy.data.materials.new("TestBody")
    material["motionbase_role"] = "body"
    prop.data.materials.append(material)
    character_path = directory / "character.blend"
    bpy.data.libraries.write(str(character_path), {character}, fake_user=True)

    for frame, x in [(1, 0.0), (12, 1.0)]:
        rig.pose.bones["root"].location.x = x
        rig.pose.bones["root"].keyframe_insert("location", frame=frame)
    action = rig.animation_data.action
    action.name = "TestMove"
    action_path = directory / "action.blend"
    bpy.data.libraries.write(str(action_path), {action}, fake_user=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    stage = bpy.data.collections.new("TestStage")
    bpy.context.scene.collection.children.link(stage)
    camera = bpy.data.objects.new("TestCamera", bpy.data.cameras.new("TestCamera"))
    camera["motionbase_id"] = "test-camera"
    camera.location = (0, -6, 1)
    camera.rotation_euler = (math.pi / 2, 0, 0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4
    stage.objects.link(camera)
    stage_path = directory / "stage.blend"
    bpy.data.libraries.write(str(stage_path), {stage}, fake_user=True)
    shot = {
        "version": 1,
        "fps": 24,
        "frames": 12,
        "size": [64, 64],
        "samples": 1,
        "stage": {"file": str(stage_path), "collection": "TestStage", "camera": "test-camera"},
        "actors": [{
            "id": "first",
            "file": str(character_path),
            "collection": "TestCharacter",
            "rig": "test-rig",
            "position": [0, 0, 0],
            "clips": [{"file": str(action_path), "action": "TestMove", "start": 1, "end": 12}],
        }],
        "trails": [{
            "actor": "first", "bone": "root", "inner": [0, 0, 0],
            "outer": [0.2, 0, 0.5], "role": "effect", "start": 2, "end": 10, "history": 3,
        }],
    }
    style = {
        "version": 1, "name": "Test look", "shading": "bands", "light": [0.3, -0.6, 0.8],
        "shadow": 0.5, "rim": 0.1, "grain": 0,
        "palette": {"sky": "#EEEEEE", "ink": "#222222", "body": "#E06040", "effect": "#E0C060"},
    }
    return shot, style
