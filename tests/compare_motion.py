"""Compatibility entry point: Blender -b -P tests/compare_motion.py -- A.blend B.blend."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motionbase.comparison import compare


if __name__ == "__main__":
    paths = sys.argv[sys.argv.index("--") + 1 :]
    if len(paths) != 2:
        raise ValueError("Expected exactly two .blend paths")
    report = compare(*paths)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise AssertionError("Motion or framing changed; see comparison report")
