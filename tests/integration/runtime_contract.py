"""Run with Blender 4.5 LTS or Python with bpy: no art pack or network needed.

    blender -b --factory-startup --disable-autoexec --python-exit-code 1 \
        -P tests/integration/runtime_contract.py
"""

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy
from fixtures import make_fixture
from motionbase.comparison import compare, run as compare_job
from motionbase.worker import require_blender, run


def build(directory, shot, style):
    directory.mkdir(parents=True, exist_ok=True)
    job = directory / "job.json"
    job.write_text(json.dumps({"shot": shot, "style": style, "command": "build"}), encoding="utf-8")
    run(job)
    result = directory / "result.blend"
    assert result.is_file(), "Build did not produce .blend output"
    return result


def verify(directory):
    require_blender()
    shot, style = make_fixture(directory / "assets")
    baseline = build(directory / "baseline", shot, style)
    second_style = copy.deepcopy(style)
    second_style.update(name="Second look", shading="continuous", grain=0.2)
    second_style["palette"]["body"] = "#40A0D0"
    restyled = build(directory / "restyled", shot, second_style)
    report = compare(baseline, restyled)
    assert report["passed"], report
    assert report["frames_compared"] == 12
    assert report["max_matrix_delta"] == 0

    # Blender-generated object names may differ; the authored actor ID remains stable.
    for obj in bpy.context.scene.objects:
        if obj.type == "ARMATURE":
            obj.name = "Renamed rig"
            obj.parent.name = "Renamed anchor"
    renamed = directory / "renamed.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(renamed))
    assert compare(baseline, renamed)["passed"]

    # A change in framing must fail even when every world transform is unchanged.
    bpy.context.scene.camera.data.ortho_scale *= 1.1
    reframed = directory / "reframed.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(reframed))
    report = compare(baseline, reframed)
    assert not report["passed"]
    assert report["max_matrix_delta"] == 0
    assert report["max_camera_delta"] > 0
    assert any(item["category"] == "camera" for item in report["mismatches"])
    comparison_job = directory / "comparison.json"
    report_path = directory / "comparison-report.json"
    comparison_job.write_text(json.dumps({"left": str(baseline), "right": str(reframed), "report": str(report_path)}))
    compare_job(comparison_job)
    assert json.loads(report_path.read_text())["passed"] is False

    # Legacy builds without actor metadata are still comparable through their anchors.
    bpy.ops.wm.open_mainfile(filepath=str(baseline), load_ui=False, use_scripts=False)
    for obj in bpy.context.scene.objects:
        if "motionbase_actor_id" in obj:
            del obj["motionbase_actor_id"]
    legacy = directory / "legacy.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(legacy))
    assert compare(baseline, legacy)["passed"]

    # Test duplicate asset instances, NLA retiming, and material-library replacement.
    repeated = copy.deepcopy(shot)
    actor = copy.deepcopy(repeated["actors"][0])
    actor["id"], actor["position"] = "echo", [2, 0, 0]
    actor["clips"] = [dict(actor["clips"][0], start=3, end=8)]
    repeated["actors"].append(actor)
    custom = bpy.data.materials.new("Custom body")
    library = directory / "custom-material.blend"
    bpy.data.libraries.write(str(library), {custom}, fake_user=True)
    custom_style = copy.deepcopy(style)
    custom_style["materials"] = {"file": str(library), "roles": {"body": "Custom body"}}
    build(directory / "repeated", repeated, custom_style)
    scene = bpy.context.scene
    rigs = {obj["motionbase_actor_id"]: obj for obj in scene.objects if obj.type == "ARMATURE"}
    assert set(rigs) == {"first", "echo"}
    scene.frame_set(8)
    end_short = rigs["echo"].pose.bones["root"].matrix.copy()
    scene.frame_set(12)
    end_full = rigs["first"].pose.bones["root"].matrix.copy()
    delta = max(abs(x - y) for row, other in zip(end_short, end_full) for x, y in zip(row, other))
    assert delta < 1e-5, f"Retimed action changed its end pose: {delta}"
    meshes = [obj for obj in scene.objects if obj.name.startswith("TestProp")]
    assert len(meshes) == 2
    assert all(obj.material_slots[0].material.name.startswith("Custom body") for obj in meshes)

    # Static environment shots are valid comparisons, including a single frame.
    environment = copy.deepcopy(shot)
    environment.update(actors=[], trails=[], frames=1)
    still = build(directory / "still", environment, style)
    assert compare(still, still)["passed"]

    # Framing contracts include FPS, output dimensions and crop ranges.
    bpy.context.scene.render.fps += 1
    bpy.context.scene.render.resolution_x += 2
    bpy.context.scene.render.use_border = True
    bpy.context.scene.render.border_min_x = 0.1
    changed = directory / "output-changed.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(changed))
    report = compare(still, changed)
    assert not report["passed"]
    paths = {item["path"] for item in report["mismatches"]}
    assert {"fps", "resolution_x", "use_border", "border_min_x"} <= paths
    print("PASS: generic assets, repeated actors, retiming, materials, restyling, framing and still shots")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="motionbase-runtime-test-") as temporary:
        verify(Path(temporary))
