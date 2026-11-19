import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from motionbase.cli import main
from test_project import ProjectFixture

ROOT = Path(__file__).resolve().parents[1]


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = ProjectFixture(Path(self.temporary.name))

    def command(self, *arguments):
        # All commands in this suite must work without starting Blender.
        environment = dict(os.environ, BLENDER_BIN=str(self.fixture.root / "no-blender"))
        return subprocess.run([sys.executable, "-m", "motionbase", *map(str, arguments)],
                              cwd=ROOT, env=environment, capture_output=True, text=True)

    def test_importing_package_cli_and_contracts_never_imports_bpy(self):
        code = ("import sys; import motionbase, motionbase.cli, motionbase.project, "
                "motionbase.runner, motionbase.comparison; assert 'bpy' not in sys.modules")
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_discovery_lists_compatibility_names_and_external_pack(self):
        result = self.command("styles", "--pack", self.fixture.pack_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue({"moon-cel", "woodblock", "demo:look", "demo:alternate"} <= set(result.stdout.splitlines()))
        assets = self.command("assets", "--pack", self.fixture.pack_path)
        self.assertEqual(assets.returncode, 0, assets.stderr)
        self.assertEqual(json.loads(assets.stdout)["id"], "demo")

    def test_cli_lock_compile_round_trip_returns_machine_readable_paths(self):
        locked = self.command("lock", self.fixture.project_path)
        self.assertEqual(locked.returncode, 0, locked.stderr)
        self.assertEqual(Path(locked.stdout.strip()), self.fixture.production / "project.lock.json")
        output = self.fixture.production / "build" / "010.json"
        compiled = self.command("compile", self.fixture.project_path, "--shot", "010",
                                "--style", "demo:alternate", "-o", output)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        receipt = json.loads(compiled.stdout)
        self.assertEqual(receipt["style_id"], "demo:alternate")
        self.assertTrue(Path(receipt["shot"]).is_file())
        self.assertTrue(Path(receipt["style"]).is_file())
        self.assertEqual(len(receipt["lock_sha256"]), 64)

    def test_missing_lock_is_an_actionable_cli_failure(self):
        output = self.fixture.production / "build" / "010.json"
        result = self.command("compile", self.fixture.project_path, "--shot", "010", "-o", output)
        self.assertEqual(result.returncode, 1)
        self.assertIn("motionbase lock", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(output.exists())

    def test_comparison_failure_returns_nonzero_with_json_report(self):
        report = {"version": 1, "passed": False, "mismatch_count": 1}
        output = io.StringIO()
        with patch("motionbase.cli.compare_files", return_value=report), contextlib.redirect_stdout(output):
            status = main(["compare", "before.blend", "after.blend", "--report", "report.json"])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue()), report)


if __name__ == "__main__":
    unittest.main()
