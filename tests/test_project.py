"""Project contracts are tested without Blender or example art assets."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from motionbase.assets import AssetPack
from motionbase.project import Project, engine_fingerprint


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ProjectFixture:
    """Placeholder .blend bytes are used only by configuration checks, never Blender."""

    def __init__(self, root):
        self.root = Path(root)
        self.pack_root = self.root / "art"
        self.production = self.root / "production"
        self.pack_path = self.pack_root / "pack.json"
        self.project_path = self.production / "project.json"
        self.shot_path = self.production / "shots" / "010.json"
        self.pack_root.mkdir(parents=True)
        for name in ("stage.blend", "character.blend", "action.blend", "materials.blend", "audio.wav"):
            (self.pack_root / name).write_bytes(b"configuration-test-placeholder:" + name.encode())
        self.style = {
            "version": 1, "name": "Test look", "shading": "bands", "light": [1, -1, 1],
            "shadow": 0.5, "rim": 0.1, "grain": 0,
            "palette": {"sky": "#EEEEEE", "ink": "#222222", "body": "#E06040"},
            "materials": {"file": "materials.blend", "roles": {"body": "Custom body"}},
        }
        write(self.pack_root / "look.json", self.style)
        write(self.pack_root / "alternate.json", {**self.style, "name": "Alternate", "grain": 0.2})
        self.pack = {
            "version": 1, "id": "demo", "revision": "1.0.0", "blender": "4.5",
            "assets": {
                "stage": {"kind": "stage", "file": "stage.blend", "collection": "Stage", "camera": "Camera"},
                "hero": {"kind": "character", "file": "character.blend", "collection": "Hero", "rig": "Rig", "rig_id": "demo-rig-v1"},
                "move": {"kind": "action", "file": "action.blend", "action": "Move", "rig_id": "demo-rig-v1"},
                "look": {"kind": "style", "file": "look.json"},
                "alternate": {"kind": "style", "file": "alternate.json"},
                "sound": {"kind": "audio", "file": "audio.wav"},
            },
        }
        self.shot = {
            "version": 1, "fps": 30, "frames": 150, "size": [960, 540],
            "stage": {"asset": "demo:stage"},
            "actors": [{"id": "hero", "asset": "demo:hero", "clips": [{"asset": "demo:move", "start": 1, "end": 150}]}],
            "audio": {"asset": "demo:sound"},
        }
        self.project = {
            "version": 1, "id": "test-production", "packs": {"demo": "../art/pack.json"},
            "shots": {"010": {"file": "shots/010.json", "style": "demo:look"}},
        }
        self.save()

    def save(self):
        write(self.pack_path, self.pack)
        write(self.shot_path, self.shot)
        write(self.project_path, self.project)


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = ProjectFixture(Path(self.temporary.name))

    def test_compilation_requires_a_lock(self):
        project = Project(self.fixture.project_path)
        output = self.fixture.production / "build" / "010.json"
        with self.assertRaisesRegex(ValueError, "Missing.*project.lock"):
            project.compile("010", output)
        self.assertFalse(output.exists())

    def test_locked_compile_resolves_ids_without_changing_inputs(self):
        project = Project(self.fixture.project_path)
        project.lock()
        originals = {path: path.read_bytes() for path in (self.fixture.project_path, self.fixture.shot_path, self.fixture.pack_path, project.lock_path)}
        result = project.compile("010", self.fixture.production / "build" / "010.json")
        shot = json.loads(Path(result["shot"]).read_text())
        style = json.loads(Path(result["style"]).read_text())
        self.assertEqual(shot["stage"]["file"], str(self.fixture.pack_root / "stage.blend"))
        self.assertEqual(shot["actors"][0]["clips"][0]["action"], "Move")
        self.assertNotIn("asset", shot["actors"][0])
        self.assertEqual(style["materials"]["file"], str(self.fixture.pack_root / "materials.blend"))
        for path, contents in originals.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_style_override_uses_locked_pack_and_preserves_motion(self):
        project = Project(self.fixture.project_path)
        project.lock()
        first = project.compile("010", self.fixture.production / "build" / "first.json")
        second = project.compile("010", self.fixture.production / "build" / "second.json", "demo:alternate")
        self.assertEqual(Path(first["shot"]).read_bytes(), Path(second["shot"]).read_bytes())
        self.assertEqual(second["style_id"], "demo:alternate")
        self.assertNotEqual(Path(first["style"]).read_bytes(), Path(second["style"]).read_bytes())
        with self.assertRaisesRegex(ValueError, "Unknown asset pack"):
            project.compile("010", self.fixture.production / "build" / "unknown.json", "other:look")

    def test_incompatible_rig_is_rejected_before_lock(self):
        self.fixture.pack["assets"]["move"]["rig_id"] = "other-rig"
        self.fixture.save()
        project = Project(self.fixture.project_path)
        with self.assertRaisesRegex(ValueError, "incompatible rigs"):
            project.lock()
        self.assertFalse(project.lock_path.exists())

    def test_assets_cannot_escape_pack_root(self):
        outside = self.fixture.root / "outside.blend"
        outside.write_bytes(b"outside")
        self.fixture.pack["assets"]["hero"]["file"] = "../outside.blend"
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "escapes"):
            AssetPack(self.fixture.pack_path)
        self.fixture.pack["assets"]["hero"]["file"] = str(outside)
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "relative"):
            AssetPack(self.fixture.pack_path)

    def test_material_library_cannot_escape_pack_root(self):
        outside = self.fixture.root / "outside.blend"
        outside.write_bytes(b"outside material")
        self.fixture.style["materials"]["file"] = "../outside.blend"
        write(self.fixture.pack_root / "look.json", self.fixture.style)
        with self.assertRaises(ValueError):
            AssetPack(self.fixture.pack_path)

    def test_symlink_escape_is_rejected(self):
        outside = self.fixture.root / "outside.blend"
        outside.write_bytes(b"outside")
        link = self.fixture.pack_root / "linked.blend"
        try:
            link.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"Symlink unavailable: {error}")
        self.fixture.pack["assets"]["hero"]["file"] = "linked.blend"
        self.fixture.save()
        with self.assertRaisesRegex(ValueError, "escapes"):
            AssetPack(self.fixture.pack_path)

    def test_lock_detects_asset_style_and_material_dependency_drift(self):
        for filename in ("action.blend", "look.json", "materials.blend"):
            with self.subTest(filename=filename):
                project = Project(self.fixture.project_path)
                project.lock()
                path = self.fixture.pack_root / filename
                original = path.read_bytes()
                if filename.endswith(".json"):
                    changed = json.loads(original)
                    changed["grain"] = 0.3
                    write(path, changed)
                else:
                    path.write_bytes(original + b"changed")
                with self.assertRaisesRegex(ValueError, "stale.*packs"):
                    Project(self.fixture.project_path).verify()
                path.write_bytes(original)

    def test_lock_detects_project_shot_manifest_and_engine_drift(self):
        for kind in ("project", "shot", "manifest", "engine"):
            with self.subTest(kind=kind):
                self.fixture.save()
                project = Project(self.fixture.project_path)
                project.lock()
                if kind == "project":
                    data = copy.deepcopy(self.fixture.project)
                    data["shots"]["010"]["style"] = "demo:alternate"
                    write(self.fixture.project_path, data)
                elif kind == "shot":
                    write(self.fixture.shot_path, {**self.fixture.shot, "samples": 4})
                elif kind == "manifest":
                    write(self.fixture.pack_path, {**self.fixture.pack, "revision": "1.0.1"})
                else:
                    changed = {**engine_fingerprint(), "source_sha256": "0" * 64}
                    with patch("motionbase.project.engine_fingerprint", return_value=changed):
                        with self.assertRaisesRegex(ValueError, "stale.*engine"):
                            project.verify()
                    continue
                with self.assertRaisesRegex(ValueError, "stale"):
                    Project(self.fixture.project_path).verify()

    def test_lock_records_material_library_hash_and_rejects_extra_fields(self):
        project = Project(self.fixture.project_path)
        project.lock()
        locked = json.loads(project.lock_path.read_text())
        self.assertIn("materials.blend", locked["packs"]["demo"]["files"])
        locked["untracked"] = True
        write(project.lock_path, locked)
        with self.assertRaisesRegex(ValueError, "stale.*untracked"):
            project.verify()

    def test_compile_cannot_overwrite_any_input(self):
        project = Project(self.fixture.project_path)
        project.lock()
        protected = [self.fixture.project_path, self.fixture.shot_path, self.fixture.pack_path,
                     self.fixture.pack_root / "look.json", project.lock_path]
        for output in protected:
            original = output.read_bytes()
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "must not overwrite"):
                project.compile("010", output)
            self.assertEqual(output.read_bytes(), original)
        # The companion .style.json output is protected independently of the shot output.
        other_shot = self.fixture.production / "shots" / "alternate.style.json"
        write(other_shot, self.fixture.shot)
        self.fixture.project["shots"]["020"] = {"file": "shots/alternate.style.json", "style": "demo:look"}
        self.fixture.save()
        project = Project(self.fixture.project_path)
        project.lock()
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            project.compile("010", other_shot.with_name("alternate.json"))

    def test_compile_companion_symlink_cannot_overwrite_source_shot(self):
        project = Project(self.fixture.project_path)
        project.lock()
        output = self.fixture.production / "build" / "010.json"
        output.parent.mkdir()
        companion = output.with_name("010.style.json")
        try:
            companion.symlink_to(self.fixture.shot_path)
        except OSError as error:
            self.skipTest(f"Symlink unavailable: {error}")
        original = self.fixture.shot_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            project.compile("010", output)
        self.assertEqual(self.fixture.shot_path.read_bytes(), original)
        self.assertTrue(companion.is_symlink())
        self.assertFalse(output.exists())

    def test_compile_outputs_cannot_alias_each_other(self):
        project = Project(self.fixture.project_path)
        project.lock()
        output = self.fixture.production / "build" / "010.json"
        write(output, {"previous": "compiled shot"})
        companion = output.with_name("010.style.json")
        try:
            companion.symlink_to(output)
        except OSError as error:
            self.skipTest(f"Symlink unavailable: {error}")
        original = output.read_bytes()
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            project.compile("010", output)
        self.assertEqual(output.read_bytes(), original)
        self.assertTrue(companion.is_symlink())

    def test_lock_symlink_cannot_overwrite_source_shot(self):
        project = Project(self.fixture.project_path)
        try:
            project.lock_path.symlink_to(self.fixture.shot_path)
        except OSError as error:
            self.skipTest(f"Symlink unavailable: {error}")
        original = self.fixture.shot_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            project.lock()
        self.assertEqual(self.fixture.shot_path.read_bytes(), original)
        self.assertTrue(project.lock_path.is_symlink())

    def test_lock_cannot_overwrite_project_named_as_lock(self):
        project_path = self.fixture.production / "project.lock.json"
        self.fixture.project_path.rename(project_path)
        original = project_path.read_bytes()
        project = Project(project_path)
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            project.lock()
        self.assertEqual(project_path.read_bytes(), original)

    def test_unknown_and_wrong_type_fields_fail_before_lock(self):
        for override in ({"unknown": True}, {"packs": []}, {"shots": []}, {"id": "Invalid ID"}):
            with self.subTest(override=override):
                write(self.fixture.project_path, {**self.fixture.project, **override})
                with self.assertRaises(ValueError):
                    Project(self.fixture.project_path)
        self.fixture.save()
        self.fixture.pack["assets"]["stage"]["kind"] = []
        self.fixture.save()
        with self.assertRaises(ValueError):
            AssetPack(self.fixture.pack_path)


if __name__ == "__main__":
    unittest.main()
