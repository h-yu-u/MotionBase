"""Resolve portable asset packs, independently of Blender and any example art."""

import copy
import re
from pathlib import Path

from .config import document, fields, object_at, style_at, text_at
from .io import sha256

ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]*")
ASSET_FIELDS = {
    "character": ("collection", "rig", "rig_id"),
    "stage": ("collection", "camera"),
    "action": ("action", "rig_id"),
    "style": (),
    "audio": (),
    "prop": ("collection",),
    "material": ("material",),
}


def identifier(value, label):
    text_at(value, label)
    if not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label}: use lowercase letters, digits, '.', '_' and '-'")
    return value


class AssetPack:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.root = self.path.parent
        self.data = document(self.path)
        fields(self.data, ("version", "id", "revision", "blender", "assets"),
               ("description", "license"), "pack")
        self.id = identifier(self.data["id"], "pack.id")
        text_at(self.data["revision"], "pack.revision")
        if not isinstance(self.data["blender"], str) or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", self.data["blender"]):
            raise ValueError("pack.blender: expected a major.minor version, e.g. 4.5")
        for key in ("description", "license"):
            if key in self.data:
                text_at(self.data[key], f"pack.{key}")
        self.assets = object_at(self.data["assets"], "pack.assets")
        if not self.assets:
            raise ValueError("pack.assets must not be empty")
        self.files = {}
        for aid, spec in self.assets.items():
            identifier(aid, "asset id")
            object_at(spec, aid)
            kind = spec.get("kind")
            if not isinstance(kind, str) or kind not in ASSET_FIELDS:
                raise ValueError(f"{aid}: unsupported asset kind {kind!r}")
            fields(spec, ("kind", "file", *ASSET_FIELDS[kind]), ("description",), aid)
            for key in ASSET_FIELDS[kind]:
                text_at(spec[key], f"{aid}.{key}")
            if "description" in spec:
                text_at(spec["description"], f"{aid}.description")
            file = self.file(spec["file"])
            if kind not in ("style", "audio") and file.suffix.lower() != ".blend":
                raise ValueError(f"{aid}: {kind} assets require a .blend file")
            if kind == "style":
                if file.suffix.lower() != ".json":
                    raise ValueError(f"{aid}: style assets require a JSON file")
                style = style_at(file)
                if "materials" in style:
                    self.file(Path(style["materials"]["file"]).relative_to(self.root).as_posix())

    def file(self, relative):
        text_at(relative, "asset.file")
        if Path(relative).is_absolute():
            raise ValueError("Pack files must use paths relative to pack.json")
        file = (self.root / relative).resolve()
        if not file.is_relative_to(self.root):
            raise ValueError(f"Pack file escapes its root: {relative}")
        if not file.is_file():
            raise ValueError(f"Missing pack asset: {file}")
        self.files[file.relative_to(self.root).as_posix()] = file
        return file

    def asset(self, name, kind):
        if name not in self.assets:
            raise ValueError(f"Unknown asset {self.id}:{name}")
        spec = self.assets[name]
        if spec["kind"] != kind:
            raise ValueError(f"{self.id}:{name}: expected {kind}, found {spec['kind']}")
        result = copy.deepcopy(spec)
        result["file"] = str(self.file(spec["file"]))
        return result

    def fingerprint(self):
        return {
            "revision": self.data["revision"],
            "manifest_sha256": sha256(self.path),
            "files": {name: sha256(path) for name, path in sorted(self.files.items())},
        }


class AssetRegistry:
    def __init__(self, paths):
        self.packs = {}
        for expected_id, path in paths.items():
            identifier(expected_id, "project pack id")
            pack = AssetPack(path)
            if pack.id != expected_id:
                raise ValueError(f"Pack id mismatch: expected {expected_id}, found {pack.id}")
            self.packs[pack.id] = pack

    def resolve(self, reference, kind):
        text_at(reference, "asset reference")
        parts = reference.split(":")
        if len(parts) != 2:
            raise ValueError(f"Expected pack-id:asset-id, got {reference!r}")
        pack_id, asset_id = parts
        if pack_id not in self.packs:
            raise ValueError(f"Unknown asset pack {pack_id!r}")
        return self.packs[pack_id].asset(asset_id, kind)
