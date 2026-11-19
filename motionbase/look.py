"""Apply a look to semantic material slots; keep geometry and animation intact."""

import bpy
from mathutils import Vector


def linear_rgb(hexcode):
    values = [int(hexcode[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in values)


def material(role, look, flat=False):
    rgb = linear_rgb(look["palette"][role])
    mat = bpy.data.materials.new(f"{look['name']} / {role}")
    mat["motionbase_role"] = role
    mat["motionbase_flat"] = flat
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    add, link = tree.nodes.new, tree.links.new
    out, emission = add("ShaderNodeOutputMaterial"), add("ShaderNodeEmission")
    link(emission.outputs[0], out.inputs["Surface"])
    emission.inputs["Color"].default_value = (*rgb, 1)
    lit = None
    if not flat:
        geo, dot = add("ShaderNodeNewGeometry"), add("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = Vector(look["light"]).normalized()
        link(geo.outputs["Normal"], dot.inputs[0])
        ramp = add("ShaderNodeValToRGB")
        colors = ramp.color_ramp
        colors.interpolation = "CONSTANT" if look["shading"] == "bands" else "EASE"
        colors.elements[1].position = 0.79
        colors.elements.new(0.38)
        strengths = (look["shadow"], (1 + look["shadow"]) * 0.5, 1.0)
        # Adding a stop can move Blender's underlying array. Resolve stops after insertion.
        for element, strength in zip(colors.elements, strengths):
            element.color = (*[v * strength for v in rgb], 1)
        link(dot.outputs["Value"], ramp.inputs[0])
        lit = ramp.outputs[0]
        if look["rim"]:
            facing = add("ShaderNodeLayerWeight")
            border = add("ShaderNodeMath")
            border.operation = "GREATER_THAN"
            link(facing.outputs["Facing"], border.inputs[0])
            border.inputs[1].default_value = 1 - look["rim"]
            mix = add("ShaderNodeMixRGB")
            link(border.outputs[0], mix.inputs[0])
            link(lit, mix.inputs[1])
            mix.inputs[2].default_value = (*linear_rgb(look["palette"]["ink"]), 1)
            lit = mix.outputs[0]
    if look["grain"]:
        noise, coord = add("ShaderNodeTexNoise"), add("ShaderNodeTexCoord")
        noise.inputs["Scale"].default_value = 125
        noise.inputs["Detail"].default_value = 2
        link(coord.outputs["Generated"], noise.inputs[0])
        mix = add("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = look["grain"]
        mix.inputs[1].default_value = (*rgb, 1)
        if lit is not None:
            link(lit, mix.inputs[1])
        link(noise.outputs["Fac"], mix.inputs[2])
        lit = mix.outputs[0]
    if lit is not None:
        link(lit, emission.inputs["Color"])
    return mat


def apply_look(objects, style):
    cache = {}
    external = {}
    if style.get("materials"):
        library = style["materials"]
        names = list(dict.fromkeys(library["roles"].values()))
        with bpy.data.libraries.load(library["file"], link=False) as (source, dest):
            missing = set(names).difference(source.materials)
            if missing:
                raise ValueError(f"Missing Blender materials: {sorted(missing)}")
            dest.materials = names.copy()
        by_name = dict(zip(names, dest.materials))
        external = {role: by_name[name] for role, name in library["roles"].items()}
    applied = set()
    for obj in objects:
        for slot in obj.material_slots:
            old = slot.material
            if not old or old in applied or "motionbase_role" not in old:
                continue
            role = old["motionbase_role"]
            if role in external:
                slot.material = external[role]
                applied.add(slot.material)
                continue
            if role not in style["palette"]:
                raise ValueError(f"{obj.name}: style is missing material role {role!r}")
            key = role, bool(old.get("motionbase_flat", False))
            if key not in cache:
                cache[key] = material(role, style, key[1])
            slot.material = cache[key]
            applied.add(slot.material)
