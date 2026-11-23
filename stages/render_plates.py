"""Render the studio shot as a numbered PNG sequence using Blender's Python."""

import argparse
import json
import sys
from math import radians
from pathlib import Path

import bpy
from mathutils import Vector


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def material(name, color, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    return mat


def block(name, size, position, surface, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(surface)
    if bevel:
        edge = obj.modifiers.new(name="Soft edges", type="BEVEL")
        edge.width = bevel
        edge.segments = 4
        obj.modifiers.new(name="Face normals", type="WEIGHTED_NORMAL")
    return obj


def light(name, location, power, size, color):
    lamp = bpy.data.lights.new(name, "AREA")
    lamp.energy, lamp.shape, lamp.size, lamp.color = power, "DISK", size, color
    obj = bpy.data.objects.new(name, lamp)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, (0, 0, 0.5))


def smoothstep(t):
    t = max(0, min(1, t))
    return t * t * (3 - 2 * t)


def render(config, output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = config["cycles_samples"]
    scene.cycles.use_denoising = True
    scene.cycles.seed = 14
    scene.render.resolution_x = config["width"]
    scene.render.resolution_y = config["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"

    scene.world = bpy.data.worlds.new("Studio ambience")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.3

    floor = material("Slate", (0.027, 0.039, 0.065), 0.10, 0.45)
    alloy = material("Black alloy", (0.093, 0.133, 0.196), 0.75, 0.24)
    glaze = material("Amber ceramic", (0.91, 0.32, 0.058), 0.26, 0.26)
    block("Stage", (200, 200, 0.12), (0, 0, -0.06), floor, 0)
    block("Base", (1.92, 1.92, 0.72), (0, 0, 0.36), alloy, 0.09)
    lid = block("Lid", (1.83, 1.83, 0.35), (0, 0, 0.91), glaze, 0.10)

    light("Key", (-3, -4, 6), 780, 5, (0.79, 0.87, 1))
    light("Rim", (3, 3, 4), 940, 3, (1, 0.72, 0.43))
    light("Fill", (1, -1, 5), 320, 4, (0.57, 0.72, 1))

    bpy.ops.object.camera_add()
    camera = scene.camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.shift_x = -0.20
    last = max(config["frames"] - 1, 1)
    reveal = max(config["reveal_frame"], 1)
    output.mkdir(parents=True, exist_ok=True)
    for frame in range(config["frames"]):
        fit = smoothstep(frame / reveal)
        arrival = smoothstep(frame / last)
        lid.location.z = 0.895 + 0.83 * (1 - fit)
        lid.rotation_euler.z = radians(-17) * (1 - fit)
        camera.location = (4.45 - 1.05 * arrival, -6.8, 4.1 - 0.4 * arrival)
        camera.data.ortho_scale = 6.3 - 0.62 * arrival
        aim(camera, (0, 0, 0.83))
        scene.render.filepath = str(output / f"{frame:06}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("config", type=Path)
    args.add_argument("output", type=Path)
    options = args.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    render(json.loads(options.config.read_text(encoding="utf-8")), options.output)
