"""Validate the v1 renderer contract without importing Blender."""

import copy
import math
import re
from pathlib import Path

from .io import read_json

PRESETS = Path(__file__).resolve().parent / "presets"


def object_at(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected an object")
    return value


def fields(value, required, optional, label):
    object_at(value, label)
    missing = set(required).difference(value)
    unknown = set(value).difference(set(required) | set(optional))
    if missing:
        raise ValueError(f"{label}: missing fields {sorted(missing)}")
    if unknown:
        raise ValueError(f"{label}: unknown fields {sorted(unknown)}")


def text_at(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected a nonempty string")
    return value


def list_at(value, label):
    if not isinstance(value, list):
        raise ValueError(f"{label}: expected an array")
    return value


def document(path):
    data = object_at(read_json(path), str(path))
    if type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError(f"{path}: expected a version 1 JSON object")
    return data


def number(value, label, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{label}: invalid number {value!r}")
    return value


def integer(value, label):
    if type(value) is not int or value < 1:
        raise ValueError(f"{label}: expected a positive integer")
    return value


def vector(value, size, label):
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f"{label}: expected {size} numbers")
    return [number(x, label) for x in value]


def existing_file(value, base, label):
    text_at(value, label)
    result = (Path(base) / value).resolve()
    if not result.is_file():
        raise ValueError(f"{label}: missing asset {result}")
    return str(result)


def validate_shot(value, base):
    """Resolve legacy file paths; project asset references are compiled first."""
    data = copy.deepcopy(value)
    fields(data, ("version", "fps", "frames", "size", "stage", "actors"),
           ("samples", "trails", "audio"), "shot")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("shot.version: expected 1")
    for key in ("fps", "frames"):
        integer(data[key], key)
    size = list_at(data["size"], "size")
    if len(size) != 2 or any(integer(v, "size") % 2 for v in size):
        raise ValueError("H.264 output needs two positive even dimensions")
    stage = data["stage"]
    fields(stage, ("file", "collection", "camera"), (), "stage")
    stage["file"] = existing_file(stage["file"], base, "stage.file")
    for key in ("collection", "camera"):
        text_at(stage[key], f"stage.{key}")
    ids = set()
    for actor in list_at(data["actors"], "actors"):
        fields(actor, ("id", "file", "collection", "rig", "clips"), ("position",), "actor")
        aid = text_at(actor["id"], "actor.id")
        if aid in ids:
            raise ValueError(f"Duplicate actor id: {aid!r}")
        ids.add(aid)
        actor["file"] = existing_file(actor["file"], base, f"{aid}.file")
        for key in ("collection", "rig"):
            text_at(actor[key], f"{aid}.{key}")
        actor["position"] = vector(actor.get("position", [0, 0, 0]), 3, f"{aid}.position")
        previous_end = 0
        for clip in list_at(actor["clips"], f"{aid}.clips"):
            fields(clip, ("file", "action", "start", "end"), (), f"{aid}.clip")
            clip["file"] = existing_file(clip["file"], base, f"{aid}.clip.file")
            text_at(clip["action"], f"{aid}.clip.action")
            start, end = (integer(clip[k], k) for k in ("start", "end"))
            if not previous_end < start <= end <= data["frames"]:
                raise ValueError(f"{aid}: clips must be ordered, in range and non-overlapping")
            previous_end = end
    for effect in list_at(data.get("trails", []), "trails"):
        fields(effect, ("actor", "bone", "inner", "outer", "role", "start", "end", "history"), (), "trail")
        for key in ("actor", "bone", "role"):
            text_at(effect[key], f"trail.{key}")
        if effect["actor"] not in ids:
            raise ValueError(f"Unknown trail actor: {effect['actor']}")
        for key in ("start", "end", "history"):
            integer(effect[key], key)
        if not 1 <= effect["start"] < effect["end"] <= data["frames"]:
            raise ValueError("Trail interval outside shot")
        for key in ("inner", "outer"):
            effect[key] = vector(effect[key], 3, f"trail.{key}")
    if "audio" in data:
        data["audio"] = existing_file(data["audio"], base, "audio")
    integer(data.get("samples", 2), "samples")
    return data


def shot_at(path):
    path = Path(path).resolve()
    return validate_shot(document(path), path.parent)


def style_path(name, directories=()):
    text_at(str(name), "style")
    path = Path(name)
    if path.is_file():
        return path.resolve()
    if path.suffix or len(path.parts) != 1:
        raise ValueError(f"Style file does not exist: {path}")
    for directory in [*map(Path, directories), PRESETS]:
        candidate = directory / f"{name}.json"
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError(f"Unknown style {name!r}; use a JSON path or --style-dir")


def style_at(name, directories=()):
    path = style_path(name, directories)
    data = document(path)
    fields(data, ("version", "name", "shading", "light", "shadow", "rim", "grain", "palette"),
           ("materials",), "style")
    text_at(data["name"], "style.name")
    palette = object_at(data["palette"], "palette")
    if not {"sky", "ink"}.issubset(palette):
        raise ValueError("style.palette requires sky and ink")
    for role, color in palette.items():
        text_at(role, "palette role")
        if not isinstance(color, str) or not re.fullmatch(r"#[\da-fA-F]{6}", color):
            raise ValueError(f"Invalid color for {role}: {color}")
    if data["shading"] not in ("bands", "continuous"):
        raise ValueError("shading must be bands or continuous")
    for key in ("shadow", "grain", "rim"):
        if not 0 <= number(data[key], key) <= 1:
            raise ValueError(f"{key} must be in [0, 1]")
    if not any(vector(data["light"], 3, "light")):
        raise ValueError("Light direction must be nonzero")
    if "materials" in data:
        library = data["materials"]
        fields(library, ("file", "roles"), (), "materials")
        library["file"] = existing_file(library["file"], path.parent, "materials.file")
        for role, material in object_at(library["roles"], "materials.roles").items():
            text_at(role, "material role")
            text_at(material, "material name")
    return data
