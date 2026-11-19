import copy
import json
import tempfile
import unittest
from pathlib import Path

from motionbase.config import shot_at, style_at, validate_shot
from motionbase.io import read_json


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ("stage.blend", "character.blend", "action.blend", "audio.wav"):
            (self.root / name).write_bytes(b"configuration-test-placeholder")
        self.shot = {
            "version": 1, "fps": 30, "frames": 150, "size": [960, 540],
            "stage": {"file": "stage.blend", "collection": "Stage", "camera": "Camera"},
            "actors": [{"id": "hero", "file": "character.blend", "collection": "Character", "rig": "Rig",
                        "clips": [{"file": "action.blend", "action": "Move", "start": 1, "end": 150}]}],
            "audio": "audio.wav",
        }

    def test_legacy_v1_resolves_relative_paths_without_mutating_input(self):
        before = copy.deepcopy(self.shot)
        result = validate_shot(self.shot, self.root)
        self.assertEqual(self.shot, before)
        self.assertEqual(result["stage"]["file"], str(self.root / "stage.blend"))
        self.assertEqual(result["actors"][0]["position"], [0, 0, 0])
        self.assertEqual(result["audio"], str(self.root / "audio.wav"))

    def test_wrong_types_unknown_fields_and_invalid_dimensions_fail(self):
        variants = [
            {"fps": True}, {"frames": 0}, {"samples": 1.0}, {"size": [961, 540]},
            {"size": [960]}, {"actors": {}}, {"version": True}, {"metadata": {}},
        ]
        for override in variants:
            with self.subTest(override=override), self.assertRaises(ValueError):
                validate_shot({**self.shot, **override}, self.root)

    def test_duplicate_actors_and_overlapping_clips_fail(self):
        duplicate = copy.deepcopy(self.shot)
        duplicate["actors"].append(copy.deepcopy(duplicate["actors"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate actor"):
            validate_shot(duplicate, self.root)
        overlapping = copy.deepcopy(self.shot)
        overlapping["actors"][0]["clips"].append(
            {"file": "action.blend", "action": "Move", "start": 150, "end": 150}
        )
        with self.assertRaisesRegex(ValueError, "non-overlapping"):
            validate_shot(overlapping, self.root)

    def test_unknown_trail_actor_and_unbounded_intervals_fail(self):
        trail = {"actor": "unknown", "bone": "root", "inner": [0, 0, 0], "outer": [0, 0, 1],
                 "role": "trail", "start": 1, "end": 10, "history": 3}
        with self.assertRaisesRegex(ValueError, "Unknown trail actor"):
            validate_shot({**self.shot, "trails": [trail]}, self.root)
        with self.assertRaisesRegex(ValueError, "outside shot"):
            validate_shot({**self.shot, "trails": [{**trail, "actor": "hero", "end": 151}]}, self.root)

    def test_missing_file_and_mixed_asset_reference_fail(self):
        (self.root / "action.blend").unlink()
        with self.assertRaisesRegex(ValueError, "missing asset"):
            validate_shot(self.shot, self.root)
        changed = copy.deepcopy(self.shot)
        changed["stage"]["asset"] = "demo:stage"
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            validate_shot(changed, self.root)

    def test_static_environment_shot_is_valid(self):
        result = validate_shot({**self.shot, "actors": [], "frames": 1}, self.root)
        self.assertEqual(result["frames"], 1)

    def test_builtin_style_names_remain_compatible(self):
        cel, paper = style_at("moon-cel"), style_at("woodblock")
        self.assertEqual(cel["palette"].keys(), paper["palette"].keys())
        self.assertNotEqual(cel["shading"], paper["shading"])

    def test_external_styles_and_material_paths_are_resolved_locally(self):
        style = style_at("moon-cel")
        style["name"] = "Local style"
        style["materials"] = {"file": "materials.blend", "roles": {"coat": "Custom coat"}}
        (self.root / "materials.blend").touch()
        (self.root / "local.json").write_text(json.dumps(style))
        loaded = style_at("local", [self.root])
        self.assertEqual(loaded["name"], "Local style")
        self.assertEqual(loaded["materials"]["file"], str(self.root / "materials.blend"))

    def test_invalid_style_values_fail_before_blender(self):
        for override in ({"light": [0, 0, 0]}, {"grain": 2}, {"palette": {"sky": "#FFFFFF"}},
                         {"shading": []}, {"unknown": "field"}):
            with self.subTest(override=override):
                path = self.root / "invalid.json"
                path.write_text(json.dumps({**style_at("moon-cel"), **override}))
                with self.assertRaises(ValueError):
                    style_at(path)

    def test_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for content in ('{"version":1,"version":1}', '{"value":NaN}', '{"value":Infinity}'):
            path = self.root / "invalid.json"
            path.write_text(content)
            with self.subTest(content=content), self.assertRaises(ValueError):
                read_json(path)


if __name__ == "__main__":
    unittest.main()
