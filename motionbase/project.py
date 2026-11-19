"""Compile a locked production into the existing single-shot v1 contract."""

import copy
import hashlib
from pathlib import Path

from . import __version__
from .assets import AssetRegistry, identifier
from .config import document, existing_file, fields, list_at, object_at, style_at, validate_shot
from .io import sha256, write_json


def engine_fingerprint():
    """Include shipped Python and compatibility looks; ignore caches and checkout state."""
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    paths = sorted([*root.glob("*.py"), *root.glob("presets/*.json")])
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"version": __version__, "source_sha256": digest.hexdigest()}


class Project:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.root = self.path.parent
        self.data = document(self.path)
        fields(self.data, ("version", "id", "packs", "shots"), (), "project")
        identifier(self.data["id"], "project.id")
        packs = object_at(self.data["packs"], "project.packs")
        if not packs:
            raise ValueError("project.packs must not be empty")
        self.registry = AssetRegistry({
            key: existing_file(value, self.root, f"packs.{key}") for key, value in packs.items()
        })
        self.shots = object_at(self.data["shots"], "project.shots")
        if not self.shots:
            raise ValueError("project.shots must not be empty")
        self.shot_files = {}
        for key, spec in self.shots.items():
            identifier(key, "shot id")
            fields(spec, ("file", "style"), (), f"shots.{key}")
            file = Path(existing_file(spec["file"], self.root, f"shots.{key}.file"))
            if not file.is_relative_to(self.root):
                raise ValueError(f"Shot {key} must live inside its production directory")
            self.shot_files[key] = file
            self.registry.resolve(spec["style"], "style")
        self.lock_path = self.root / "project.lock.json"

    def resolve_shot(self, shot_id, style=None):
        if shot_id not in self.shots:
            raise ValueError(f"Unknown shot {shot_id!r}; available: {', '.join(self.shots)}")
        data = copy.deepcopy(document(self.shot_files[shot_id]))
        fields(data, ("version", "fps", "frames", "size", "stage", "actors"),
               ("samples", "trails", "audio"), "shot")

        def source(spec, kind, required=(), optional=()):
            fields(spec, ("asset", *required), optional, f"{kind} reference")
            return self.registry.resolve(spec["asset"], kind)

        stage = source(data["stage"], "stage")
        data["stage"] = {key: stage[key] for key in ("file", "collection", "camera")}
        for actor in list_at(data["actors"], "actors"):
            character = source(actor, "character", ("id", "clips"), ("position",))
            for clip in list_at(actor["clips"], "clips"):
                action = source(clip, "action", ("start", "end"))
                if action["rig_id"] != character["rig_id"]:
                    raise ValueError(
                        f"{actor['id']}: incompatible rigs {character['rig_id']!r} / {action['rig_id']!r}; "
                        "retarget the action before using it"
                    )
                clip.pop("asset")
                clip.update({key: action[key] for key in ("file", "action")})
            actor.pop("asset")
            actor.update({key: character[key] for key in ("file", "collection", "rig")})
        if "audio" in data:
            data["audio"] = source(data["audio"], "audio")["file"]
        resolved = validate_shot(data, self.shot_files[shot_id].parent)
        reference = style if style is not None else self.shots[shot_id]["style"]
        look = self.registry.resolve(reference, "style")
        return resolved, style_at(look["file"]), reference

    def snapshot(self):
        # Validate all inputs before writing a lock. A lock must describe an executable plan.
        for shot_id in self.shots:
            self.resolve_shot(shot_id)
        return {
            "version": 1,
            "project": self.data["id"],
            "project_sha256": sha256(self.path),
            "engine": engine_fingerprint(),
            "packs": {
                name: {"manifest": self.data["packs"][name], **pack.fingerprint()}
                for name, pack in sorted(self.registry.packs.items())
            },
            "shots": {
                name: {"file": self.shots[name]["file"], "sha256": sha256(path),
                       "style": self.shots[name]["style"]}
                for name, path in sorted(self.shot_files.items())
            },
        }

    def protected_inputs(self):
        paths = {self.path, *self.shot_files.values()}
        for pack in self.registry.packs.values():
            paths.update((pack.path, *pack.files.values()))
        return paths

    def lock(self):
        if self.lock_path.resolve() in self.protected_inputs():
            raise ValueError("Lock output must not overwrite a project, shot or asset input")
        return write_json(self.lock_path, self.snapshot())

    def verify(self):
        if not self.lock_path.is_file():
            raise ValueError(f"Missing {self.lock_path}; run motionbase lock {self.path}")
        locked = document(self.lock_path)
        current = self.snapshot()
        if locked != current:
            changed = [key for key in current if locked.get(key) != current[key]]
            changed += sorted(set(locked).difference(current))
            raise ValueError(
                f"Project lock is stale ({', '.join(changed)}). Inspect the intended changes, "
                "then run motionbase lock to accept the new inputs."
            )
        return locked

    def compile(self, shot_id, output, style=None):
        self.verify()
        shot, look, reference = self.resolve_shot(shot_id, style)
        output = Path(output).resolve()
        if output.suffix.lower() != ".json":
            raise ValueError("Compiled shot output must use .json")
        style_output = output.with_name(output.stem + ".style.json").resolve()
        protected = self.protected_inputs() | {self.lock_path.resolve()}
        if output == style_output or output in protected or style_output in protected:
            raise ValueError("Compile outputs must not overwrite project, shot or asset inputs")
        write_json(style_output, look)
        write_json(output, shot)
        return {"shot": str(output), "style": str(style_output), "style_id": reference,
                "lock_sha256": sha256(self.lock_path)}
